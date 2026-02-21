"""Fetch and parse HTML content from arXiv papers."""

import re

import httpx
from bs4 import BeautifulSoup

from .arxiv_fetcher import Paper


async def fetch_paper_html(paper: Paper) -> str | None:
    """
    Fetch the HTML content of a paper from arXiv.

    Returns the main text content extracted from the HTML, or None if unavailable.
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

    if sections:
        return "\n\n".join(sections)

    # Fallback: just get all text
    return main_content.get_text(separator=" ", strip=True)


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
