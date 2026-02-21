"""Tests for site builder report parsing."""

from preprint_alert.site_builder import _parse_report


def test_parse_report_extracts_heading_title(tmp_path):
    report = tmp_path / "report-2026-01-15.md"
    report.write_text("# Great Title\n\nSome content here about papers.")
    result = _parse_report(report)
    assert result["title"] == "Great Title"
    assert result["date_str"] == "2026-01-15"
    assert result["date_display"] == "January 15, 2026"


def test_parse_report_extracts_title_with_preamble(tmp_path):
    """Title should be found even when preceded by LLM preamble text."""
    report = tmp_path / "report-2026-01-15.md"
    report.write_text("Here's my engaging article:\n\n# Actual Title\n\nContent.")
    result = _parse_report(report)
    assert result["title"] == "Actual Title"


def test_parse_report_extracts_bold_title(tmp_path):
    """Fallback to **bold** title when no heading is present."""
    report = tmp_path / "report-2026-01-15.md"
    report.write_text("Some preamble.\n\n**Bold Title**\n\nContent here.")
    result = _parse_report(report)
    assert result["title"] == "Bold Title"


def test_parse_report_fallback_title(tmp_path):
    report = tmp_path / "report-2026-01-15.md"
    report.write_text("No heading here, just content about papers.")
    result = _parse_report(report)
    assert result["title"] == "Report 2026-01-15"


def test_parse_report_excerpt_skips_preamble(tmp_path):
    """Excerpt should skip LLM preamble lines like 'Here's my...'."""
    report = tmp_path / "report-2026-01-15.md"
    report.write_text(
        "Here's my engaging article:\n\n# Title\n\nActual content about NLP papers."
    )
    result = _parse_report(report)
    assert "Here's my" not in result["excerpt"]
    assert "Actual content" in result["excerpt"]


def test_parse_report_excerpt_truncates_long_text(tmp_path):
    report = tmp_path / "report-2026-01-15.md"
    report.write_text("# Title\n\n" + "x" * 300)
    result = _parse_report(report)
    assert len(result["excerpt"]) == 203  # 200 + "..."
    assert result["excerpt"].endswith("...")


def test_build_site_creates_files(tmp_path):
    """Integration test for build_site."""
    from preprint_alert.site_builder import build_site

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "report-2026-01-10.md").write_text(
        "# Paper Highlights\n\nToday's interesting papers."
    )
    (reports_dir / "report-2026-01-11.md").write_text(
        "# More Papers\n\nAnother day of papers."
    )

    site_dir = tmp_path / "site"
    build_site(reports_dir=reports_dir, site_dir=site_dir)

    assert (site_dir / "index.html").exists()
    assert (site_dir / "report-2026-01-10.html").exists()
    assert (site_dir / "report-2026-01-11.html").exists()

    index_html = (site_dir / "index.html").read_text()
    assert "Paper Highlights" in index_html
    assert "More Papers" in index_html
