import re

from bs4 import BeautifulSoup

ALWAYS_PROTECTED = ["math", "svg"]
GIST_MAX = 60
HEADINGS = ["h1", "h2", "h3"]
# a lone block element inside <p> is invalid; unwrap it after restoring
BLOCK_LEVEL = (
    "figure", "table", "pre", "div", "p", "header", "h1", "h2", "h3", "aside", "section",
)
# publisher callouts: No Starch <aside epub:type="sidebar"><section class="note">,
# DocBook/O'Reilly <div class="note|tip|warning|caution|important|sidebar">
CALLOUT_CLASSES = re.compile(r"^(note|tip|warning|caution|important|sidebar|box)$", re.I)
CALLOUT_LABELS = re.compile(r"^(note|tip|warning|caution|important)s?$", re.I)
# wrappers an image's styling can hang off
IMAGE_WRAPPERS = ("figure", "div", "p", "span", "a")
PLAIN_IMG_ATTRS = {"src", "alt"}


def _image_only(node, image) -> bool:
    """True when `node` holds this image and no text or second image.

    Empty markers are tolerated: DocBook wraps images as
    `<div class="mediaobject"><a id="med_id1"></a><img/></div>`.
    """
    if node.get_text(strip=True):
        return False
    images = node.find_all("img")
    return len(images) == 1 and images[0] is image


def _wrap_target(image):
    """Smallest element carrying this image's styling.

    Markdown expresses `src` and `alt` and nothing else, so whatever holds the
    styling — a wrapper class or an attribute on the image — must travel as a
    token. Climb only through wrappers holding the image alone, so a section
    div full of prose is never swallowed; figures are taken whole so their
    <figcaption> comes along. Figures without an image stay markdown, keeping
    table figures readable and compressible by the model.
    """
    node = image
    while node.parent is not None:
        parent = node.parent
        if parent.name == "figure":
            return parent
        if parent.name in IMAGE_WRAPPERS and _image_only(parent, image):
            node = parent
            continue
        break
    return node


def _worth_protecting(target, image) -> bool:
    if target.name == "figure":
        return True
    if set(image.attrs) - PLAIN_IMG_ATTRS:
        return True  # class/id/style on the image itself
    return target is not image and bool(target.attrs)  # classed wrapper


def _token_re(kind: str, block_id: int) -> re.Pattern:
    # tolerant of an edited/escaped/dropped gist, strict on the id:
    # the char after the id must not be a digit, so PRE-1 never eats PRE-10
    return re.compile(rf"⟦{kind}-{block_id}(?:[^0-9⟦⟧][^⟦⟧]*)?⟧")


def _is_callout(node) -> bool:
    if node.name == "aside" and "sidebar" in (node.get("epub:type") or ""):
        return True
    if node.name in ("div", "section", "aside"):
        return any(CALLOUT_CLASSES.match(cls) for cls in node.get("class", []))
    return False


def _callout_label(node) -> str:
    # the visible label ("Note", "Tips", "Warning") when the callout has one
    head = node.find(["h1", "h2", "h3", "h4", "h5", "h6"]) or node.find(
        ["p", "span"], class_=re.compile("title|head", re.I)
    )
    text = head.get_text(" ", strip=True) if head else ""
    if not text:
        for cls in node.get("class", []):
            if CALLOUT_LABELS.match(cls):
                text = cls.capitalize()
    return text[:20]


def _gist(node) -> str:
    if node.name == "svg":
        for tag in ("title", "desc"):
            found = node.find(tag)
            if found and found.get_text(strip=True):
                return found.get_text(strip=True)[:GIST_MAX]
    caption = node.find("figcaption") if node.name != "img" else None
    if caption and caption.get_text(" ", strip=True):
        return caption.get_text(" ", strip=True)[:GIST_MAX]
    image = node if node.name == "img" else node.find("img")
    if image is not None:
        return ((image.get("alt") or "").strip() or "image")[:GIST_MAX]
    text = node.get_text(" ", strip=True)
    text = re.sub(r"[⟦⟧\s]+", lambda m: " " if m.group().isspace() else "", text)
    return text[:GIST_MAX] or "diagram"


