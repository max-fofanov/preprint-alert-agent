"""Command-line interface for the preprint alert agent."""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from .agents import run_agent


def get_report_path() -> Path:
    """Get the path for today's report."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    return reports_dir / f"report-{date_str}.md"


async def async_main(output_path: Path | None = None) -> None:
    """Run the agent and save the report."""
    print("🚀 Starting Preprint Alert Agent\n")

    report = await run_agent()

    if output_path is None:
        output_path = get_report_path()

    output_path.write_text(report)
    print(f"\n✅ Report saved to: {output_path}")


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

    args = parser.parse_args()

    asyncio.run(async_main(args.output))


if __name__ == "__main__":
    main()
