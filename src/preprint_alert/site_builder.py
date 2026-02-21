"""Build a static site from markdown reports."""

import logging
import re
from datetime import datetime
from pathlib import Path

import markdown

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")
SITE_DIR = Path("site")

GITHUB_URL = "https://github.com/max-fofanov/preprint-alert-agent"

CSS = """
*,
*::before,
*::after {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --text: #353740;
    --text-secondary: #6e6e80;
    --bg: #fafaf9;
    --bg-secondary: #f3f3f0;
    --border: #e5e5e6;
    --accent: #10a37f;
    --link: #10a37f;
}

@media (prefers-color-scheme: dark) {
    :root {
        --text: #d1d5db;
        --text-secondary: #9ca3af;
        --bg: #111111;
        --bg-secondary: #1a1a1a;
        --border: #2a2a2a;
        --accent: #34d399;
        --link: #34d399;
    }
}

body {
    font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    color: var(--text);
    background: var(--bg);
    line-height: 1.8;
    font-size: 17px;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

main {
    flex: 1;
}

.site-header {
    border-bottom: 1px solid var(--border);
    padding: 20px 0;
    margin-bottom: 48px;
}

.site-header .container {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.site-header a {
    text-decoration: none;
    color: var(--text);
}

.site-title {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.site-nav a {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 15px;
    transition: color 0.15s;
}

.site-nav a:hover {
    color: var(--accent);
}

.container {
    max-width: 680px;
    margin: 0 auto;
    padding: 0 24px;
}

/* Index page */
.index-tagline {
    color: var(--text-secondary);
    font-size: 16px;
    padding-bottom: 32px;
}

.report-list {
    list-style: none;
    padding: 0;
}

.report-item {
    border-top: 1px solid var(--border);
    padding: 28px 0;
    transition: background 0.15s;
}

.report-item:last-child {
    border-bottom: 1px solid var(--border);
}

.report-item:hover {
    background: var(--bg-secondary);
    margin: 0 -24px;
    padding-left: 24px;
    padding-right: 24px;
}

.report-date {
    font-size: 14px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.report-badge {
    display: inline-block;
    font-size: 12px;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 10px;
    letter-spacing: 0;
    text-transform: none;
    vertical-align: middle;
}

.report-item h2 {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 26px;
    font-weight: 400;
    line-height: 1.3;
    letter-spacing: -0.01em;
    margin-bottom: 8px;
}

.report-item h2 a {
    color: var(--text);
    text-decoration: none;
    transition: color 0.15s;
}

.report-item h2 a:hover {
    color: var(--accent);
}

.report-excerpt {
    color: var(--text-secondary);
    font-size: 16px;
    line-height: 1.6;
}

/* Empty report (no interesting papers) */
.report-item-empty {
    opacity: 0.55;
}

.report-item-empty:hover {
    background: transparent;
    margin: 0;
    padding-left: 0;
    padding-right: 0;
}

.report-item-empty h2 {
    font-size: 18px;
    font-family: inherit;
}

/* Article page */
.article-header {
    padding: 80px 0 40px;
    text-align: center;
}

.article-date {
    font-size: 14px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 16px;
}

.article-header h1 {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 40px;
    font-weight: 400;
    line-height: 1.2;
    letter-spacing: -0.02em;
}

.article-body {
    padding-bottom: 80px;
}

.article-body h2,
.article-body h3 {
    font-family: Georgia, 'Times New Roman', serif;
    font-weight: 400;
    letter-spacing: -0.01em;
    margin-top: 48px;
    margin-bottom: 16px;
}

.article-body h2 {
    font-size: 30px;
    line-height: 1.25;
}

.article-body h3 {
    font-size: 24px;
    line-height: 1.3;
}

.article-body p {
    margin-bottom: 24px;
}

.article-body a {
    color: var(--link);
    text-decoration: underline;
    text-underline-offset: 2px;
    text-decoration-thickness: 1px;
    transition: text-decoration-thickness 0.15s;
}

.article-body a:hover {
    text-decoration-thickness: 2px;
}

.article-body strong {
    font-weight: 600;
}

.article-body em {
    font-style: italic;
}

.article-body blockquote {
    border-left: 3px solid var(--border);
    padding-left: 20px;
    margin: 32px 0;
    color: var(--text-secondary);
    font-style: italic;
}

.article-body code {
    font-family: 'Söhne Mono', 'Menlo', monospace;
    font-size: 0.9em;
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 4px;
}

.article-body ul,
.article-body ol {
    margin-bottom: 24px;
    padding-left: 24px;
}

.article-body li {
    margin-bottom: 8px;
}

.back-link {
    display: inline-block;
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 15px;
    padding: 40px 0 0;
    transition: color 0.15s;
}

.back-link:hover {
    color: var(--accent);
}

.article-nav {
    display: flex;
    justify-content: space-between;
    padding: 32px 0 0;
    gap: 24px;
}

.article-nav a {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 15px;
    max-width: 45%;
    transition: color 0.15s;
}

.article-nav a:hover {
    color: var(--accent);
}

.nav-newer {
    margin-left: auto;
    text-align: right;
}

footer {
    border-top: 1px solid var(--border);
    padding: 32px 0;
    margin-top: 48px;
    text-align: center;
    font-size: 14px;
    color: var(--text-secondary);
}

footer a {
    color: var(--text-secondary);
    text-decoration: underline;
    text-underline-offset: 2px;
    text-decoration-thickness: 1px;
    transition: color 0.15s;
}

footer a:hover {
    color: var(--accent);
}
"""


