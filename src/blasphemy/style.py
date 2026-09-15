import re

# words the reader never wants in rewritten prose; a stem present in the
# source chapter is the author's and stays allowed
BANNED_STEMS = {
    "gate": r"gat(?:e|es|ed|ing)",
    "provenance": r"provenances?",
    "delve": r"delv(?:e|es|ed|ing)",
}


def _present(stem: str, text: str) -> bool:
    return re.search(rf"\b{BANNED_STEMS[stem]}\b", text, re.I) is not None


def banned(source_md: str, output_md: str) -> list[str]:
    return [
        stem for stem in BANNED_STEMS
        if _present(stem, output_md) and not _present(stem, source_md)
    ]
