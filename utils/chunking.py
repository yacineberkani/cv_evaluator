"""
Intelligent Dynamic Chunking — adapté au format JEMS et CVs similaires.

Format JEMS caractéristique
────────────────────────────
  Page 1 : Identité + bloc profil sans header explicite
            → heuristique : tout ce qui précède la première section majuscule

  Compétences : deux sous-sections (Gen AI & Agentic AI / RAG / COMPÉTENCES TECHNIQUES /
                Frameworks / Langages / BDD / Cloud…)

  Formations  : liste chronologique annéé + diplôme + établissement + description

  Expériences : blocs structurés :
    ┌─────────────────────────────────────────────┐
    │ POSTE (caps ou titre court)                 │
    │ ENTREPRISE                                  │
    │ durée (X an(s) / X mois)                   │
    │ période (Mois YYYY à Mois YYYY)             │
    │ Contexte …                                  │
    │ Missions …                                  │
    │ Résultats …                                 │
    │ Environnement technique …                   │
    └─────────────────────────────────────────────┘

Stratégie de chunking
──────────────────────
1. DÉTECTION DES SECTIONS MAJEURES  (regex + heuristique caps)
2. EXTRACTION DU PROFIL IMPLICITE   (avant la 1re section majeure)
3. SPLITTING ADAPTÉ PAR SECTION TYPE
     experiences  → 1 Chunk par bloc expérience (Contexte/Missions/Résultats/Env)
     competences  → regroupement par catégorie (Gen AI / RAG / Techniques / Outils…)
     formations   → 1 Chunk global (généralement court)
     autres       → paragraphes ou chunk unique
4. BUDGET TOKENS respecté (<= MAX_TOKENS_PER_CHUNK par chunk)
5. CONTEXT INJECTION entre chunks de la même section (overlap 200 tokens)
6. FALLBACKS garantis pour les 4 sections requises

Compatibilité
─────────────
  chunk_cv_by_sections()  → interface legacy orchestrator (inchangée)
  get_section_or_full()   → interface legacy orchestrator (inchangée)
  chunk_cv()              → nouvelle interface riche (CVSections)
  get_best_chunks_for_agent() → composition budget-aware pour les agents
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────────
MAX_TOKENS_PER_CHUNK: int = 3_000
OVERLAP_TOKENS:       int = 200
CHARS_PER_TOKEN:    float = 4.0
MAX_CHARS:            int = int(MAX_TOKENS_PER_CHUNK * CHARS_PER_TOKEN)
OVERLAP_CHARS:        int = int(OVERLAP_TOKENS * CHARS_PER_TOKEN)

# ── Vocabulaire des sections (FR + EN) ───────────────────────────────────────
SECTION_PATTERNS: Dict[str, List[str]] = {
    # Profil / résumé (header explicite)
    "resume": [
        r"(?i)^(profil(\s+pro(fessionnel)?)?|résumé(\s+pro(fessionnel)?)?|summary"
        r"|about\s*me|à\s*propos|objectif(\s*(pro|career))?|présentation"
        r"|introduction|accroche|executive\s*summary)\s*$",
    ],
    # Expériences
    "experiences": [
        r"(?i)^(expériences?\s*(professionnelle[s]?)?|professional\s*experience"
        r"|work\s*experience|employment|parcours\s*professionnel"
        r"|postes?\s*occupés?|carrière|career\s*history)\s*$",
    ],
    # Compétences
    "competences": [
        r"(?i)^(compétences?(\s+techniques?)?(\s+et\s+savoir[s]?\s*faire)?"
        r"|skills?|technical\s*skills?|hard\s*skills?|soft\s*skills?"
        r"|savoir[s]?\s*faire|stack\s*technique|expertise|outils?\s*(et\s*technos?)?)\s*$",
    ],
    # Formations
    "formations": [
        r"(?i)^(formations?|education|diplôme[s]?|cursus|études"
        r"|certifications?|parcours\s*académique|qualifications?|scolarité)\s*$",
    ],
    # Langues
    "langues": [
        r"(?i)^(langues?|languages?|linguistic)\s*$",
    ],
    # Centres d'intérêt
    "centres_interet": [
        r"(?i)^(centre[s]?\s*d'intérêt|hobbies?|loisirs?|interests?"
        r"|activités?\s*extra|passions?)\s*$",
    ],
    # Projets / réalisations
    "projets": [
        r"(?i)^(projets?|projects?|réalisations?|portfolio|open.?source)\s*$",
    ],
    # Publications
    "publications": [
        r"(?i)^(publications?|articles?|recherche[s]?|research|papers?)\s*$",
    ],
    # Références
    "references": [
        r"(?i)^(référence[s]?|references?|recommendations?)\s*$",
    ],
}

REQUIRED_SECTIONS = {"resume", "experiences", "competences", "formations"}

# ── Pattern de début de bloc expérience (format JEMS) ────────────────────────
# Ligne de poste  : tout en CAPS ou titre court + maj, ≤ 80 chars, souvent seule
# Ligne durée     : "X an(s)" / "X mois" / "X ans et Y mois"
# Ligne période   : "Mois YYYY à Mois YYYY"  ou  "Mois YYYY – Mois YYYY"
_EXP_BLOCK_PATTERNS = [
    # Poste tout en caps (ex: DATA SCIENTIST - GEN AI / NLP)
    re.compile(r"^[A-Z][A-Z\s\-/,\.]{5,79}$"),
    # Durée (ex: "1 an et 4 mois", "2 mois", "3 ans")
    re.compile(r"(?i)^\d+\s+(an|ans|mois)(\s+et\s+\d+\s+(mois|ans?))?$"),
    # Période (ex: "Octobre 2024 à février 2026")
    re.compile(
        r"(?i)^(janvier|février|mars|avril|mai|juin|juillet|août|septembre"
        r"|octobre|novembre|décembre|jan|fév|mar|avr|juil|août|sept|oct|nov|déc"
        r"|january|february|march|april|may|june|july|august|september"
        r"|october|november|december)\s+\d{4}"
    ),
]

# ── Sous-sections internes d'un bloc expérience ───────────────────────────────
_EXP_SUBSECTION = re.compile(
    r"(?i)^(contexte|missions?|résultats?|environnement\s*technique"
    r"|stack\s*technique|technologies|outils?|livrables?)\s*:?\s*$"
)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class Chunk:
    section: str
    index: int
    total_chunks: int
    text: str
    token_estimate: int
    preceding_context: str = ""
    is_overflow: bool = False
    # Métadonnées JEMS spécifiques
    exp_title: Optional[str] = None      # "DATA SCIENTIST - GEN AI / NLP"
    exp_company: Optional[str] = None    # "ASSYSTEM EOS"
    exp_period: Optional[str] = None     # "Octobre 2024 à février 2026"

    @property
    def full_text(self) -> str:
        if self.preceding_context:
            return (
                f"[CONTEXTE PRÉCÉDENT]\n{self.preceding_context}"
                f"\n\n[CONTENU PRINCIPAL]\n{self.text}"
            )
        return self.text

    def __repr__(self) -> str:
        title = f" | {self.exp_title}" if self.exp_title else ""
        return (
            f"Chunk(section={self.section!r}{title}, "
            f"idx={self.index}/{self.total_chunks - 1}, "
            f"~{self.token_estimate} tok, overflow={self.is_overflow})"
        )


@dataclass
class CVSections:
    chunks_by_section: Dict[str, List[Chunk]] = field(default_factory=dict)
    full_text: str = ""
    detected_sections: List[str] = field(default_factory=list)
    profil_implicit: bool = False   # True si le profil a été extrait sans header

    def get_section_text(
        self,
        section: str,
        max_tokens: int = MAX_TOKENS_PER_CHUNK,
        join_sep: str = "\n\n",
    ) -> str:
        chunks = self.chunks_by_section.get(section, [])
        if not chunks or sum(c.token_estimate for c in chunks) < 20:
            logger.warning("[CVSections] Section '%s' absente. Fallback full_text.", section)
            return _window(self.full_text, max_tokens)
        budget = max_tokens
        parts: List[str] = []
        for chunk in chunks:
            if budget <= 0:
                break
            parts.append(chunk.full_text)
            budget -= chunk.token_estimate
        result = join_sep.join(parts)
        if budget < 0:
            result = _truncate(result, max_tokens)
        return result

    def get_experience_chunks(self) -> List[Chunk]:
        """Retourne les chunks d'expérience triés (utile pour itérer poste par poste)."""
        return self.chunks_by_section.get("experiences", [])

    def get_first_chunk(self, section: str) -> Optional[Chunk]:
        chunks = self.chunks_by_section.get(section, [])
        return chunks[0] if chunks else None

    def section_token_count(self, section: str) -> int:
        return sum(c.token_estimate for c in self.chunks_by_section.get(section, []))

    def summary_report(self) -> str:
        lines = ["=== CV Chunking Report ==="]
        if self.profil_implicit:
            lines.append("  [profil extrait implicitement (pas de header)]")
        for sec, chunks in self.chunks_by_section.items():
            total_tok = sum(c.token_estimate for c in chunks)
            overflow = " [SPLIT]" if any(c.is_overflow for c in chunks) else ""
            exp_titles = ""
            if sec == "experiences":
                titles = [c.exp_title for c in chunks if c.exp_title]
                if titles:
                    exp_titles = "\n    → " + "\n    → ".join(titles)
            lines.append(
                f"  {sec:<20} {len(chunks):>2} chunk(s)  ~{total_tok:>5} tokens{overflow}{exp_titles}"
            )
        return "\n".join(lines)


