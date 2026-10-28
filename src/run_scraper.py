import asyncio
from pathlib import Path

from src.async_generators import PageResult
from src.json_writer import write_json
from src.scraper import scrape_urls

URLS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://www.python.org/",
]


def show_progress(result: PageResult) -> None:
    """Print each page as soon as it has been scraped."""
    status = "done" if result["success"] else "failed"
    print(f"  {status}: {result['url']}")


async def main() -> None:
    """Run the scraper and save extracted results."""
    print(f"Scraping {len(URLS)} pages (results appear as they finish)...")
    results = await scrape_urls(URLS, on_result=show_progress)

    output_path = Path("output") / "scraped_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    await write_json(output_path, results)

    successful = sum(result["success"] for result in results)

    print("\nScraping results")
    print("================")

    for result in results:
        status = "success" if result["success"] else "failed"
        print(f"{result['url']}: {status}")
        print(f"  Title: {result['title']}")
        print(f"  Emails found: {len(result['emails'])}")

    print(f"\nSuccessful pages: {successful}/{len(URLS)}")
    print(f"JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
