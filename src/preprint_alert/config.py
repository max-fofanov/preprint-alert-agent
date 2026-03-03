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

    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3.2")

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
I'm interested in papers with genuinely novel ideas in NLP and language models:
- New architectures, training methods, or decoding strategies
- Reasoning, planning, and agentic capabilities
- Interpretability and mechanistic understanding of models
- Creative approaches to retrieval, grounding, or tool use
- Efficiency breakthroughs (not minor speedups — real paradigm shifts)
- Surprising empirical findings that challenge conventional wisdom

I am NOT interested in:
- Incremental benchmark gains ("we applied X to task Y, got +3% F1")
- Papers that simply fine-tune an existing model on a niche dataset
- Pure dataset/benchmark papers without methodological novelty
- Papers focused solely on non-English languages (unless the method is novel)
- Straightforward application papers with no new ideas

Prefer papers that make you think "that's clever" over papers that make you think
"that's a lot of GPUs." Papers from strong research labs (e.g. Google, Meta, DeepMind,
OpenAI, top universities) are often — but not always — more interesting due to broader
ablation studies and bolder ideas.
"""