# ── API publique ──────────────────────────────────────────────────────────────

def chunk_cv(full_text: str) -> CVSections:
    """
    Point d'entrée principal.

    Étapes :
      1. Détection des frontières de sections
      2. Extraction du profil implicite (avant la 1re section)
      3. Découpe adaptée par type de section
      4. Fallback pour les sections requises absentes
    """
    result = CVSections(full_text=full_text)
    lines = full_text.splitlines()

    # 1. Frontières
    boundaries = _detect_boundaries(lines)
    logger.info("[Chunking] %d frontières détectées.", len(boundaries))

    # 2. Profil implicite : tout ce qui précède la 1re section majeure
    profil_text = _extract_implicit_profile(lines, boundaries)
    if profil_text and "resume" not in {b[1] for b in boundaries}:
        result.profil_implicit = True
        result.chunks_by_section["resume"] = [
            Chunk(
                section="resume",
                index=0,
                total_chunks=1,
                text=profil_text,
                token_estimate=_tokens(profil_text),
            )
        ]
        result.detected_sections.append("resume")

    # 3. Slicing et chunking par section
    raw_sections = _slice_sections(lines, boundaries)
    result.detected_sections += [s for s in raw_sections if s not in result.detected_sections]

    for section_name, raw_text in raw_sections.items():
        new_chunks = _chunk_section(section_name, raw_text)
        if section_name in result.chunks_by_section:
            existing = result.chunks_by_section[section_name]
            offset = len(existing)
            for c in new_chunks:
                c.index += offset
            result.chunks_by_section[section_name] = existing + new_chunks
        else:
            result.chunks_by_section[section_name] = new_chunks

    # Recalcul total_chunks après fusions éventuelles
    for sec, chunks in result.chunks_by_section.items():
        for c in chunks:
            c.total_chunks = len(chunks)

    # 4. Fallback sections requises
    for sec in REQUIRED_SECTIONS:
        if sec not in result.chunks_by_section:
            logger.warning("[Chunking] Section requise '%s' absente. Injection fallback.", sec)
            fb = (
                f"[Section '{sec}' non détectée — contenu complet du CV]\n\n"
                + _window(full_text, MAX_TOKENS_PER_CHUNK)
            )
            result.chunks_by_section[sec] = [
                Chunk(
                    section=sec,
                    index=0,
                    total_chunks=1,
                    text=fb,
                    token_estimate=_tokens(fb),
                )
            ]

    logger.info("[Chunking]\n%s", result.summary_report())
    return result


