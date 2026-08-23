import markdown as md_lib
from bs4 import BeautifulSoup
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    return markdownify(str(body), heading_style="ATX").strip()


def markdown_to_html(markdown: str) -> str:
    return md_lib.markdown(markdown, extensions=["tables", "fenced_code"])
