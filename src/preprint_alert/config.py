"""Configuration and LLM setup."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()


def get_llm() -> ChatOpenAI:
    """Get the configured LLM via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/preprint-alert-agent",
            "X-Title": "Preprint Alert Agent",
        },
    )


# Research interests - customize this to match your interests
RESEARCH_INTERESTS = """
I'm interested in:
- Reasoning/thinking

I'm less interested in:
- Incremental improvements on existing benchmarks
- Pure dataset papers without methodological novelty
- Papers focused solely on non-English languages (unless methodology is novel)
"""
