import asyncio
import sys
from pathlib import Path

from src.benchmark import benchmark_fetching
from src.json_writer import write_json

URLS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://www.python.org/",
]

OUTPUT_PATH = Path("output") / "benchmark_results.json"


async def main() -> int:
    """Run the benchmark, show and save its results; return an exit code."""
    results = await benchmark_fetching(URLS)

    print("\nBenchmark results")
    print("=================")

    for method, metrics in results.items():
        print(
            f"{method:12} "
            f"time={metrics['elapsed_seconds']:.4f}s "
            f"successful={metrics['successful_requests']}/{len(URLS)}"
        )

    try:
        saved_path = await write_json(OUTPUT_PATH, results)
    except OSError as error:
        print(f"\nCould not save results to {OUTPUT_PATH}: {error}", file=sys.stderr)
        return 1

    print(f"\nResults saved to: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
