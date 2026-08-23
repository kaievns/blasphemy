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


def _unescape_tokens(html: str) -> str:
    # markdown escaping can add backslashes inside token spans
    return re.sub(r"⟦[^⟦⟧]*⟧", lambda m: m.group().replace("\\", ""), html)


def restore(html: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    html = _unescape_tokens(html)
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


def protect_anchors(html: str, ids: set[str]) -> tuple[str, list[str]]:
    if not ids:
        return html, []
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for element in soup.find_all(id=True):
        anchor_id = element.get("id")
        if anchor_id in ids and anchor_id not in found:
            element.insert_before(f"⟦ANCHOR:{anchor_id}⟧")
            found.append(anchor_id)
    return str(soup), found


def restore_anchors(html: str, ids: list[str]) -> tuple[str, list[str]]:
    html = _unescape_tokens(html)
    missing = []
    for anchor_id in ids:
        pattern = re.compile(rf"⟦ANCHOR:{re.escape(anchor_id)}⟧")
        html, count = pattern.subn(f'<a id="{anchor_id}"></a>', html, count=1)
        if count == 0:
            missing.append(anchor_id)
        else:
            html = pattern.sub("", html)
    # a fallback anchor at the chapter top beats a broken link
    if missing:
        fallback = "".join(f'<a id="{a}"></a>' for a in missing)
        html = fallback + html
    return html, missing