def get_best_chunks_for_agent(
    cv: CVSections,
    primary_section: str,
    context_sections: Optional[List[str]] = None,
    agent_token_budget: int = MAX_TOKENS_PER_CHUNK * 2,
) -> str:
    parts: List[str] = []
    remaining = agent_token_budget

    primary_text = cv.get_section_text(primary_section, max_tokens=remaining)
    parts.append(primary_text)
    remaining -= _tokens(primary_text)

    for ctx_sec in (context_sections or []):
        if remaining <= 100:
            break
        ctx_text = cv.get_section_text(
            ctx_sec, max_tokens=min(remaining, MAX_TOKENS_PER_CHUNK)
        )
        parts.append(f"\n\n--- [CONTEXTE : {ctx_sec.upper()}] ---\n{ctx_text}")
        remaining -= _tokens(ctx_text)

    return "\n\n".join(parts)


# ── Interfaces legacy (orchestrator actuel inchangé) ─────────────────────────

def chunk_cv_by_sections(full_text: str) -> Dict[str, str]:
    cv = chunk_cv(full_text)
    out: Dict[str, str] = {"full_text": full_text}
    for sec, chunks in cv.chunks_by_section.items():
        out[sec] = "\n\n".join(c.full_text for c in chunks)
    return out


def get_section_or_full(
    sections: Dict[str, str],
    section_name: str,
    max_chars: int = MAX_CHARS,
) -> str:
    content = sections.get(section_name, "")
    if len(content) < 100:
        content = sections.get("full_text", "")
    return _truncate_chars(content, max_chars)


