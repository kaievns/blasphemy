import re

from bs4 import BeautifulSoup

PROTECTED_TAGS = ["math", "svg", "figure"]
GIST_MAX = 60
# a lone block element inside <p> is invalid; unwrap it after restoring
BLOCK_LEVEL = ("figure", "table", "pre", "div")


def _protectable(node) -> bool:
    # Figures are protected only when they carry an image, because that is
    # where the wrapper's styling lives (figure.opener floats the chapter art
    # at 20% width; flattened to a bare <img> it renders full size). Figures
    # wrapping tables stay markdown so the model can still read and compress
    # them.
    return node.name != "figure" or node.find("img") is not None


def _token_re(kind: str, block_id: int) -> re.Pattern:
    # tolerant of an edited/escaped/dropped gist, strict on the id:
    # the char after the id must not be a digit, so PRE-1 never eats PRE-10
    return re.compile(rf"⟦{kind}-{block_id}(?:[^0-9⟦⟧][^⟦⟧]*)?⟧")


def _gist(node) -> str:
    if node.name == "svg":
        for tag in ("title", "desc"):
            found = node.find(tag)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)[:GIST_MAX]
    if node.name == "figure":
        caption = node.find("figcaption")
        if caption and caption.get_text(" ", strip=True):
            return caption.get_text(" ", strip=True)[:GIST_MAX]
        image = node.find("img")
        alt = (image.get("alt") or "").strip() if image else ""
        return (alt or "image")[:GIST_MAX]
    text = node.get_text(" ", strip=True)
    text = re.sub(r"[⟦⟧\s]+", lambda m: " " if m.group().isspace() else "", text)
    return text[:GIST_MAX] or "diagram"


def protect(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = {}
    protected_ids: set[int] = set()
    for block_id, node in enumerate(soup.find_all(PROTECTED_TAGS)):
        if not _protectable(node):
            continue
        if any(id(parent) in protected_ids for parent in node.parents):
            continue
        kind = node.name.upper()
        key = f"{kind}-{block_id}"
        blocks[key] = str(node)
        protected_ids.add(id(node))
        node.replace_with(f"⟦{key}: {_gist(node)}⟧")
    return str(soup), blocks


def _unescape_tokens(html: str) -> str:
    # markdown escaping can add backslashes inside token spans
    return re.sub(r"⟦[^⟦⟧]*⟧", lambda m: m.group().replace("\\", ""), html)


def _image_src(fragment: str) -> str | None:
    match = re.search(r'<img[^>]+src="([^"]+)"', fragment)
    return match.group(1) if match else None


def _rewrap_image(html: str, original: str) -> tuple[str, bool]:
    """Re-apply a dropped figure wrapper to its image, matched by src.

    Rescues output written before figures were protected (cached rewrites)
    and any run where the model drops the token but keeps the markdown image.
    """
    src = _image_src(original)
    if not src:
        return html, False
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        if image.get("src") != src:
            continue
        target = image
        parent = image.parent
        if parent and parent.name == "p" and not parent.get_text(strip=True):
            target = parent
        target.replace_with(BeautifulSoup(original, "html.parser"))
        return str(soup), True
    return html, False


def _unwrap_block_paragraphs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for para in soup.find_all("p"):
        children = [
            child
            for child in para.children
            if getattr(child, "name", None) or str(child).strip()
        ]
        if len(children) == 1 and getattr(children[0], "name", None) in BLOCK_LEVEL:
            para.replace_with(children[0])
    return str(soup)


def restore(html: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    html = _unescape_tokens(html)
    missing = []
    for key, original in blocks.items():
        kind, block_id = key.rsplit("-", 1)
        pattern = _token_re(kind, int(block_id))
        html, count = pattern.subn(original.replace("\\", r"\\"), html, count=1)
        if count:
            html = pattern.sub("", html)
            continue
        html, rewrapped = _rewrap_image(html, original)
        if not rewrapped:
            missing.append(key)
    if blocks:
        html = _unwrap_block_paragraphs(html)
    return html, missing


def extract_pre(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [str(pre) for pre in soup.find_all("pre")]


def restore_pre(html: str, originals: list[str]) -> tuple[str, bool]:
    # swap regenerated fenced code back for the original pre markup
    # (listing annotations, bolded input, styled spans survive)
    if not originals:
        return html, True
    soup = BeautifulSoup(html, "html.parser")
    pres = soup.find_all("pre")
    if len(pres) != len(originals):
        return html, False
    for pre, original in zip(pres, originals):
        pre.replace_with(BeautifulSoup(original, "html.parser"))
    return str(soup), True


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
