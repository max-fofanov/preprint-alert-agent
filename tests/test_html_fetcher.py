"""Tests for HTML fetcher and methodology extraction."""

from preprint_alert.html_fetcher import extract_methodology_section


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