# ── Logique interne ───────────────────────────────────────────────────────────

def _tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))

def _truncate(text: str, max_tokens: int) -> str:
    return _truncate_chars(text, int(max_tokens * CHARS_PER_TOKEN))

def _truncate_chars(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[… TRONQUÉ — dépasse la fenêtre de contexte …]"

def _window(text: str, max_tokens: int) -> str:
    return _truncate(text, max_tokens)


def _detect_boundaries(lines: List[str]) -> List[Tuple[int, str]]:
    """
    Détecte les headers de sections.
    Critères JEMS : ligne courte (≤ 60 chars), tout en majuscules ou correspondant
    aux patterns, précédée/suivie de lignes vides de préférence.
    """
    boundaries: List[Tuple[int, str]] = []
    seen_at: Dict[str, int] = {}
    n = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 60:
            continue

        for section_name, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, stripped):
                    last = seen_at.get(section_name, -999)
                    if i - last > 5:
                        boundaries.append((i, section_name))
                        seen_at[section_name] = i
                    break

    boundaries.sort(key=lambda x: x[0])
    return boundaries


def _extract_implicit_profile(
    lines: List[str],
    boundaries: List[Tuple[int, str]],
) -> str:
    """
    Dans les CVs JEMS, le profil est en haut sans header explicite.
    On extrait tout ce qui précède la 1re section détectée.
    On garde un maximum de MAX_CHARS/3 (le profil est généralement court).
    """
    if not boundaries:
        return ""
    first_boundary = boundaries[0][0]
    if first_boundary <= 2:
        return ""

    raw = "\n".join(lines[:first_boundary]).strip()
    if not raw or len(raw) < 50:
        return ""

    max_chars = MAX_CHARS // 3
    if len(raw) > max_chars:
        raw = raw[:max_chars] + "\n[…tronqué]"
    return raw


def _slice_sections(
    lines: List[str],
    boundaries: List[Tuple[int, str]],
) -> Dict[str, str]:
    raw: Dict[str, str] = {}
    n = len(boundaries)

    for idx, (start_line, section_name) in enumerate(boundaries):
        end_line = boundaries[idx + 1][0] if idx + 1 < n else len(lines)
        content = "\n".join(lines[start_line:end_line]).strip()
        if not content:
            continue
        if section_name in raw:
            raw[section_name] += "\n\n" + content
        else:
            raw[section_name] = content

    return raw


def _chunk_section(section_name: str, raw_text: str) -> List[Chunk]:
    """Dispatche vers la stratégie de découpage appropriée selon le type de section."""
    if section_name == "experiences":
        return _chunk_experiences(raw_text)
    elif section_name == "competences":
        return _chunk_competences(raw_text)
    else:
        return _chunk_generic(section_name, raw_text)