FAVICON = (
    '<link rel="icon" href="data:image/svg+xml,'
    '%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20viewBox=%220%200%20100%20100%22%3E'
    '%3Ctext%20y=%22.9em%22%20font-size=%2290%22%3E'
    "%F0%9F%93%84"  # U+1F4C4 page facing up emoji
    "%3C/text%3E%3C/svg%3E"
    '">'
)


def _page_shell(title: str, body: str, description: str = "") -> str:
    """Wrap content in the HTML shell with head, styles, header, footer."""
    og_tags = ""
    if description:
        og_tags = (
            f'\n    <meta property="og:title" content="{title}">'
            f'\n    <meta property="og:description" content="{description[:200]}">'
            '\n    <meta property="og:type" content="article">'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>{og_tags}
    {FAVICON}
    <style>{CSS}</style>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <a href="index.html" class="site-title">Preprint Alert</a>
            <nav class="site-nav">
                <a href="{GITHUB_URL}">GitHub</a>
            </nav>
        </div>
    </header>
    {body}
    <footer>
        <div class="container">Built with <a href="{GITHUB_URL}">Preprint Alert Agent</a></div>
    </footer>
</body>
</html>"""


def _parse_report(path: Path) -> dict:
    """Parse a markdown report file into metadata and content."""
    text = path.read_text()

    # Extract date from filename: report-YYYY-MM-DD.md
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    date_str = match.group(1) if match else "Unknown"
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date.strftime("%B %d, %Y")
    except ValueError:
        date_display = date_str

    # Extract title from first markdown heading, or bold text as fallback
    title_match = re.search(r"^#+\s+(.+)$", text, re.MULTILINE)
    if not title_match:
        title_match = re.search(r"^\*\*(.+?)\*\*$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else f"Report {date_str}"

    # Get first paragraph as excerpt, skipping headings and LLM preamble
    lines = text.split("\n")
    excerpt = ""
    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith("**")
            and not stripped.lower().startswith("here's my")
            and not stripped.lower().startswith("here is my")
        ):
            excerpt = stripped[:200]
            if len(stripped) > 200:
                excerpt += "..."
            break

    # Convert markdown to HTML
    html_content = markdown.markdown(text, extensions=["extra", "smarty"])

    # Count arXiv paper links
    paper_count = len(re.findall(r"arxiv\.org/abs/", text))

    # Detect "no papers" reports
    is_empty = "no interesting papers" in title.lower()

    return {
        "date_str": date_str,
        "date_display": date_display,
        "title": title,
        "excerpt": excerpt,
        "html": html_content,
        "slug": path.stem,
        "paper_count": paper_count,
        "is_empty": is_empty,
    }


def build_site(reports_dir: Path = REPORTS_DIR, site_dir: Path = SITE_DIR) -> None:
    """Build the full static site from markdown reports."""
    site_dir.mkdir(exist_ok=True)

    # Parse all reports
    report_files = sorted(reports_dir.glob("report-*.md"), reverse=True)
    reports = [_parse_report(f) for f in report_files]

    if not reports:
        logger.warning("No reports found to build site from.")
        return

    # Build individual report pages (reports sorted newest-first)
    for i, report in enumerate(reports):
        # Strip the first h1/h2/h3 from body since we show it in the header
        body_html = re.sub(r"^<h[123][^>]*>.*?</h[123]>", "", report["html"], count=1).strip()

        # Build prev/next navigation
        nav_html = '<div class="article-nav">'
        if i < len(reports) - 1:  # older report exists
            older = reports[i + 1]
            nav_html += (
                f'<a class="nav-older" href="{older["slug"]}.html">'
                f'&larr; {older["title"][:50]}</a>'
            )
        if i > 0:  # newer report exists
            newer = reports[i - 1]
            nav_html += (
                f'<a class="nav-newer" href="{newer["slug"]}.html">'
                f'{newer["title"][:50]} &rarr;</a>'
            )
        nav_html += "</div>"

        article = f"""
    <main class="container">
        <div class="article-header">
            <div class="article-date">{report["date_display"]}</div>
            <h1>{report["title"]}</h1>
        </div>
        <div class="article-body">
            {body_html}
        </div>
        <a href="index.html" class="back-link">&larr; All reports</a>
        {nav_html}
    </main>"""

        page = _page_shell(report["title"], article, description=report["excerpt"])
        (site_dir / f"{report['slug']}.html").write_text(page)

    # Build index page
    items_html = ""
    for report in reports:
        if report["is_empty"]:
            items_html += f"""
        <li class="report-item report-item-empty">
            <div class="report-date">{report["date_display"]}</div>
            <h2>No interesting papers today</h2>
        </li>"""
        else:
            badge = ""
            if report["paper_count"]:
                n = report["paper_count"]
                label = f"{n} paper{'s' if n != 1 else ''}"
                badge = f'<span class="report-badge">{label}</span>'
            items_html += f"""
        <li class="report-item">
            <div class="report-date">{report["date_display"]}{badge}</div>
            <h2><a href="{report["slug"]}.html">{report["title"]}</a></h2>
            <p class="report-excerpt">{report["excerpt"]}</p>
        </li>"""

    index_body = f"""
    <main class="container">
        <p class="index-tagline">AI-curated daily highlights from arXiv cs.CL</p>
        <ul class="report-list">
            {items_html}
        </ul>
    </main>"""

    index_page = _page_shell("Preprint Alert", index_body)
    (site_dir / "index.html").write_text(index_page)

    logger.info("Built %d report pages + index → %s/", len(reports), site_dir)
