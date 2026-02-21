"""LangGraph agents for paper analysis."""

import asyncio
import logging
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from .arxiv_fetcher import Paper, fetch_papers
from .config import RESEARCH_INTERESTS, get_llm
from .html_fetcher import extract_methodology_section, fetch_paper_html

logger = logging.getLogger(__name__)


@dataclass
class PaperAnalysis:
    """Analysis result for a single paper."""

    paper: Paper
    summary: str
    methodology_insights: str
    why_interesting: str


class AgentState(dict):
    """State passed through the LangGraph workflow."""

    papers: list[Paper]
    interesting_paper_ids: list[str]
    analyses: list[PaperAnalysis]
    final_report: str


def make_initial_state() -> AgentState:
    """Create initial empty state."""
    return AgentState(
        papers=[],
        interesting_paper_ids=[],
        analyses=[],
        final_report="",
    )


# Coordinator Agent - picks interesting papers
COORDINATOR_PROMPT = (
    "You are a research paper curator. Your job is to review paper "
    "titles and abstracts from arXiv and identify which ones are "
    "genuinely interesting and worth reading in detail.\n\n"
    f"{RESEARCH_INTERESTS}\n\n"
    "Given a list of papers with their titles and abstracts, return "
    "ONLY the arXiv IDs of papers that look interesting, one per line. "
    "Be selective - only pick papers that seem to have novel ideas "
    "or methods.\n\n"
    "Do not include any other text, just the arXiv IDs of interesting "
    "papers, one per line."
)


async def coordinator_node(state: AgentState) -> AgentState:
    """Coordinator agent that picks interesting papers."""
    logger.info("Fetching papers from arXiv...")
    papers = await fetch_papers()
    logger.info("Found %d papers", len(papers))

    if not papers:
        state["papers"] = []
        state["interesting_paper_ids"] = []
        return state

    state["papers"] = papers

    # Format papers for the LLM
    papers_text = "\n\n".join(
        f"ID: {p.arxiv_id}\nTitle: {p.title}\nAbstract: {p.abstract[:500]}..."
        for p in papers
    )

    llm = get_llm()
    logger.info("Analyzing which papers look interesting...")

    try:
        response = await llm.ainvoke([
            SystemMessage(content=COORDINATOR_PROMPT),
            HumanMessage(content=f"Here are today's papers:\n\n{papers_text}"),
        ])
    except Exception as e:
        logger.warning("LLM error in coordinator: %s", e)
        state["interesting_paper_ids"] = []
        return state

    # Parse response - expect arXiv IDs, one per line
    interesting_ids = [
        line.strip()
        for line in response.content.strip().split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    # Validate IDs exist in our paper list
    valid_ids = {p.arxiv_id for p in papers}
    interesting_ids = [id for id in interesting_ids if id in valid_ids]

    logger.info("Selected %d interesting papers", len(interesting_ids))
    state["interesting_paper_ids"] = interesting_ids
    return state


# Paper Analyst Agent - analyzes individual papers
ANALYST_PROMPT = (
    "You are a research paper analyst. Your job is to read a paper's "
    "full content and extract the key insights about its methodology "
    "and contributions.\n\n"
    "Focus on:\n"
    "1. What is the core methodological innovation?\n"
    "2. What makes this approach different from prior work?\n"
    "3. What are the key technical details that make this work?\n"
    "4. What are the main results and why do they matter?\n\n"
    'Be concise but insightful. Focus on the "cool" technical '
    "details that a researcher would want to know."
)


async def analyze_single_paper(paper: Paper) -> PaperAnalysis:
    """Analyze a single paper in detail."""
    logger.info("Analyzing: %s...", paper.title[:60])

    # Fetch full HTML content
    html_content = await fetch_paper_html(paper)

    if html_content:
        methodology = extract_methodology_section(html_content)
        content_for_analysis = (
            f"Title: {paper.title}\n\n"
            f"Abstract: {paper.abstract}\n\n"
            f"Methodology section:\n{methodology[:10000]}"
        )
    else:
        # Fall back to just abstract if HTML not available
        content_for_analysis = (
            f"Title: {paper.title}\n\n"
            f"Abstract: {paper.abstract}\n\n"
            "(Full HTML not available for this paper)"
        )

    llm = get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=ANALYST_PROMPT),
            HumanMessage(content=content_for_analysis),
        ])
    except Exception as e:
        logger.warning("LLM error analyzing %s: %s", paper.title[:40], e)
        return PaperAnalysis(
            paper=paper,
            summary="Analysis unavailable due to an error.",
            methodology_insights="Analysis could not be completed.",
            why_interesting="",
        )

    return PaperAnalysis(
        paper=paper,
        summary=response.content[:500],
        methodology_insights=response.content,
        why_interesting="",
    )


