# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Preprint Alert Agent is a LangGraph-based multi-agent system that:
1. Fetches today's NLP papers from arXiv's cs.CL RSS feed
2. Uses an LLM to identify interesting papers based on configured research interests
3. Spawns sub-agents to analyze each interesting paper's full HTML content
4. Generates an engaging narrative report (not a list) with embedded paper links
5. Builds a static HTML site from all reports

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the agent (generates report + builds site)
preprint-alert                    # Output to reports/report-YYYY-MM-DD.md
preprint-alert -o custom.md       # Custom output path

# Run tests
pytest                            # All tests
pytest tests/test_arxiv_fetcher.py::test_parse_arxiv_id  # Single test

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

```
coordinator_node  →  analyst_node  →  report_writer_node  →  (CLI builds site)
      │                   │                   │                      │
   Picks            Fetches HTML         Writes free-form      Converts all
   interesting      and extracts         narrative article     reports/ → site/
   papers           methodology
```

**Key files:**
- `src/preprint_alert/agents.py` - LangGraph workflow with three nodes: coordinator, analyst, report_writer. `AgentState` dict passes through nodes with: `papers`, `interesting_paper_ids`, `analyses`, `final_report`
- `src/preprint_alert/config.py` - LLM setup (OpenRouter via `langchain_openai.ChatOpenAI`) and `RESEARCH_INTERESTS` prompt
- `src/preprint_alert/arxiv_fetcher.py` - RSS feed parsing, `Paper` dataclass
- `src/preprint_alert/html_fetcher.py` - Full paper HTML fetching and methodology extraction via BeautifulSoup
- `src/preprint_alert/site_builder.py` - Converts `reports/*.md` → `site/*.html` (index + per-report pages)
- `src/preprint_alert/cli.py` - CLI entrypoint; runs the agent then calls `build_site()`

**Deployment:** GitHub Actions workflow (`.github/workflows/daily-report.yml`) runs daily at 05:30 UTC, generates a report, commits to `main`, and deploys `site/` to GitHub Pages.

## Configuration

Copy `.env.example` to `.env` and set:
- `OPENROUTER_API_KEY` - Required
- `OPENROUTER_MODEL` - Model to use (default: `anthropic/claude-3.5-sonnet`)

Edit `RESEARCH_INTERESTS` in `config.py` to customize what the agent finds interesting.
