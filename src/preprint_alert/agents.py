"""LangGraph agents for paper analysis."""

import asyncio
from dataclasses import dataclass
from typing import Annotated

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from .arxiv_fetcher import Paper, fetch_papers
from .config import RESEARCH_INTERESTS, get_llm
from .html_fetcher import extract_methodology_section, fetch_paper_html


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
COORDINATOR_PROMPT = f"""You are a research paper curator. Your job is to review paper titles and abstracts from arXiv and identify which ones are genuinely interesting and worth reading in detail.

{RESEARCH_INTERESTS}

Given a list of papers with their titles and abstracts, return ONLY the arXiv IDs of papers that look interesting, one per line. Be selective - only pick papers that seem to have novel ideas or methods.

Do not include any other text, just the arXiv IDs of interesting papers, one per line."""


async def coordinator_node(state: AgentState) -> AgentState:
    """Coordinator agent that picks interesting papers."""
    print("📋 Fetching papers from arXiv...")
    papers = await fetch_papers()
    print(f"   Found {len(papers)} papers")

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
    print("🤔 Analyzing which papers look interesting...")

    response = await llm.ainvoke([
        SystemMessage(content=COORDINATOR_PROMPT),
        HumanMessage(content=f"Here are today's papers:\n\n{papers_text}"),
    ])

    # Parse response - expect arXiv IDs, one per line
    interesting_ids = [
        line.strip()
        for line in response.content.strip().split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    # Validate IDs exist in our paper list
    valid_ids = {p.arxiv_id for p in papers}
    interesting_ids = [id for id in interesting_ids if id in valid_ids]

    print(f"   Selected {len(interesting_ids)} interesting papers")
    state["interesting_paper_ids"] = interesting_ids
    return state


# Paper Analyst Agent - analyzes individual papers
ANALYST_PROMPT = """You are a research paper analyst. Your job is to read a paper's full content and extract the key insights about its methodology and contributions.

Focus on:
1. What is the core methodological innovation?
2. What makes this approach different from prior work?
3. What are the key technical details that make this work?
4. What are the main results and why do they matter?

Be concise but insightful. Focus on the "cool" technical details that a researcher would want to know."""


async def analyze_single_paper(paper: Paper) -> PaperAnalysis:
    """Analyze a single paper in detail."""
    print(f"   📖 Analyzing: {paper.title[:60]}...")

    # Fetch full HTML content
    html_content = await fetch_paper_html(paper)

    if html_content:
        methodology = extract_methodology_section(html_content)
        content_for_analysis = f"Title: {paper.title}\n\nAbstract: {paper.abstract}\n\nMethodology section:\n{methodology[:10000]}"
    else:
        # Fall back to just abstract if HTML not available
        content_for_analysis = f"Title: {paper.title}\n\nAbstract: {paper.abstract}\n\n(Full HTML not available for this paper)"

    llm = get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=ANALYST_PROMPT),
        HumanMessage(content=content_for_analysis),
    ])

    return PaperAnalysis(
        paper=paper,
        summary=response.content[:500],
        methodology_insights=response.content,
        why_interesting="",  # Will be filled by report writer context
    )


async def analyst_node(state: AgentState) -> AgentState:
    """Analyze each interesting paper in parallel."""
    papers_to_analyze = [
        p for p in state["papers"] if p.arxiv_id in state["interesting_paper_ids"]
    ]

    if not papers_to_analyze:
        state["analyses"] = []
        return state

    print(f"🔬 Analyzing {len(papers_to_analyze)} papers in detail...")

    # Run analyses in parallel
    analyses = await asyncio.gather(*[analyze_single_paper(p) for p in papers_to_analyze])

    state["analyses"] = list(analyses)
    return state


# Report Writer Agent - synthesizes into article
REPORT_WRITER_PROMPT = f"""You are a science journalist writing an engaging article about today's interesting papers from arXiv's NLP section.

{RESEARCH_INTERESTS}

Write a compelling, free-form article that:
1. Opens with a hook about today's most exciting developments
2. Weaves together the papers into a narrative - don't just list them
3. Highlights the coolest methodological insights
4. Explains why these advances matter
5. Naturally embeds links to papers using markdown: [paper title](url)

Write in an engaging, accessible style - like a blog post from a researcher who's excited about what they found. Avoid dry academic language.

Do NOT use bullet points or numbered lists. Write flowing prose with natural transitions between topics."""


async def report_writer_node(state: AgentState) -> AgentState:
    """Write the final report as an engaging article."""
    analyses = state["analyses"]

    if not analyses:
        state["final_report"] = "# No interesting papers found today\n\nCheck back tomorrow!"
        return state

    print("✍️  Writing report...")

    # Format analyses for the report writer
    analyses_text = "\n\n---\n\n".join(
        f"Paper: {a.paper.title}\n"
        f"Link: {a.paper.link}\n"
        f"Authors: {', '.join(a.paper.authors[:5])}\n"
        f"Analysis:\n{a.methodology_insights}"
        for a in analyses
    )

    llm = get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=REPORT_WRITER_PROMPT),
        HumanMessage(content=f"Here are the papers I analyzed today:\n\n{analyses_text}"),
    ])

    state["final_report"] = response.content
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
