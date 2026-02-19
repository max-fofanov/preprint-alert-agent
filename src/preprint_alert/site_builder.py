"""Build a static site from markdown reports."""

import re
from datetime import datetime
from pathlib import Path

import markdown

REPORTS_DIR = Path("reports")
SITE_DIR = Path("site")

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
    --bg: #ffffff;
    --bg-secondary: #f7f7f8;
    --border: #e5e5e6;
    --accent: #10a37f;
    --link: #10a37f;
}

body {
    font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    color: var(--text);
    background: var(--bg);
    line-height: 1.8;
    font-size: 17px;
    -webkit-font-smoothing: antialiased;
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
}

.container {
    max-width: 680px;
    margin: 0 auto;
    padding: 0 24px;
}

/* Index page */
.index-hero {
    padding: 80px 0 48px;
}

.index-hero h1 {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 44px;
    font-weight: 400;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin-bottom: 16px;
}

.index-hero p {
    font-size: 19px;
    color: var(--text-secondary);
    line-height: 1.6;
}

.report-list {
    list-style: none;
    padding: 0;
}

.report-item {
    border-top: 1px solid var(--border);
    padding: 32px 0;
}

.report-item:last-child {
    border-bottom: 1px solid var(--border);
}

.report-date {
    font-size: 14px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
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
}

.report-item h2 a:hover {
    color: var(--accent);
}

.report-excerpt {
    color: var(--text-secondary);
    font-size: 16px;
    line-height: 1.6;
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
}

.back-link:hover {
    color: var(--accent);
}

footer {
    border-top: 1px solid var(--border);
    padding: 32px 0;
    margin-top: 48px;
    text-align: center;
    font-size: 14px;
    color: var(--text-secondary);
}
"""


def _page_shell(title: str, body: str) -> str:
    """Wrap content in the HTML shell with head, styles, header, footer."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS}</style>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <a href="index.html" class="site-title">Preprint Alert</a>
            <nav class="site-nav">
                <a href="index.html">Archive</a>
            </nav>
        </div>
    </header>
    {body}
    <footer>
        <div class="container">Generated by Preprint Alert Agent</div>
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

    # Extract title from first heading
    title_match = re.match(r"^#+\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else f"Report {date_str}"

    # Get first paragraph as excerpt
    lines = text.split("\n")
    excerpt = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            excerpt = stripped[:200]
            if len(stripped) > 200:
                excerpt += "..."
            break

    # Convert markdown to HTML
    html_content = markdown.markdown(text, extensions=["extra", "smarty"])

    return {
        "date_str": date_str,
        "date_display": date_display,
        "title": title,
        "excerpt": excerpt,
        "html": html_content,
        "slug": path.stem,
    }


def build_site(reports_dir: Path = REPORTS_DIR, site_dir: Path = SITE_DIR) -> None:
    """Build the full static site from markdown reports."""
    site_dir.mkdir(exist_ok=True)

    # Parse all reports
    report_files = sorted(reports_dir.glob("report-*.md"), reverse=True)
    reports = [_parse_report(f) for f in report_files]

    if not reports:
        print("   No reports found to build site from.")
        return

    # Build individual report pages
    for report in reports:
        # Strip the first h1/h2/h3 from body since we show it in the header
        body_html = re.sub(r"^<h[123][^>]*>.*?</h[123]>", "", report["html"], count=1).strip()

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
    </main>"""

        page = _page_shell(report["title"], article)
        (site_dir / f"{report['slug']}.html").write_text(page)

    # Build index page
    items_html = ""
    for report in reports:
        items_html += f"""
        <li class="report-item">
            <div class="report-date">{report["date_display"]}</div>
            <h2><a href="{report["slug"]}.html">{report["title"]}</a></h2>
            <p class="report-excerpt">{report["excerpt"]}</p>
        </li>"""

    index_body = f"""
    <main class="container">
        <div class="index-hero">
            <h1>Preprint Alert</h1>
            <p>AI-curated highlights from today's arXiv papers</p>
        </div>
        <ul class="report-list">
            {items_html}
        </ul>
    </main>"""

    index_page = _page_shell("Preprint Alert", index_body)
    (site_dir / "index.html").write_text(index_page)

    print(f"   Built {len(reports)} report pages + index → {site_dir}/")
