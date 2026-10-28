import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from src.async_generators import PageResult
from src.json_writer import write_json
from src.scraper import scrape_urls

DEFAULT_URLS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://www.python.org/",
]

OUTPUT_PATH = Path("output") / "scraped_results.json"


def print_banner() -> None:
    """Display the application title."""
    print("\n" + "=" * 42)
    print("           ASYNC WEB SCRAPER")
    print("=" * 42)


def get_urls() -> list[str]:
    """Prompt for URLs and return valid HTTP(S) URLs."""
    print("\nEnter website URLs separated by commas.")
    print("Press Enter to use the default demo websites.")

    raw_urls = input("URLs: ").strip()

    if not raw_urls:
        return DEFAULT_URLS.copy()

    urls: list[str] = []

    for item in raw_urls.split(","):
        url = item.strip()

        try:
            parsed = urlsplit(url)
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.port != 0
            )
        except ValueError:
            valid = False

        if not valid:
            print(f"Skipping invalid URL: {url}")
            continue

        if url not in urls:
            urls.append(url)

    return urls


def get_concurrency() -> int:
    """Prompt for a concurrency limit between one and ten."""
    while True:
        raw_value = input("Maximum concurrent requests (1-10, default 5): ").strip()

        if not raw_value:
            return 5

        try:
            value = int(raw_value)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if 1 <= value <= 10:
            return value

        print("Choose a number between 1 and 10.")


def display_results(results: list[dict]) -> None:
    """Display a readable summary of scraping results."""
    successful = sum(result["success"] is True for result in results)

    print("\nScraping results")
    print("=" * 42)

    for index, result in enumerate(results, start=1):
        status = "SUCCESS" if result["success"] else "FAILED"
        print(f"\n[{index}/{len(results)}] {result['url']}")
        print(f"  Status: {status}")
        print(f"  Title: {result['title'] or 'Not found'}")

        emails = result["emails"]
        print(f"  Emails found: {len(emails)}")

        for email in emails:
            print(f"    - {email}")

    print("\n" + "=" * 42)
    print(f"Completed: {successful}/{len(results)} websites successful")


def show_progress(result: PageResult) -> None:
    """Print each website as soon as it has been scraped."""
    status = "done" if result["success"] else "failed"
    print(f"  {status}: {result['url']}")


async def scrape_interactively() -> None:
    """Collect user options, scrape websites, and save results."""
    urls = get_urls()

    if not urls:
        print("No valid URLs were provided. Returning to the menu.")
        return

    concurrency = get_concurrency()

    print(f"\nStarting scraper for {len(urls)} website(s)...")
    print(f"Maximum concurrent requests: {concurrency}")

    results = await scrape_urls(
        urls,
        max_concurrency=concurrency,
        on_result=show_progress,
    )

    display_results(results)

    try:
        saved_path = await write_json(OUTPUT_PATH, results)
    except OSError as error:
        print(f"Could not save results to {OUTPUT_PATH}: {error}")
        return

    print(f"JSON saved to: {saved_path}")


def view_saved_results() -> None:
    """Display previously saved results."""
    if not OUTPUT_PATH.exists():
        print("\nNo saved results found. Run a scrape first.")
        return

    try:
        results = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read saved results: {error}")
        return

    print(f"\nSaved results from {OUTPUT_PATH}:")
    print(json.dumps(results, indent=2, ensure_ascii=False))


async def main() -> None:
    """Run the interactive demonstration menu."""
    while True:
        print_banner()
        print("1. Scrape websites")
        print("2. View previous results")
        print("3. Exit")

        choice = input("\nChoose an option (1-3): ").strip()

        if choice == "1":
            try:
                await scrape_interactively()
            except (ValueError, TypeError) as error:
                print(f"Invalid scraper configuration: {error}")
        elif choice == "2":
            view_saved_results()
        elif choice == "3":
            print("\nThank you for using Async Web Scraper. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    asyncio.run(main())
