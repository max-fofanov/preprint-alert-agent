"""Command-line interface for the preprint alert agent."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from .agents import run_agent
from .site_builder import build_site

logger = logging.getLogger(__name__)


def get_report_path() -> Path:
    """Get the path for today's report."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    return reports_dir / f"report-{date_str}.md"


async def async_main(output_path: Path | None = None) -> None:
    """Run the agent and save the report."""
    logger.info("Starting Preprint Alert Agent")

    report = await run_agent()

    if output_path is None:
        output_path = get_report_path()

    output_path.write_text(report)
    logger.info("Report saved to: %s", output_path)

    logger.info("Building site...")
    build_site()
    logger.info("Site built → site/index.html")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Analyze today's arXiv papers and generate a report"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for the report (default: reports/report-YYYY-MM-DD.md)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug output",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        asyncio.run(async_main(args.output))
    except Exception:
        logger.exception("Agent failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
