"""
Découpage dynamique intelligent pour le contenu des CV.

Stratégie : découpage hybride par section + prise en compte des tokens
───────────────────────────────────────────────────────────────────────
1. DÉTECTION DES SECTIONS    → expressions régulières (FR + EN) pour localiser
                               les limites sémantiques
2. ESTIMATION DES TOKENS     → heuristique ~4 caractères/token, sans librairie externe
3. DÉCOUPAGE ADAPTATIF       → les sections qui dépassent le budget de tokens sont
                               sous-découpées par paragraphe / bloc de dates afin
                               que le LLM ne reçoive jamais un mur de texte tronqué
                               en pleine phrase
4. INJECTION DE CONTEXTE     → chaque fragment de dépassement reçoit un « en‑tête »
                               léger résumant ce qui précède (continuité sémantique)
5. SOLUTION DE SECOURS       → si aucune section n’est trouvée, le texte complet
                               est divisé en fenêtres avec chevauchement paramétrable

Budget de tokens par défaut
───────────────────────────
  MAX_TOKENS_PER_CHUNK  = 3 000   (sûr pour les modèles avec contexte 4k)
  OVERLAP_TOKENS        =   200   (préservation du contexte entre fragments)
  CHARS_PER_TOKEN       =     4   (heuristique conservative pour le français/anglais)

API rétrocompatible
───────────────────
  chunk_cv_by_sections()  → interface dict héritée (utilisée par l’orchestrateur actuel)
  get_section_or_full()   → fonction utilitaire héritée (utilisée par l’orchestrateur actuel)

Nouvelle API
────────────
  chunk_cv()                    → renvoie un dataclass CVSections
  get_best_chunks_for_agent()   → chaîne de caractères adaptée au budget de tokens
                                  pour l’agent
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Tunable constants ────────────────────────────────────────────────────────
MAX_TOKENS_PER_CHUNK: int = 3_000
OVERLAP_TOKENS: int = 200
CHARS_PER_TOKEN: float = 4.0
MAX_CHARS: int = int(MAX_TOKENS_PER_CHUNK * CHARS_PER_TOKEN)
OVERLAP_CHARS: int = int(OVERLAP_TOKENS * CHARS_PER_TOKEN)

# ── Section vocabulary (FR + EN) ─────────────────────────────────────────────
SECTION_PATTERNS: Dict[str, List[str]] = {
    "resume": [
        r"(?i)(profil\s*pro|profil\s*candidat|résumé\s*pro|summary|about\s*me"
        r"|à\s*propos|objectif(\s*(pro|career))?|présentation|introduction"
        r"|accroche|profil$|executive\s*summary)",
    ],
    "experiences": [
        r"(?i)(expérience[s]?\s*(professionnelle[s]?)?|professional\s*experience"
        r"|work\s*experience|employment|parcours\s*professionnel"
        r"|postes?\s*occupés?|carrière|career\s*history)",
    ],
    "competences": [
        r"(?i)(compétence[s]?|skills?|savoir[s]?\s*faire|technical\s*skills?"
        r"|compétences?\s*techniques?|hard\s*skills?|soft\s*skills?"
        r"|outils?|technologies?|stack\s*technique|expertise)",
    ],
    "formations": [
        r"(?i)(formation[s]?|education|diplôme[s]?|cursus|études"
        r"|certifications?|parcours\s*académique|academic|qualifications?)",
    ],
    "langues": [
        r"(?i)(langue[s]?|languages?|linguistic)",
    ],
    "centres_interet": [
        r"(?i)(centre[s]?\s*d'intérêt|hobbies?|loisirs?|interests?"
        r"|activités?\s*extra|passions?)",
    ],
    "projets": [
        r"(?i)(projet[s]?|projects?|réalisations?|portfolio|open.?source)",
    ],
    "references": [
        r"(?i)(référence[s]?|references?|recommendations?)",
    ],
    "publications": [
        r"(?i)(publications?|articles?|recherche[s]?|research|papers?)",
    ],
}

REQUIRED_SECTIONS = {"resume", "experiences", "competences", "formations"}


# ── Core data structures ──────────────────────────────────────────────────────

@dataclass
class Chunk:
    """A single text chunk with metadata."""
    section: str
    index: int
    total_chunks: int
    text: str
    token_estimate: int
    preceding_context: str = ""
    is_overflow: bool = False

    @property
    def full_text(self) -> str:
        if self.preceding_context:
            return (
                f"[CONTEXTE PRÉCÉDENT]\n{self.preceding_context}"
                f"\n\n[CONTENU PRINCIPAL]\n{self.text}"
            )
        return self.text

    def __repr__(self) -> str:
        return (
            f"Chunk(section={self.section!r}, "
            f"idx={self.index}/{self.total_chunks - 1}, "
            f"~{self.token_estimate} tokens, overflow={self.is_overflow})"
        )


@dataclass
class CVSections:
    """Container returned by chunk_cv()."""
    chunks_by_section: Dict[str, List[Chunk]] = field(default_factory=dict)
    full_text: str = ""
    detected_sections: List[str] = field(default_factory=list)

    def get_section_text(
        self,
        section: str,
        max_tokens: int = MAX_TOKENS_PER_CHUNK,
        join_sep: str = "\n\n",
    ) -> str:
        chunks = self.chunks_by_section.get(section, [])
        if not chunks or sum(c.token_estimate for c in chunks) < 20:
            logger.warning(
                "[CVSections] Section '%s' absent. Using full_text window.", section
            )
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

    def get_first_chunk(self, section: str) -> Optional[Chunk]:
        chunks = self.chunks_by_section.get(section, [])
        return chunks[0] if chunks else None

    def section_token_count(self, section: str) -> int:
        return sum(c.token_estimate for c in self.chunks_by_section.get(section, []))

    def summary_report(self) -> str:
        lines = ["=== CV Chunking Report ==="]
        for sec, chunks in self.chunks_by_section.items():
            total_tok = sum(c.token_estimate for c in chunks)
            overflow_tag = (
                " [OVERFLOW → SPLIT]"
                if any(c.is_overflow for c in chunks)
                else ""
            )
            lines.append(
                f"  {sec:<20} {len(chunks)} chunk(s)  ~{total_tok} tokens{overflow_tag}"
            )
        return "\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_cv(full_text: str) -> CVSections:
    """
    Main entry-point.  Returns a CVSections object.

    Algorithm
    ─────────
    1. Detect section header lines via regex.
    2. Slice raw text between consecutive headers.
    3. For each raw slice:
         a. <= MAX_CHARS  → single Chunk
         b.  > MAX_CHARS  → adaptive split (experience blocks, paragraphs,
                             hard character split as last resort)
    4. Ensure all REQUIRED_SECTIONS exist with a full_text fallback.
    """
    result = CVSections(full_text=full_text)
    lines = full_text.splitlines()

    boundaries = _detect_boundaries(lines)
    logger.info("[Chunking] Detected %d section boundaries.", len(boundaries))

    raw_sections = _slice_sections(lines, boundaries)
    result.detected_sections = list(raw_sections.keys())

    for section_name, raw_text in raw_sections.items():
        new_chunks = _adaptive_chunk(section_name, raw_text)
        if section_name in result.chunks_by_section:
            existing = result.chunks_by_section[section_name]
            offset = len(existing)
            for c in new_chunks:
                c.index += offset
            result.chunks_by_section[section_name] = existing + new_chunks
        else:
            result.chunks_by_section[section_name] = new_chunks

    # Fix total_chunks after potential merging of duplicate sections
    for section_name, chunks in result.chunks_by_section.items():
        total = len(chunks)
        for c in chunks:
            c.total_chunks = total

    # Fallback for required but absent sections
    for sec in REQUIRED_SECTIONS:
        if sec not in result.chunks_by_section:
            logger.warning(
                "[Chunking] Required section '%s' not found. Injecting fallback.", sec
            )
            fallback_text = (
                f"[Section '{sec}' non détectée — contenu complet du CV]\n\n"
                + _window(full_text, MAX_TOKENS_PER_CHUNK)
            )
            result.chunks_by_section[sec] = [
                Chunk(
                    section=sec,
                    index=0,
                    total_chunks=1,
                    text=fallback_text,
                    token_estimate=_tokens(fallback_text),
                    is_overflow=False,
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
    """
    Compose optimal input string for an agent within a token budget.
    primary_section fills the budget first; context_sections are appended
    in order until the budget is exhausted.
    """
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


# ── Backward-compatible interfaces ────────────────────────────────────────────

def chunk_cv_by_sections(full_text: str) -> Dict[str, str]:
    """
    Legacy dict interface used by the current orchestrator.
    Returns {section_name: joined_text, 'full_text': full_text}.
    """
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
    """
    Legacy helper used by the current orchestrator.
    Retrieves section text, falling back to full_text, truncated to max_chars.
    """
    content = sections.get(section_name, "")
    if len(content) < 100:
        content = sections.get("full_text", "")
    return _truncate_chars(content, max_chars)


# ── Internal helpers ──────────────────────────────────────────────────────────

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
    boundaries: List[Tuple[int, str]] = []
    seen_at: Dict[str, int] = {}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
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


def _adaptive_chunk(section_name: str, raw_text: str) -> List[Chunk]:
    """Split raw_text into Chunks, respecting MAX_CHARS."""
    if len(raw_text) <= MAX_CHARS:
        return [
            Chunk(
                section=section_name,
                index=0,
                total_chunks=1,
                text=raw_text,
                token_estimate=_tokens(raw_text),
                is_overflow=False,
            )
        ]

    logger.info(
        "[Chunking] Section '%s' (%d chars). Splitting adaptively.",
        section_name, len(raw_text),
    )

    if section_name == "experiences":
        blocks = _split_by_experience_blocks(raw_text)
    else:
        blocks = _split_by_paragraphs(raw_text)

    normalised = _normalise_blocks(blocks)

    chunks: List[Chunk] = []
    prev_tail = ""

    for i, block in enumerate(normalised):
        preceding = _make_context_header(prev_tail) if prev_tail else ""
        chunks.append(
            Chunk(
                section=section_name,
                index=i,
                total_chunks=len(normalised),
                text=block,
                token_estimate=_tokens(block),
                preceding_context=preceding,
                is_overflow=True,
            )
        )
        prev_tail = block[-OVERLAP_CHARS:] if len(block) > OVERLAP_CHARS else block

    return chunks


def _split_by_experience_blocks(text: str) -> List[str]:
    """Split on lines that look like experience anchors (caps title or year)."""
    ANCHOR = re.compile(
        r"(?m)^(?:"
        r"[A-ZÁÀÂÉÈÊÎÏÔÙÛÜ][^\n]{5,60}(?:[-–|@•]|chez|at)\s*\S"
        r"|.*\b(19|20)\d{2}\b.*"
        r")$"
    )
    positions = [m.start() for m in ANCHOR.finditer(text)]

    if len(positions) < 2:
        return _split_by_paragraphs(text)

    blocks: List[str] = []
    if positions[0] > 0:
        blocks.append(text[: positions[0]].strip())
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[pos:end].strip())

    return [b for b in blocks if b]


def _split_by_paragraphs(text: str) -> List[str]:
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _normalise_blocks(blocks: List[str]) -> List[str]:
    """Merge tiny blocks; hard-split oversized ones."""
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
        if len(block) <= MAX_CHARS:
            result.append(block)
        else:
            result.extend(_hard_split(block))
    return result


def _hard_split(text: str) -> List[str]:
    """Last-resort split on character count with newline-aware boundary."""
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
