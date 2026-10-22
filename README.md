# Async Web Scraper

A Python project demonstrating asynchronous web scraping, concurrent HTTP requests, error handling, data extraction, asynchronous file I/O, and performance benchmarking.

## Features

- Fetch multiple URLs concurrently using `asyncio` and `aiohttp`.
- Manage concurrent operations with `asyncio.gather()` and `asyncio.create_task()`.
- Apply timeouts and retry temporary request failures.
- Handle HTTP errors and failed requests without losing successful results.
- Use an asynchronous generator with `async for` to yield fetched page results.
- Apply retry and rate-limit decorators.
- Extract HTML page titles and email addresses using regular expressions.
- Transform email data using `map()` and `filter()`, normalize addresses, and remove duplicates.
- Save scraping and benchmark results as JSON using asynchronous file I/O.
- Compare sequential, threaded, and asynchronous fetching performance.
- Test functionality with `pytest` and check code quality with Black and Ruff.

## Requirements

- Python 3.11 or newer
- The dependencies listed in `requirements.txt`

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run the scraper

Run the integrated scraping workflow:

```powershell
python -m src.run_scraper
```

The program fetches the configured URLs concurrently, extracts each page's title and email addresses, and saves the results to:

`output/scraped_results.json`

The default URLs are configured in `src/run_scraper.py`. Edit the `URLS` list to scrape other pages.

Each result contains:

- `url`: the page URL
- `success`: whether fetching succeeded
- `title`: the extracted page title, or `null` if none was found
- `emails`: normalized, unique email addresses found on the page

Failed requests are recorded with `success` set to `false`, a `null` title, and an empty email list.

## Run the performance benchmark

Run:

```powershell
python -m src.run_benchmark
```

The benchmark compares three approaches using the same URLs:

1. **Sequential:** fetches URLs one after another using blocking standard-library HTTP.
2. **Threaded:** fetches URLs concurrently using `ThreadPoolExecutor`.
3. **Async:** fetches URLs concurrently using `asyncio` and `aiohttp`.

Benchmark results are saved to:

`output/benchmark_results.json`

### Example benchmark results

One successful run with three URLs produced these measurements:

| Method | Elapsed time | Successful requests |
| --- | ---: | ---: |
| Sequential | 1.805503 seconds | 3/3 |
| Threaded | 0.706765 seconds | 3/3 |
| Async | 0.709232 seconds | 3/3 |

In this run, both concurrent approaches completed faster than sequential fetching. Threaded fetching was approximately 2.55 times as fast as sequential fetching, and asynchronous fetching was approximately 2.54 times as fast.

These are sample measurements, not guaranteed results. Network conditions, server response times, and other environmental factors can change benchmark timings.

## Sample JSON output

A successful scraping result has this structure:

```json
[
    {
        "url": "https://example.com/",
        "success": true,
        "title": "Example Domain",
        "emails": []
    }
]
```

Actual output depends on the content returned by each website.

## Project structure

```text
async-web-scraper/
├── src/
│   ├── async_basics.py
│   ├── async_generators.py
│   ├── benchmark.py
│   ├── data_extraction.py
│   ├── http_client.py
│   ├── json_writer.py
│   ├── rate_limit.py
│   ├── retry.py
│   ├── run_benchmark.py
│   ├── run_scraper.py
│   └── scraper.py
├── tests/
├── output/
├── requirements.txt
└── README.md
```

## Testing

Run the complete test suite:

```powershell
python -m pytest -v
```

Run formatting and lint checks:

```powershell
python -m black --check src tests
python -m ruff check src tests
```

Measure test coverage, including branches:

```powershell
python -m coverage run --branch -m pytest
python -m coverage report -m
```

## Demonstration

For the lab demonstration, show concurrent fetching, error handling, extracted page data, the generated JSON output, and the benchmark comparison.
