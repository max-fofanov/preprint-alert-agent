"""Tests for agent pipeline resilience."""

from unittest.mock import patch

import pytest

from preprint_alert.agents import PaperAnalysis, analyst_node
from preprint_alert.arxiv_fetcher import Paper


def _make_paper(arxiv_id: str = "2401.00001", title: str = "Test Paper") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=["Author A"],
        abstract="An abstract.",
        link=f"https://arxiv.org/abs/{arxiv_id}",
    )


@pytest.mark.asyncio
async def test_analyst_node_handles_partial_failures():
    """If one paper fails analysis, others should still succeed."""
    paper1 = _make_paper("2401.00001", "Good Paper")
    paper2 = _make_paper("2401.00002", "Bad Paper")

    good_analysis = PaperAnalysis(
        paper=paper1,
        summary="Summary",
        methodology_insights="Insights",
        why_interesting="",
    )

    async def mock_analyze(paper):
        if paper.arxiv_id == "2401.00002":
            raise RuntimeError("LLM timeout")
        return good_analysis

    state = {
        "papers": [paper1, paper2],
        "interesting_paper_ids": ["2401.00001", "2401.00002"],
        "analyses": [],
        "final_report": "",
    }

    with patch("preprint_alert.agents.analyze_single_paper", side_effect=mock_analyze):
        result = await analyst_node(state)

    assert len(result["analyses"]) == 1
    assert result["analyses"][0].paper.arxiv_id == "2401.00001"


@pytest.mark.asyncio
async def test_analyst_node_empty_when_no_papers():
    state = {
        "papers": [],
        "interesting_paper_ids": [],
        "analyses": [],
        "final_report": "",
    }
    result = await analyst_node(state)
    assert result["analyses"] == []
