"""Tests for HTML fetcher and methodology extraction."""

from bs4 import BeautifulSoup

from preprint_alert.html_fetcher import (
    extract_affiliations,
    extract_methodology_section,
    extract_repo_links,
)


def test_extract_methodology_finds_numbered_section():
    content = "1 Introduction\nSome intro text.\n\n2 Methodology\nOur approach uses transformers."
    result = extract_methodology_section(content)
    assert "Methodology" in result[:30]
    assert "Our approach" in result


def test_extract_methodology_finds_unnumbered_heading():
    content = "Introduction\nBlah.\n\nMethods\nWe propose a new method."
    result = extract_methodology_section(content)
    assert "Methods" in result[:20]


def test_extract_methodology_ignores_mid_sentence():
    """Should not match 'method' appearing mid-sentence."""
    content = (
        "We compare our method to baselines in section 4.\n\n"
        "3 Our Approach\nWe propose a novel architecture."
    )
    result = extract_methodology_section(content)
    # Should find "Our Approach" section, not the mid-sentence "method"
    assert "Our Approach" in result[:30]


def test_extract_methodology_fallback_on_no_match():
    content = "A" * 25000
    result = extract_methodology_section(content)
    assert len(result) == 20000


def test_extract_methodology_limits_length():
    content = "Methodology\n" + "x" * 20000
    result = extract_methodology_section(content)
    assert len(result) == 15000


def test_extract_methodology_case_insensitive():
    content = "Some preamble.\n\nMETHODOLOGY\nDetails here."
    result = extract_methodology_section(content)
    assert "METHODOLOGY" in result[:30]


# --- Affiliation extraction tests ---

ARXIV_AUTHORS_HTML = """
<div class="ltx_authors">
  <span class="ltx_creator ltx_role_author">
    <span class="ltx_personname">Alice Smith</span>
    <span class="ltx_author_notes">
      <span class="ltx_contact ltx_role_affiliation">Google DeepMind</span>
    </span>
  </span>
  <span class="ltx_creator ltx_role_author">
    <span class="ltx_personname">Bob Jones</span>
    <span class="ltx_author_notes">
      <span class="ltx_contact ltx_role_affiliation">Stanford University</span>
    </span>
  </span>
</div>
"""


def test_extract_affiliations_basic():
    soup = BeautifulSoup(ARXIV_AUTHORS_HTML, "html.parser")
    result = extract_affiliations(soup)
    assert result == ["Google DeepMind", "Stanford University"]


def test_extract_affiliations_deduplicates():
    html = """
    <div class="ltx_authors">
      <span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Alice</span>
        <span class="ltx_author_notes">
          <span class="ltx_contact ltx_role_affiliation">Meta FAIR</span>
        </span>
      </span>
      <span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Bob</span>
        <span class="ltx_author_notes">
          <span class="ltx_contact ltx_role_affiliation">Meta FAIR</span>
        </span>
      </span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_affiliations(soup)
    assert result == ["Meta FAIR"]


def test_extract_affiliations_strips_superscript_numbers():
    """Superscript markers like '1 2' from LaTeXML should be cleaned."""
    html = """
    <div class="ltx_authors">
      <span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Alice</span>
        <span class="ltx_author_notes">
          <span class="ltx_contact ltx_role_affiliation">
            Meta Reality Labs, 2 FAIR, Meta, 3 HKUST
          </span>
        </span>
      </span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_affiliations(soup)
    assert len(result) == 1
    assert "Meta Reality Labs" in result[0]
    assert "FAIR" in result[0]
    # Bare numbers should be stripped
    assert " 2 " not in result[0]


def test_extract_affiliations_no_authors_div():
    soup = BeautifulSoup("<html><body>No authors here</body></html>", "html.parser")
    result = extract_affiliations(soup)
    assert result == []


def test_extract_affiliations_empty_affiliation_skipped():
    html = """
    <div class="ltx_authors">
      <span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Alice</span>
        <span class="ltx_author_notes">
          <span class="ltx_contact ltx_role_affiliation"></span>
        </span>
      </span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_affiliations(soup)
    assert result == []


# --- Repo link extraction tests ---


def test_extract_repo_links_github():
    html = """
    <a href="https://github.com/facebookresearch/CRAG/">code</a>
    <a href="https://example.com">other</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_repo_links(soup)
    assert result == ["https://github.com/facebookresearch/CRAG"]


def test_extract_repo_links_huggingface():
    html = """
    <a href="https://huggingface.co/meta-llama/Llama-3">model</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_repo_links(soup)
    assert result == ["https://huggingface.co/meta-llama/Llama-3"]


def test_extract_repo_links_filters_arxiv_boilerplate():
    html = """
    <a href="https://github.com/deepseek-ai/DeepSeek-V2">real repo</a>
    <a href="https://github.com/arXiv/html_feedback/issues">feedback</a>
    <a href="https://github.com/brucemiller/LaTeXML/issues">latexml</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_repo_links(soup)
    assert result == ["https://github.com/deepseek-ai/DeepSeek-V2"]


def test_extract_repo_links_deduplicates():
    html = """
    <a href="https://github.com/org/repo">link 1</a>
    <a href="https://github.com/org/repo#section">link 2</a>
    <a href="https://github.com/org/repo/">link 3</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = extract_repo_links(soup)
    assert result == ["https://github.com/org/repo"]


def test_extract_repo_links_none_found():
    html = "<a href='https://example.com'>nothing here</a>"
    soup = BeautifulSoup(html, "html.parser")
    result = extract_repo_links(soup)
    assert result == []
