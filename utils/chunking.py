"""
Semantic chunking utility for CV content.
Splits CV text into meaningful sections for targeted agent processing.
"""

import re
from typing import Dict, Optional


# Common section headers in French and English CVs
SECTION_PATTERNS = {
    "resume": [
        r"(?i)(profil|résumé|summary|about\s*me|à\s*propos|objectif|présentation|introduction|accroche)",
    ],
    "experiences": [
        r"(?i)(expérience[s]?\s*(professionnelle[s]?)?|professional\s*experience|work\s*experience|parcours\s*professionnel|postes?\s*occupés?)",
    ],
    "competences": [
        r"(?i)(compétence[s]?|skills?|savoir[s]?\s*faire|technical\s*skills?|compétences?\s*techniques?|hard\s*skills?|soft\s*skills?|outils?|technologies?|stack\s*technique)",
    ],
    "formations": [
        r"(?i)(formation[s]?|education|diplôme[s]?|cursus|études|certifications?|parcours\s*académique)",
    ],
    "langues": [
        r"(?i)(langue[s]?|languages?)",
    ],
    "centres_interet": [
        r"(?i)(centre[s]?\s*d'intérêt|hobbies?|loisirs?|interests?|activités?\s*extra)",
    ],
    "projets": [
        r"(?i)(projet[s]?|projects?|réalisations?|portfolio)",
    ],
    "references": [
        r"(?i)(référence[s]?|references?)",
    ],
}


def chunk_cv_by_sections(full_text: str) -> Dict[str, str]:
    """
    Split CV text into semantic sections.
    Returns a dict with section names as keys and content as values.
    Always includes 'full_text' key with complete content.
    """
    sections: Dict[str, str] = {"full_text": full_text}
    lines = full_text.split("\n")

    # Find section boundaries
    section_boundaries = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            continue
        for section_name, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, stripped):
                    section_boundaries.append((i, section_name))
                    break

    # Sort by line number
    section_boundaries.sort(key=lambda x: x[0])

    # Extract content between boundaries
    for idx, (line_num, section_name) in enumerate(section_boundaries):
        if idx + 1 < len(section_boundaries):
            next_line = section_boundaries[idx + 1][0]
        else:
            next_line = len(lines)

        content = "\n".join(lines[line_num:next_line]).strip()
        if section_name in sections:
            sections[section_name] += "\n\n" + content
        else:
            sections[section_name] = content

    # If no sections were found, put everything in experiences and resume
    if len(sections) == 1:  # Only full_text
        sections["resume"] = full_text[:2000]
        sections["experiences"] = full_text
        sections["competences"] = full_text
        sections["formations"] = full_text

    # Ensure all required sections exist with fallback
    for key in ["resume", "experiences", "competences", "formations"]:
        if key not in sections:
            sections[key] = f"[Section '{key}' non détectée dans le CV. Contenu complet fourni pour analyse.]\n\n{full_text}"

    return sections


def get_section_or_full(sections: Dict[str, str], section_name: str, max_chars: int = 15000) -> str:
    """
    Get a specific section, falling back to full text if section is too short.
    Truncates to max_chars to respect context window limits.
    """
    content = sections.get(section_name, "")
    if len(content) < 100:
        content = sections.get("full_text", "")

    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[... TRONQUÉ pour respecter la fenêtre de contexte ...]"

    return content
