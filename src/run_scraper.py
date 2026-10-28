import asyncio
import sys
from pathlib import Path

from src.async_generators import PageResult
from src.json_writer import write_json
from src.scraper import scrape_urls

URLS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://www.python.org/",
]

OUTPUT_PATH = Path("output") / "scraped_results.json"


def show_progress(result: PageResult) -> None:
    """Print each page as soon as it has been scraped."""
    status = "done" if result["success"] else "failed"
    print(f"  {status}: {result['url']}")


async def main() -> int:
    """Run the scraper, show the results and save them; return an exit code."""
    print(f"Scraping {len(URLS)} pages (results appear as they finish)...")
    results = await scrape_urls(URLS, on_result=show_progress)

    successful = sum(result["success"] for result in results)

    print("\nScraping results")
    print("================")

    for result in results:
        status = "success" if result["success"] else "failed"
        print(f"{result['url']}: {status}")
        print(f"  Title: {result['title']}")
        print(f"  Emails found: {len(result['emails'])}")

    print(f"\nSuccessful pages: {successful}/{len(URLS)}")

    try:
        saved_path = await write_json(OUTPUT_PATH, results)
    except OSError as error:
        print(f"Could not save results to {OUTPUT_PATH}: {error}", file=sys.stderr)
        return 1

    print(f"JSON saved to: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
