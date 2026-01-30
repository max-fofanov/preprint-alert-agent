"""Tests for arXiv fetcher."""

import pytest

from preprint_alert.arxiv_fetcher import parse_arxiv_id, clean_text


def test_parse_arxiv_id():
    """Test extracting arXiv ID from URLs."""
    assert parse_arxiv_id("https://arxiv.org/abs/2401.12345") == "2401.12345"
    assert parse_arxiv_id("https://arxiv.org/abs/2401.12345/") == "2401.12345"
    assert parse_arxiv_id("http://arxiv.org/abs/cs/0123456") == "0123456"


def test_clean_text():
    """Test text cleaning."""
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("line1\n\nline2") == "line1 line2"
    assert clean_text(None) == ""
    assert clean_text("") == ""


@pytest.mark.asyncio
async def test_fetch_papers_integration():
    """Integration test for fetching papers (requires network)."""
    from preprint_alert.arxiv_fetcher import fetch_papers

    papers = await fetch_papers()

    # Should return a list (may be empty on weekends/holidays)
    assert isinstance(papers, list)

    if papers:
        paper = papers[0]
        assert paper.arxiv_id
        assert paper.title
        assert paper.link
        assert paper.html_url.startswith("https://arxiv.org/html/")