# ── Découpage spécialisé : EXPÉRIENCES ────────────────────────────────────────

def _chunk_experiences(raw_text: str) -> List[Chunk]:
    """
    Découpe la section expériences en 1 Chunk par poste.
    Détecte les blocs JEMS :
      TITRE_POSTE
      ENTREPRISE
      durée / période
      Contexte / Missions / Résultats / Environnement technique
    """
    blocks = _split_experience_blocks(raw_text)

    if not blocks:
        return _chunk_generic("experiences", raw_text)

    chunks: List[Chunk] = []
    prev_tail = ""

    for i, block in enumerate(blocks):
        title, company, period = _extract_exp_metadata(block)
        preceding = _make_context_header(prev_tail) if prev_tail else ""

        # Si le bloc est trop grand (rare mais possible), on le re-split
        if len(block) > MAX_CHARS:
            sub_blocks = _split_by_paragraphs(block)
            sub_blocks = _normalise_blocks(sub_blocks)
            for j, sub in enumerate(sub_blocks):
                chunks.append(
                    Chunk(
                        section="experiences",
                        index=len(chunks),
                        total_chunks=0,  # recalculé après
                        text=sub,
                        token_estimate=_tokens(sub),
                        preceding_context=preceding if j == 0 else _make_context_header(sub_blocks[j-1][-OVERLAP_CHARS:]),
                        is_overflow=(j > 0),
                        exp_title=title,
                        exp_company=company,
                        exp_period=period,
                    )
                )
        else:
            chunks.append(
                Chunk(
                    section="experiences",
                    index=len(chunks),
                    total_chunks=0,
                    text=block,
                    token_estimate=_tokens(block),
                    preceding_context=preceding,
                    is_overflow=False,
                    exp_title=title,
                    exp_company=company,
                    exp_period=period,
                )
            )

        prev_tail = block[-OVERLAP_CHARS:] if len(block) > OVERLAP_CHARS else block

    return chunks


def _split_experience_blocks(text: str) -> List[str]:
    """
    Identifie les frontières entre postes dans la section expériences.

    Heuristique JEMS :
    Structure typique d un bloc :
        TITRE POSTE (ligne 1, CAPS)
        ENTREPRISE  (ligne 2, CAPS — fait partie du même bloc !)
        1 an et 4 mois
        Octobre 2024 à février 2026
        Contexte / Missions / Résultats / Environnement technique ...

    On détecte le début d un bloc = première ligne CAPS dont l'une des
    LOOKAHEAD_MAX lignes suivantes contient une durée ou une période.
    La ligne CAPS immédiatement suivante (entreprise) N EST PAS un nouveau bloc.
    """
    LOOKAHEAD_MAX = 8  # cherche durée/période dans les N lignes suivantes

    lines = text.splitlines()
    n = len(lines)
    block_starts: List[int] = []

    def _is_caps_title(s: str) -> bool:
        return (
            bool(s)
            and len(s) <= 80
            and s == s.upper()
            and len(s) > 4
            and not s.startswith("©")
            and not re.match(r"^\d", s)
        )

    def _has_duration(start_i: int) -> bool:
        for j in range(start_i, min(start_i + LOOKAHEAD_MAX, n)):
            s = lines[j].strip()
            for pat in _EXP_BLOCK_PATTERNS[1:]:
                if pat.match(s):
                    return True
        return False

    i = 0
    while i < n:
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue

        if _is_caps_title(stripped) and _has_duration(i):
            # Vérifier que ce n est pas juste l entreprise d un bloc déjà ouvert :
            # Si le bloc_start précédent est très proche (< 3 lignes non-vides)
            # et que lui aussi est en CAPS, il s agit du header TITRE+ENTREPRISE
            # → on n ouvre PAS un nouveau bloc, on saute
            if block_starts:
                last_start = block_starts[-1]
                # lignes non-vides entre last_start et i
                non_empty_between = sum(
                    1 for l in lines[last_start + 1:i] if l.strip()
                )
                if non_empty_between <= 1 and _is_caps_title(lines[last_start].strip()):
                    # C est la ligne entreprise juste après le titre → skip
                    i += 1
                    continue
            block_starts.append(i)

        i += 1

    if len(block_starts) < 2:
        paragraphs = re.split(r"\n{3,}", text)
        cleaned = [p.strip() for p in paragraphs if p.strip()]
        return cleaned if cleaned else [text]

    blocks: List[str] = []
    if block_starts[0] > 0:
        header = "\n".join(lines[:block_starts[0]]).strip()
        if header:
            blocks.append(header)

    for k, start in enumerate(block_starts):
        end = block_starts[k + 1] if k + 1 < len(block_starts) else n
        block = "\n".join(lines[start:end]).strip()
        if block:
            blocks.append(block)

    return blocks