def _chapter_title(soup):
    """The chapter's title block, when its markup carries styling.

    Publishers hang layout off the title: number/title spans, centring, a
    bottom margin the opener art floats into. `# Title` loses all of it and
    the art ends up over the heading. A plain `<h1>text</h1>` is left to
    markdown, which reproduces it exactly.
    """
    heading = next(
        (
            h for h in soup.find_all(HEADINGS)
            if not any(_is_callout(p) for p in h.find_parents(["aside", "div", "section"]))
        ),
        None,
    )  # a note's own "Note" heading is not the chapter title
    if heading is None:
        return None
    header = heading.find_parent("header")
    target = header if header is not None else heading
    styled = bool(target.attrs) or any(
        child.attrs for child in target.find_all(True)
    )
    return target if styled else None


def protect(html: str) -> tuple[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    wanted = {id(node): node for node in soup.find_all(ALWAYS_PROTECTED)}
    title = _chapter_title(soup)
    if title is not None:
        wanted[id(title)] = title
    for image in soup.find_all("img"):
        target = _wrap_target(image)
        if _worth_protecting(target, image):
            wanted[id(target)] = target

    blocks = {}
    protected_ids: set[int] = set()
    counter = 0
    for node in soup.find_all(True):  # document order keeps token ids readable
        if id(node) not in wanted:
            continue
        if any(id(parent) in protected_ids for parent in node.parents):
            continue
        if node is title:
            # own id space: the title must not shift the numbering of
            # figures and formulas, or every cached rewrite stops matching
            key = "TITLE-0"
        else:
            key = f"{node.name.upper()}-{counter}"
            counter += 1
        blocks[key] = str(node)
        protected_ids.add(id(node))
        node.replace_with(f"⟦{key}: {_gist(node)}⟧")
    return str(soup), blocks


def carry_lead_class(html: str, original_html: str) -> str:
    """Give the rewrite's first paragraph the original lead paragraph's class.

    Publishers style the chapter opener's lead paragraph (larger type, no
    indent, drop cap); it is rewritten, so its class has to be re-applied.
    """
    source = BeautifulSoup(original_html, "html.parser")
    heading = source.find(HEADINGS)
    lead = heading.find_next("p") if heading is not None else source.find("p")
    if lead is None or not lead.get("class"):
        return html
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(HEADINGS)
    first = heading.find_next("p") if heading is not None else soup.find("p")
    while first is not None and not first.get_text(strip=True):
        first = first.find_next("p")  # skip anchor-only paragraphs
    if first is None or first.get("class"):
        return html
    first["class"] = lead["class"]
    return str(soup)


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


def _retitle(html: str, original: str) -> str:
    """Swap the rewrite's own heading for the original styled title.

    Rescues rewrites cached before titles were protected (they carry a bare
    `# Title`) and any run where the model writes a heading instead of the
    token. With no heading to replace, the title goes on top: it has exactly
    one right place, so this never fails a chapter.
    """
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(HEADINGS)
    title = BeautifulSoup(original, "html.parser")
    if heading is not None:
        heading.replace_with(title)
        return str(soup)
    return original + html


def _dress(heading, shell_html: str) -> bool:
    """Put the paragraphs after `heading` inside the publisher's callout shell."""
    paragraphs = []
    sibling = heading.find_next_sibling()
    while sibling is not None and sibling.name == "p":
        paragraphs.append(sibling)
        sibling = sibling.find_next_sibling()
    if not paragraphs:
        return False
    callout = BeautifulSoup(shell_html, "html.parser").find(True)
    body_paras = [
        p for p in callout.find_all("p") if not p.find_parent(class_=re.compile("hr"))
    ]
    anchor = body_paras[0] if body_paras else None
    for p in body_paras[1:]:
        p.decompose()
    for p in paragraphs:
        fresh = p.extract()
        if anchor is not None:
            anchor.insert_before(fresh)
        else:
            callout.append(fresh)
    if anchor is not None:
        anchor.decompose()
    heading.replace_with(callout)
    return True


def restyle_notes(html: str, original_html: str) -> str:
    """Re-box notes the model chose to keep as `## Note` + paragraphs.

    Notes are chapter content: the rewrite is free to dissolve them into the
    prose, gather them into an asides section, or keep them. This only
    touches the last case, where the markdown round trip has already turned
    the publisher's boxed callout into a bare heading and paragraphs — the
    original callout of the same label is reused as the shell, its body
    swapped for the rewritten paragraphs, so label, rules and classes return
    while the model's text stays.
    """
    shells = {}
    for node in BeautifulSoup(original_html, "html.parser").find_all(["aside", "div", "section"]):
        if _is_callout(node) and not node.find_parent(["aside"]):
            label = _callout_label(node).casefold()
            if label:
                shells.setdefault(label, str(node))
    if not shells:
        return html
    soup = BeautifulSoup(html, "html.parser")
    changed = False
    for heading in soup.find_all(["h2", "h3", "h4"]):
        shell = shells.get(heading.get_text(" ", strip=True).casefold())
        if shell is None:
            continue
        parent = heading.find_parent(["aside", "div", "section"])
        if parent is not None and _is_callout(parent):
            continue  # already boxed
        changed = _dress(heading, shell) or changed
    return str(soup) if changed else html


ANY_TOKEN = re.compile(r"⟦[^⟦⟧]*⟧")


def strip_tokens(html: str) -> str:
    """Drop tokens nothing could restore (e.g. a cache from an older run)."""
    return ANY_TOKEN.sub("", html)


def _caption_key(text: str) -> str:
    # whitespace-free: inline markup makes get_text insert stray spaces
    # ("Figure 1-1 : x" from <a>Figure 1-1</a>: x)
    return "".join(ANY_TOKEN.sub("", text).split()).casefold()


def _drop_duplicate_captions(html: str) -> str:
    """Remove a caption the model also wrote as prose beside its figure.

    A rewrite made before figures were protected keeps the caption as a
    paragraph; restoring the figure brings the original <figcaption> back and
    the reader sees it twice.
    """
    soup = BeautifulSoup(html, "html.parser")
    for figure in soup.find_all("figure"):
        caption = figure.find("figcaption")
        if caption is None:
            continue
        key = _caption_key(caption.get_text(" ", strip=True))
        if not key:
            continue
        for sibling in (figure.find_next_sibling(), figure.find_previous_sibling()):
            if sibling is None or sibling.name not in ("p", "div"):
                continue
            if _caption_key(sibling.get_text(" ", strip=True)) == key:
                sibling.decompose()
                break
    return str(soup)


def _unwrap_block_paragraphs(html: str) -> str:
    # adjacent tokens (a title then its opener art) share one markdown
    # paragraph, so a <p> may hold several restored blocks and nothing else
    soup = BeautifulSoup(html, "html.parser")
    for para in soup.find_all("p"):
        children = [
            child
            for child in para.children
            if getattr(child, "name", None) or str(child).strip()
        ]
        if children and all(
            getattr(child, "name", None) in BLOCK_LEVEL for child in children
        ):
            para.replace_with(*children)
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
        if kind == "TITLE":
            html = _retitle(html, original)
            continue
        html, rewrapped = _rewrap_image(html, original)
        if not rewrapped:
            missing.append(key)
    if blocks:
        html = _drop_duplicate_captions(_unwrap_block_paragraphs(html))
    return html, missing


CAPTION_LABEL = re.compile(r"^\s*(figure|table|listing|example)\s+[\dA-Z]+[-.–]\d+", re.I)


def _caption_label(text: str) -> str | None:
    match = CAPTION_LABEL.match(ANY_TOKEN.sub("", text))
    return "".join(match.group().split()).casefold() if match else None


def _captions(soup) -> dict[str, tuple]:
    """Original caption markup by label ("table2-1"), with its figure wrapper."""
    found = {}
    for node in soup.find_all(["figcaption", "p"]):
        if node.name == "p" and not (node.get("class") or node.find_parent("figcaption")):
            continue
        if node.find_parent("figcaption") is not None:
            continue  # the figcaption itself is recorded
        figure = node.find_parent("figure")
        if figure is not None and figure.find("img"):
            continue  # travels inside its protected figure already
        label = _caption_label(node.get_text(" ", strip=True))
        if label and label not in found:
            wraps_table = bool(figure is not None and figure.find("table"))
            found[label] = (node, figure if wraps_table else None)
    return found


def restore_captions(html: str, original_html: str) -> str:
    """Re-apply publisher caption markup the markdown round trip flattened.

    Listing captions (`p.CodeListingCaption`) and table titles
    (`figcaption.TableTitle` inside a `<figure>` wrapping the table) come back
    as plain paragraphs; the CSS hooks that set their face and spacing hang
    off exactly those classes. Match by the caption's label ("Table 2-1")
    and copy the original element over the rewritten paragraph, re-wrapping
    an adjacent table into its original `<figure>`.
    """
    originals = _captions(BeautifulSoup(original_html, "html.parser"))
    if not originals:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for para in soup.find_all("p"):
        if para.get("class") or para.find_parent(["figure", "figcaption"]):
            continue
        label = _caption_label(para.get_text(" ", strip=True))
        entry = originals.pop(label, None) if label else None
        if entry is None:
            continue
        caption, figure = entry
        replacement = BeautifulSoup(str(caption), "html.parser")
        if figure is not None:
            table = para.find_next_sibling()
            if table is not None and table.name == "table":
                wrapper = soup.new_tag("figure", **{
                    k: v for k, v in figure.attrs.items()
                })
                para.insert_before(wrapper)
                wrapper.append(replacement)
                wrapper.append(table.extract())
                para.decompose()
                continue
        para.replace_with(replacement)
    return str(soup)


def extract_pre(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [str(pre) for pre in soup.find_all("pre")]


def _code_key(html: str) -> str:
    return " ".join(BeautifulSoup(html, "html.parser").get_text().split())


def restore_pre(html: str, originals: list[str]) -> tuple[str, int]:
    """Swap regenerated fenced code back for the original pre markup.

    Listing annotations, bolded input and styled spans live only in the
    original. Blocks are matched by their text, so a listing the model
    dropped or merged costs that listing alone; whatever is left unmatched
    is paired in order when the leftover counts agree (the model edited the
    code slightly) and otherwise stays fenced. Returns how many stayed.
    """
    if not originals:
        return html, 0
    soup = BeautifulSoup(html, "html.parser")
    pres = soup.find_all("pre")
    pool = {}
    for original in originals:
        pool.setdefault(_code_key(original), []).append(original)
    leftover_pres = []
    for pre in pres:
        candidates = pool.get(_code_key(str(pre)))
        if candidates:
            pre.replace_with(BeautifulSoup(candidates.pop(0), "html.parser"))
        else:
            leftover_pres.append(pre)
    leftover_originals = [o for group in pool.values() for o in group]
    if leftover_pres and len(leftover_pres) == len(leftover_originals):
        # same count, different text: lightly edited in place — but only
        # trust the pairing when the code actually overlaps
        ordered = [o for o in originals if o in leftover_originals]
        pairs = list(zip(leftover_pres, ordered))
        if all(_similar(_code_key(str(p)), _code_key(o)) for p, o in pairs):
            for pre, original in pairs:
                pre.replace_with(BeautifulSoup(original, "html.parser"))
            leftover_pres = []
    return str(soup), len(leftover_pres)


def _similar(a: str, b: str) -> bool:
    words_a, words_b = set(a.split()), set(b.split())
    if not words_a or not words_b:
        return False
    return len(words_a & words_b) / max(len(words_a), len(words_b)) >= 0.6


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
