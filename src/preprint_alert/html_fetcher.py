"""Fetch and parse HTML content from arXiv papers."""

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from .arxiv_fetcher import Paper


def extract_affiliations(soup: BeautifulSoup) -> list[str]:
    """
    Extract unique author affiliations from arXiv HTML (LaTeXML format).

    Looks for ltx_contact/ltx_role_affiliation spans inside the ltx_authors block.
    Returns deduplicated list of affiliation strings.
    """
    affiliations: list[str] = []
    authors_div = soup.find("div", class_="ltx_authors")
    if not authors_div:
        return affiliations

    for aff in authors_div.find_all("span", class_="ltx_role_affiliation"):
        text = aff.get_text(separator=" ", strip=True)
        # Strip superscript numbers/markers that LaTeXML leaves in the text
        text = re.sub(r"\b\d+\b", "", text)
        # Collapse whitespace and stray commas left after stripping numbers
        text = re.sub(r"\s+", " ", text).strip().strip(",").strip()
        if text and text not in affiliations:
            affiliations.append(text)

    return affiliations


# Domains that are arXiv boilerplate, not paper repos
_BOILERPLATE_REPOS = {"arxiv", "brucemiller"}


def extract_repo_links(soup: BeautifulSoup) -> list[str]:
    """
    Extract GitHub and Hugging Face links from paper HTML.

    Filters out arXiv infrastructure links (LaTeXML, html_feedback, etc.).
    Returns deduplicated list of URLs.
    """
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.match(r"https?://(github\.com|huggingface\.co)/", href):
            continue
        # Strip fragment and trailing slash for dedup
        url = href.split("#")[0].rstrip("/")
        # Skip arXiv boilerplate repos
        parts = url.split("/")
        if len(parts) >= 4 and parts[3].lower() in _BOILERPLATE_REPOS:
            continue
        if url not in links:
            links.append(url)
    return links


@dataclass
class PaperHTML:
    """Parsed HTML content and metadata from an arXiv paper."""

    text: str
    affiliations: list[str]
    repo_links: list[str]


async def fetch_paper_html(paper: Paper) -> PaperHTML | None:
    """
    Fetch the HTML content of a paper from arXiv.

    Returns parsed text content and affiliations, or None if unavailable.
    Note: Not all arXiv papers have HTML versions available.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(paper.html_url, timeout=60.0)

            # HTML version may not exist for all papers
            if response.status_code == 404:
                return None

            response.raise_for_status()
        except httpx.HTTPError:
            return None

    soup = BeautifulSoup(response.text, "lxml")

    # Extract metadata before we strip elements
    affiliations = extract_affiliations(soup)
    repo_links = extract_repo_links(soup)

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "header", "footer"]):
        element.decompose()

    # Try to find the main article content
    # arXiv HTML papers typically have content in article or main tags
    main_content = soup.find("article") or soup.find("main") or soup.find("body")

    if main_content is None:
        return None

    # Extract text, preserving some structure
    sections = []

    # Look for section headings and their content
    for section in main_content.find_all(["section", "div"], class_=lambda x: x and "ltx_" in x):
        section_text = section.get_text(separator=" ", strip=True)
        if section_text:
            sections.append(section_text)

    text = "\n\n".join(sections) if sections else main_content.get_text(separator=" ", strip=True)
    return PaperHTML(text=text, affiliations=affiliations, repo_links=repo_links)


def extract_methodology_section(html_content: str) -> str:
    """
    Try to extract methodology/methods section from paper content.

    Looks for section headings (start of line, optionally numbered) rather than
    arbitrary substring matches to avoid false positives from mid-sentence mentions.

    Returns the full content if no specific methodology section is found.
    """
    # Common methodology section headers, ordered by specificity
    method_markers = [
        "methodology",
        "proposed method",
        "our approach",
        "methods",
        "method",
        "approach",
        "architecture",
        "model",
    ]

    for marker in method_markers:
        # Match marker at start of a line, optionally preceded by a section number
        pattern = rf"(?:^|\n)\s*(?:\d+\.?\s+)?{re.escape(marker)}\b"
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            start = match.start()
            return html_content[start : start + 15000]

    # If no methodology section found, return truncated content
    return html_content[:20000]
