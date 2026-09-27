import html
import re
import unicodedata

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from markdownify import MarkdownConverter, chomp
from mdit_py_plugins.deflist import deflist_plugin

BACKTICK_RUN = re.compile(r"`+")
BLOCK_MARKER = re.compile(r"^(\d+)([.)])(?=\s|$)|^([-+*])(?=\s|$)|^(#+)(?=\s|$)|^(>)")
NUMBERED_START = re.compile(r"^(\s*\d+)([.)])(?=\s)")
EMPHASIS = ("em", "i", "strong", "b")
TAG_NAME = re.compile(r"<\s*/?\s*([A-Za-z][\w.-]*)")
HTML_ELEMENTS = frozenset(
    "a abbr address article aside b bdi bdo blockquote br caption cite code col "
    "colgroup dd del details dfn div dl dt em figcaption figure footer h1 h2 h3 "
    "h4 h5 h6 header hr i img ins kbd li main mark nav ol p pre q rp rt ruby "
    "s samp section small span strong sub summary sup table tbody td tfoot th "
    "thead time tr u ul var wbr".split()
)


class _Converter(MarkdownConverter):
    # markdown has no syntax for these; inline HTML survives the round trip,
    # except inside code, where it would show as literal tags
    def _inline(self, tag, text, parent_tags):
        if parent_tags and {"pre", "code"} & set(parent_tags):
            return text
        return f"<{tag}>{text}</{tag}>"

    def convert_sup(self, el, text, parent_tags=None, *args, **kwargs):
        return self._inline("sup", text, parent_tags)

    def convert_sub(self, el, text, parent_tags=None, *args, **kwargs):
        return self._inline("sub", text, parent_tags)

    def convert_u(self, el, text, parent_tags=None, *args, **kwargs):
        return self._inline("u", text, parent_tags)

    def convert_var(self, el, text, parent_tags=None, *args, **kwargs):
        # placeholders are usually written <like-this>; unescaped they would
        # come back as a fake tag and the reader swallows them
        if parent_tags and {"pre", "code"} & set(parent_tags):
            return text
        return f"<var>{html.escape(text, quote=False)}</var>"

    def convert_dt(self, el, text, parent_tags=None, *args, **kwargs):
        # a term like "1) No automation" would open a list and end the <dl>
        term = super().convert_dt(el, text, parent_tags or set(), *args, **kwargs)
        if not term.strip():
            return term
        head, line, tail = term.partition(term.strip())
        return f"{head}{_escape_marker(line)}{tail}"

    def convert_p(self, el, text, parent_tags=None, *args, **kwargs):
        # prose opening "2) …" or "2021. …" would start an ordered list
        para = super().convert_p(el, text, parent_tags or set(), *args, **kwargs)
        return NUMBERED_START.sub(lambda m: f"{m.group(1)}\\{m.group(2)}", para, count=1) if para.strip() else para

    def convert_td(self, el, text, parent_tags=None, *args, **kwargs):
        # a | inside a cell, code spans included, would split the cell
        return super().convert_td(el, text.replace("|", "\\|"), parent_tags or set(), *args, **kwargs)

    def convert_th(self, el, text, parent_tags=None, *args, **kwargs):
        return super().convert_th(el, text.replace("|", "\\|"), parent_tags or set(), *args, **kwargs)

    def _emphasis(self, el, text, parent_tags, base):
        markdown = base(self, el, text, parent_tags or set())
        prefix, suffix, inner = chomp(text)
        if not inner or (parent_tags and "_noformat" in parent_tags):
            return markdown
        before = prefix[-1:] or _neighbour(el, -1)
        after = suffix[:1] or _neighbour(el, 1)
        # CommonMark will not open or close emphasis on punctuation that
        # touches a letter outside it; inline HTML says the same thing safely
        if (_punct(inner[0]) and before.isalnum()) or (_punct(inner[-1]) and after.isalnum()):
            return f"{prefix}<{el.name}>{inner}</{el.name}>{suffix}"
        return markdown

    def convert_em(self, el, text, parent_tags=None, *args, **kwargs):
        return self._emphasis(el, text, parent_tags, MarkdownConverter.convert_em)

    def convert_i(self, el, text, parent_tags=None, *args, **kwargs):
        return self._emphasis(el, text, parent_tags, MarkdownConverter.convert_i)

    def convert_strong(self, el, text, parent_tags=None, *args, **kwargs):
        return self._emphasis(el, text, parent_tags, MarkdownConverter.convert_strong)

    def convert_b(self, el, text, parent_tags=None, *args, **kwargs):
        return self._emphasis(el, text, parent_tags, MarkdownConverter.convert_b)

    def convert_pre(self, el, text, *args, **kwargs):
        fenced = super().convert_pre(el, text, *args, **kwargs)
        longest = max((len(run) for run in BACKTICK_RUN.findall(text or "")), default=0)
        if longest < 3:
            return fenced
        fence = "`" * (longest + 1)
        head, _, rest = fenced.partition("```")
        body, _, tail = rest.rpartition("```")
        return f"{head}{fence}{body}{fence}{tail}"


def _escape_marker(line: str) -> str:
    def escape(m):
        if m.group(1):
            return f"{m.group(1)}\\{m.group(2)}"
        return "\\" + next(g for g in m.groups()[2:] if g)
    return BLOCK_MARKER.sub(escape, line, count=1)


def _punct(char: str) -> bool:
    return bool(char) and unicodedata.category(char)[0] in "PS"


INLINE = frozenset("a abbr b bdi cite code em i kbd mark q s samp small span strong sub sup u var".split())


def _neighbour(el, step: int) -> str:
    """The character just outside `el`, looking through inline wrappers."""
    node = el
    while node is not None:
        sibling = node.previous_sibling if step < 0 else node.next_sibling
        while sibling is not None:
            text = sibling.get_text() if hasattr(sibling, "get_text") else str(sibling)
            if text:
                return text[-1] if step < 0 else text[0]
            sibling = sibling.previous_sibling if step < 0 else sibling.next_sibling
        node = node.parent if node.parent is not None and node.parent.name in INLINE else None
    return " "


def _merge_adjacent_emphasis(soup) -> None:
    # <em>co</em><em>mpile</em> would become *co**mpile*
    for node in soup.find_all(EMPHASIS):
        while node.parent is not None:
            nxt = node.next_sibling
            if getattr(nxt, "name", None) != node.name or nxt.attrs != node.attrs:
                break
            for child in list(nxt.children):
                node.append(child.extract())
            nxt.decompose()


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    _merge_adjacent_emphasis(soup)
    body = soup.body or soup
    return _Converter(heading_style="ATX").convert(str(body)).strip()


def _known(markup: str) -> bool:
    match = TAG_NAME.match(markup.strip())
    return bool(match) and match.group(1).lower() in HTML_ELEMENTS


def _html_inline(self, tokens, idx, options, env):
    content = tokens[idx].content
    return content if _known(content) else html.escape(content, quote=False)


def _html_block(self, tokens, idx, options, env):
    content = tokens[idx].content
    if _known(content):
        return content
    return f"<p>{html.escape(content.strip(), quote=False)}</p>\n"


_MD = (
    MarkdownIt("commonmark", {"html": True, "xhtmlOut": True})
    .enable("table")
    .use(deflist_plugin)
)
_MD.add_render_rule("html_inline", _html_inline)
_MD.add_render_rule("html_block", _html_block)


def markdown_to_html(markdown: str) -> str:
    return _MD.render(markdown)
