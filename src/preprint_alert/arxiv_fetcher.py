"""Fetch papers from arXiv RSS feed."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

ARXIV_RSS_URL = "https://rss.arxiv.org/rss/cs.CL"

# Namespaces used in arXiv RSS
NAMESPACES = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


@dataclass
class Paper:
    """A paper from arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    link: str

    @property
    def html_url(self) -> str:
        """Get the HTML page URL for this paper."""
        return f"https://export.arxiv.org/html/{self.arxiv_id}"

    @property
    def pdf_url(self) -> str:
        """Get the PDF URL for this paper."""
        return f"https://export.arxiv.org/pdf/{self.arxiv_id}"


def parse_arxiv_id(link: str) -> str:
    """Extract arXiv ID from link like https://arxiv.org/abs/2401.12345."""
    return link.rstrip("/").split("/")[-1]


def clean_text(text: str | None) -> str:
    """Clean up text from RSS feed."""
    if not text:
        return ""
    # Remove excessive whitespace
    return " ".join(text.split())


async def fetch_papers() -> list[Paper]:
    """Fetch today's papers from arXiv cs.CL RSS feed."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(ARXIV_RSS_URL, timeout=30.0)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Error fetching arXiv RSS feed: %s", e)
        return []

    root = ET.fromstring(response.text)
    papers = []

    for item in root.findall(".//item"):
        title_elem = item.find("title")
        link_elem = item.find("link")
        description_elem = item.find("description")
        creator_elem = item.find("dc:creator", NAMESPACES)

        if title_elem is None or link_elem is None:
            continue

        link = link_elem.text or ""
        arxiv_id = parse_arxiv_id(link)

        # Parse authors (comma-separated in dc:creator)
        authors_text = creator_elem.text if creator_elem is not None else ""
        authors = [a.strip() for a in authors_text.split(",")] if authors_text else []

        # Clean title - remove arXiv ID prefix if present
        title = clean_text(title_elem.text)
        if title.startswith(f"{arxiv_id}:"):
            title = title[len(arxiv_id) + 1 :].strip()

        paper = Paper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=clean_text(description_elem.text if description_elem is not None else ""),
            link=link,
        )
        papers.append(paper)

    return papers
