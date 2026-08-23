import re

from bs4 import BeautifulSoup

PROTECTED_TAGS = ["math", "svg"]
GIST_MAX = 60


def _token_re(kind: str, block_id: int) -> re.Pattern:
    # tolerant of an edited/escaped/dropped gist, strict on the id
    return re.compile(rf"⟦{kind}-{block_id}(?:[^⟦⟧]*)⟧")


def _gist(node) -> str:
    if node.name == "svg":
        for tag in ("title", "desc"):
            found = node.find(tag)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)[:GIST_MAX]
    text = node.get_text(" ", strip=True)
    text = re.sub(r"[⟦⟧\s]+", lambda m: " " if m.group().isspace() else "", text)
    return text[:GIST_MAX] or "diagram"


def protect(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = {}
    for block_id, node in enumerate(soup.find_all(PROTECTED_TAGS)):
        if node.find_parent(PROTECTED_TAGS):
            continue
        kind = node.name.upper()
        key = f"{kind}-{block_id}"
        blocks[key] = str(node)
        node.replace_with(f"⟦{key}: {_gist(node)}⟧")
    return str(soup), blocks


def restore(html: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    missing = []
    for key, original in blocks.items():
        kind, block_id = key.rsplit("-", 1)
        pattern = _token_re(kind, int(block_id))
        html, count = pattern.subn(original.replace("\\", r"\\"), html, count=1)
        if count == 0:
            missing.append(key)
        else:
            html = pattern.sub("", html)
    return html, missing