def _extract_exp_metadata(block: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extrait titre, entreprise et période depuis un bloc expérience JEMS.

    Format JEMS :
      Ligne 1 : TITRE POSTE (CAPS)
      Ligne 2 : ENTREPRISE  (CAPS possible — ex: ASSYSTEM EOS)
      Ligne 3 : durée (ex: 1 an et 4 mois)
      Ligne 4 : période (ex: Octobre 2024 à février 2026)
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return None, None, None

    title = None
    company = None
    period = None

    # Ligne 0 : toujours le titre (première ligne non-vide du bloc)
    title = lines[0] if lines else None

    # Lignes 1-6 : on cherche entreprise, durée, période
    for i, line in enumerate(lines[1:7], start=1):
        # Période : pattern "Mois YYYY à Mois YYYY"
        if period is None and _EXP_BLOCK_PATTERNS[2].match(line):
            period = line
            continue
        # Durée simple : on ignore, la période vient après
        if _EXP_BLOCK_PATTERNS[1].match(line):
            continue
        # Sous-section interne → on arrête
        if _EXP_SUBSECTION.match(line):
            break
        # Entreprise : première ligne non-durée, non-période, non-sous-section
        if company is None and not _EXP_BLOCK_PATTERNS[1].match(line):
            company = line

    return title, company, period


# ── Découpage spécialisé : COMPÉTENCES ────────────────────────────────────────

def _chunk_competences(raw_text: str) -> List[Chunk]:
    """
    Groupe les compétences par catégorie fonctionnelle :
      - Bloc 1 : Gen AI & Agentic AI, RAG (compétences métier)
      - Bloc 2 : IA technique (LLM, ML, NLP…) + Outils (frameworks, langages…)
      - Bloc 3 : Infrastructure (cloud, BDD, DevOps…)

    Si le total rentre dans MAX_CHARS → 1 chunk unique.
    """
    if len(raw_text) <= MAX_CHARS:
        return [
            Chunk(
                section="competences",
                index=0,
                total_chunks=1,
                text=raw_text,
                token_estimate=_tokens(raw_text),
            )
        ]

    # Catégories JEMS connues → regroupement logique
    CATEGORY_GROUPS = [
        # Groupe 1 : compétences GenAI & RAG (ce qui différencie le profil)
        {
            "label": "Compétences GenAI & RAG",
            "patterns": [
                r"(?i)(gen\s*ai|agentic|rag|llm|prompt|idp|ocr|langchain|langgraph"
                r"|orchestrat|contexte\s*conv)",
            ],
        },
        # Groupe 2 : Machine Learning & NLP
        {
            "label": "Machine Learning & NLP",
            "patterns": [
                r"(?i)(machine\s*learning|deep\s*learning|nlp|reinforcement|fine.?tun"
                r"|embeddings?|vectori|transformers?|pytorch|tensorflow|scikit|hugging)",
            ],
        },
        # Groupe 3 : Outils & Frameworks
        {
            "label": "Outils & Frameworks",
            "patterns": [
                r"(?i)(python|java|sql|docker|kubernetes|git|github|gitlab|pycharm"
                r"|vscode|jupyter|cursor|pandas|numpy|streamlit|talend|colab)",
            ],
        },
        # Groupe 4 : Cloud, BDD & DevOps
        {
            "label": "Cloud, BDD & Infrastructure",
            "patterns": [
                r"(?i)(aws|gcp|google\s*cloud|azure|postgresql|mysql|redis|chroma"
                r"|qdrant|pinecone|bigquery|mongodb|hadoop|spark|power\s*bi|looker)",
            ],
        },
    ]

    paragraphs = _split_by_paragraphs(raw_text)
    groups: Dict[str, List[str]] = {g["label"]: [] for g in CATEGORY_GROUPS}
    groups["Autres"] = []

    for para in paragraphs:
        assigned = False
        for group in CATEGORY_GROUPS:
            if any(re.search(p, para) for p in group["patterns"]):
                groups[group["label"]].append(para)
                assigned = True
                break
        if not assigned:
            groups["Autres"].append(para)

    chunks: List[Chunk] = []
    for label, paras in groups.items():
        if not paras:
            continue
        text = f"[{label}]\n\n" + "\n\n".join(paras)
        if len(text) > MAX_CHARS:
            sub_texts = _hard_split(text)
            for j, sub in enumerate(sub_texts):
                chunks.append(
                    Chunk(
                        section="competences",
                        index=len(chunks),
                        total_chunks=0,
                        text=sub,
                        token_estimate=_tokens(sub),
                        is_overflow=(j > 0),
                    )
                )
        else:
            chunks.append(
                Chunk(
                    section="competences",
                    index=len(chunks),
                    total_chunks=0,
                    text=text,
                    token_estimate=_tokens(text),
                )
            )

    if not chunks:
        return _chunk_generic("competences", raw_text)

    return chunks


# ── Découpage générique (formations, langues, profil, etc.) ───────────────────

def _chunk_generic(section_name: str, raw_text: str) -> List[Chunk]:
    """
    Chunk unique si ≤ MAX_CHARS, sinon split par paragraphes avec overlap.
    """
    if len(raw_text) <= MAX_CHARS:
        return [
            Chunk(
                section=section_name,
                index=0,
                total_chunks=1,
                text=raw_text,
                token_estimate=_tokens(raw_text),
            )
        ]

    logger.info(
        "[Chunking] Section '%s' (%d chars). Split générique.", section_name, len(raw_text)
    )
    blocks = _normalise_blocks(_split_by_paragraphs(raw_text))
    chunks: List[Chunk] = []
    prev_tail = ""

    for i, block in enumerate(blocks):
        preceding = _make_context_header(prev_tail) if prev_tail else ""
        chunks.append(
            Chunk(
                section=section_name,
                index=i,
                total_chunks=len(blocks),
                text=block,
                token_estimate=_tokens(block),
                preceding_context=preceding,
                is_overflow=(i > 0),
            )
        )
        prev_tail = block[-OVERLAP_CHARS:] if len(block) > OVERLAP_CHARS else block

    return chunks


# ── Utilitaires internes ───────────────────────────────────────────────────────

def _split_by_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def _normalise_blocks(blocks: List[str]) -> List[str]:
    """Fusionne les blocs trop petits, éclate les blocs trop grands."""
    merged: List[str] = []
    buffer = ""
    for block in blocks:
        if len(buffer) + len(block) + 2 <= MAX_CHARS:
            buffer = (buffer + "\n\n" + block).strip() if buffer else block
        else:
            if buffer:
                merged.append(buffer)
            buffer = block
    if buffer:
        merged.append(buffer)

    result: List[str] = []
    for block in merged:
        result.extend([block] if len(block) <= MAX_CHARS else _hard_split(block))
    return result


def _hard_split(text: str) -> List[str]:
    """Dernier recours : découpe par nombre de chars avec overlap sur newline."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            search_start = end - MAX_CHARS // 5
            nl = text.rfind("\n", search_start, end)
            if nl > search_start:
                end = nl
        chunks.append(text[start:end].strip())
        start = max(start + 1, end - OVERLAP_CHARS)
    return [c for c in chunks if c]


def _make_context_header(prev_tail: str) -> str:
    lines = [l.strip() for l in prev_tail.splitlines() if l.strip()]
    summary = " | ".join(lines[-3:]) if lines else prev_tail[:120]
    return f"(Suite — contexte fin du bloc précédent) : {summary}"
