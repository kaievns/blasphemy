import markdown as md_lib
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


class _Converter(MarkdownConverter):
    # markdown has no syntax for these; inline HTML survives the round trip
    def convert_sup(self, el, text, *args, **kwargs):
        return f"<sup>{text}</sup>"

    def convert_sub(self, el, text, *args, **kwargs):
        return f"<sub>{text}</sub>"

    def convert_u(self, el, text, *args, **kwargs):
        return f"<u>{text}</u>"


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    return _Converter(heading_style="ATX").convert(str(body)).strip()


def markdown_to_html(markdown: str) -> str:
    return md_lib.markdown(markdown, extensions=["tables", "fenced_code"])
