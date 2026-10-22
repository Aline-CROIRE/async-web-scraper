import asyncio
from pathlib import Path

from src.benchmark import benchmark_fetching
from src.json_writer import write_json

URLS = [
    "https://example.com/",
    "https://www.iana.org/",
    "https://www.python.org/",
]


async def main() -> None:
    """Run the benchmark and save its results."""
    results = await benchmark_fetching(URLS)

    print("\nBenchmark results")
    print("=================")

    for method, metrics in results.items():
        print(
            f"{method:12} "
            f"time={metrics['elapsed_seconds']:.4f}s "
            f"successful={metrics['successful_requests']}/{len(URLS)}"
        )

    output_path = Path("output") / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    await write_json(output_path, results)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
