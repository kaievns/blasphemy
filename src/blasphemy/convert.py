import html
import re

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from markdownify import MarkdownConverter
from mdit_py_plugins.deflist import deflist_plugin

BACKTICK_RUN = re.compile(r"`+")
BLOCK_MARKER = re.compile(r"^(\d+)([.)])|^([-+*#>])")
TAG_NAME = re.compile(r"<\s*/?\s*([A-Za-z][\w.-]*)")
HTML_ELEMENTS = frozenset(
    "a abbr address article aside b bdi bdo blockquote br caption cite code col "
    "colgroup dd del details dfn div dl dt em figcaption figure footer h1 h2 h3 "
    "h4 h5 h6 header hr i img ins kbd li main mark math nav ol p pre q rp rt ruby "
    "s samp section small span strong sub summary sup svg table tbody td tfoot th "
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
        line = BLOCK_MARKER.sub(lambda m: f"{m.group(1)}\\{m.group(2)}" if m.group(1) else f"\\{m.group(3)}", line, count=1)
        return f"{head}{line}{tail}"

    def convert_pre(self, el, text, *args, **kwargs):
        fenced = super().convert_pre(el, text, *args, **kwargs)
        longest = max((len(run) for run in BACKTICK_RUN.findall(text or "")), default=0)
        if longest < 3:
            return fenced
        fence = "`" * (longest + 1)
        head, _, rest = fenced.partition("```")
        body, _, tail = rest.rpartition("```")
        return f"{head}{fence}{body}{fence}{tail}"


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
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