async def analyst_node(state: AgentState) -> AgentState:
    """Analyze each interesting paper in parallel."""
    papers_to_analyze = [
        p for p in state["papers"] if p.arxiv_id in state["interesting_paper_ids"]
    ]

    if not papers_to_analyze:
        state["analyses"] = []
        return state

    logger.info("Analyzing %d papers in detail...", len(papers_to_analyze))

    # Run analyses in parallel, tolerating individual failures
    results = await asyncio.gather(
        *[analyze_single_paper(p) for p in papers_to_analyze],
        return_exceptions=True,
    )
    analyses = [r for r in results if isinstance(r, PaperAnalysis)]
    failed = [r for r in results if isinstance(r, BaseException)]
    if failed:
        logger.warning("%d paper(s) failed analysis", len(failed))
        for err in failed:
            logger.warning("  %s", err)

    state["analyses"] = analyses
    return state


# Report Writer Agent - synthesizes into article
REPORT_WRITER_PROMPT = (
    "You are a science journalist writing an engaging article about "
    "today's interesting papers from arXiv's NLP section.\n\n"
    f"{RESEARCH_INTERESTS}\n\n"
    "Write a compelling, free-form article that:\n"
    "1. Opens with a hook about today's most exciting developments\n"
    "2. Weaves together the papers into a narrative - don't just "
    "list them\n"
    "3. Highlights the coolest methodological insights\n"
    "4. Explains why these advances matter\n\n"
    "CRITICAL: Every time you mention a paper, you MUST include a "
    "markdown link to it. Use the exact URLs provided.\n"
    "Format: [Paper Title](url) - e.g., "
    "[Attention Is All You Need]"
    "(https://arxiv.org/abs/1706.03762)\n\n"
    "Write in an engaging, accessible style - like a blog post from "
    "a researcher who's excited about what they found. "
    "Avoid dry academic language.\n\n"
    "Do NOT use bullet points or numbered lists. Write flowing prose "
    "with natural transitions between topics.\n\n"
    "Start your article DIRECTLY with a markdown # heading as the "
    "title. Do NOT include any preamble or meta-commentary before "
    "the title."
)


async def report_writer_node(state: AgentState) -> AgentState:
    """Write the final report as an engaging article."""
    analyses = state["analyses"]

    if not analyses:
        state["final_report"] = "# No interesting papers found today\n\nCheck back tomorrow!"
        return state

    logger.info("Writing report...")

    # Format analyses for the report writer
    analyses_text = "\n\n---\n\n".join(
        f"PAPER: {a.paper.title}\n"
        f"URL (use this in markdown links): {a.paper.link}\n"
        f"Authors: {', '.join(a.paper.authors[:5])}\n"
        f"Analysis:\n{a.methodology_insights}"
        for a in analyses
    )

    llm = get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=REPORT_WRITER_PROMPT),
            HumanMessage(content=f"Here are the papers I analyzed today:\n\n{analyses_text}"),
        ])
        state["final_report"] = response.content
    except Exception as e:
        logger.warning("LLM error in report writer: %s", e)
        paper_list = "\n".join(
            f"- [{a.paper.title}]({a.paper.link})" for a in analyses
        )
        state["final_report"] = (
            "# Today's Papers\n\n"
            "Automatic report generation encountered an error. "
            "Here are the papers that were identified as interesting:\n\n"
            f"{paper_list}"
        )
    return state


def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("report_writer", report_writer_node)

    # Define edges
    workflow.set_entry_point("coordinator")
    workflow.add_edge("coordinator", "analyst")
    workflow.add_edge("analyst", "report_writer")
    workflow.add_edge("report_writer", END)

    return workflow.compile()


async def run_agent() -> str:
    """Run the full agent pipeline and return the report."""
    graph = build_graph()
    initial_state = make_initial_state()

    final_state = await graph.ainvoke(initial_state)
    return final_state["final_report"]
