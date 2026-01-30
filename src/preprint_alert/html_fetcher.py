"""Fetch and parse HTML content from arXiv papers."""

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

    Returns the full content if no specific methodology section is found.
    """
    content_lower = html_content.lower()

    # Common methodology section headers
    method_markers = [
        "methodology",
        "methods",
        "method",
        "approach",
        "our approach",
        "proposed method",
        "model",
        "architecture",
    ]

    # Try to find methodology section
    for marker in method_markers:
        idx = content_lower.find(marker)
        if idx != -1:
            # Return from this point, but limit to reasonable length
            return html_content[idx : idx + 15000]

    # If no methodology section found, return truncated content
    return html_content[:20000]
