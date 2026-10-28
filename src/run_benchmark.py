import argparse
import asyncio
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.benchmark import (
    METHODS,
    MethodResult,
    benchmark_fetching,
    local_benchmark_server,
)
from src.json_writer import write_json

# Used only by --mode network, which contacts these public sites.
NETWORK_URLS = [
    "https://example.com/",
    "https://example.org/",
    "https://example.net/",
    "https://www.iana.org/",
    "https://www.iana.org/domains",
    "https://www.iana.org/protocols",
    "https://www.iana.org/numbers",
    "https://www.iana.org/about",
    "https://www.python.org/",
    "https://www.python.org/about/",
    "https://www.python.org/downloads/",
    "https://www.python.org/doc/",
    "https://www.python.org/community/",
    "https://docs.python.org/3/",
    "https://docs.python.org/3/library/asyncio.html",
    "https://docs.python.org/3/library/json.html",
    "https://docs.python.org/3/library/re.html",
    "https://peps.python.org/",
    "https://pypi.org/",
    "https://docs.aiohttp.org/en/stable/",
]

OUTPUT_PATH = Path("output") / "benchmark_results.json"


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _non_negative_float(value: str) -> float:
    number = float(value)
    if not number >= 0 or number == float("inf"):
        raise argparse.ArgumentTypeError("must be a finite number of at least 0")
    return number


def _positive_float(value: str) -> float:
    number = _non_negative_float(value)
    if number == 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the benchmark's command-line options."""
    parser = argparse.ArgumentParser(
        description="Compare sequential, threaded and async HTTP fetching.",
    )
    parser.add_argument(
        "--mode",
        choices=("local", "network"),
        default="local",
        help="local: reproducible local server (default); network: public URLs",
    )
    parser.add_argument(
        "--pages",
        type=_positive_int,
        default=25,
        help="local mode: number of pages to fetch (default: 25)",
    )
    parser.add_argument(
        "--latency",
        type=_non_negative_float,
        default=0.1,
        help="local mode: seconds each page waits before responding (default: 0.1)",
    )
    parser.add_argument(
        "--repetitions",
        type=_positive_int,
        default=5,
        help="times to run each method (default: 5)",
    )
    parser.add_argument(
        "--concurrency",
        type=_positive_int,
        default=10,
        help="requests at once for threaded and async (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=10.0,
        help="seconds before a request is abandoned (default: 10)",
    )
    return parser.parse_args(argv)


def format_results(results: dict[str, MethodResult], url_count: int) -> str:
    """Format benchmark results as a plain-text table."""
    baseline = results["sequential"]["elapsed_seconds"]
    header = (
        f"{'Method':<12}{'Median':>10}{'Min':>10}{'Max':>10}"
        f"{'Successful':>13}{'Speed-up':>10}"
    )
    lines = [header]

    for method in METHODS:
        metrics = results[method]
        median = metrics["elapsed_seconds"]
        speed_up = f"{baseline / median:.2f}x" if median > 0 else "n/a"
        lines.append(
            f"{method:<12}{median:>9.3f}s{metrics['min_seconds']:>9.3f}s"
            f"{metrics['max_seconds']:>9.3f}s"
            f"{metrics['successful_requests']:>8}/{url_count:<4}{speed_up:>10}"
        )

    return "\n".join(lines)


async def main(argv: list[str] | None = None) -> int:
    """Run the benchmark, show and save its results; return an exit code."""
    args = parse_args(argv)
    options = {
        "repetitions": args.repetitions,
        "concurrency": args.concurrency,
        "timeout": args.timeout,
    }

    if args.mode == "local":
        with local_benchmark_server(args.pages, args.latency) as urls:
            results = await benchmark_fetching(urls, **options)
    else:
        urls = NETWORK_URLS
        results = await benchmark_fetching(urls, **options)

    conditions = {
        "mode": args.mode,
        "url_count": len(urls),
        "latency_seconds": args.latency if args.mode == "local" else None,
        "repetitions": args.repetitions,
        "concurrency": args.concurrency,
        "timeout_seconds": args.timeout,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    print("\nBenchmark results")
    print("=================")
    print(
        f"Mode: {args.mode}, URLs: {len(urls)}, repetitions: {args.repetitions}, "
        f"concurrency: {args.concurrency}"
        + (f", latency: {args.latency}s" if args.mode == "local" else "")
    )
    print()
    print(format_results(results, len(urls)))
    print("\nMedian of all repetitions; speed-up is relative to sequential.")

    try:
        saved_path = await write_json(
            OUTPUT_PATH,
            {"conditions": conditions, "results": results},
        )
    except OSError as error:
        print(f"\nCould not save results to {OUTPUT_PATH}: {error}", file=sys.stderr)
        return 1

    print(f"\nResults saved to: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
