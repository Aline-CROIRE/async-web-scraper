# Async Web Scraper

Fetches web pages concurrently with `asyncio` and `aiohttp`, extracts each page's title and email addresses with regular expressions, and saves the results as JSON. A benchmark compares the async version with sequential and threaded versions.

## Setup

You need Python 3.11 or newer.

```bash
git clone https://github.com/Aline-CROIRE/async-web-scraper.git
cd async-web-scraper
python -m venv .venv
```

Activate the virtual environment:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- macOS / Linux: `source .venv/bin/activate`

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
python -m src.run_scraper                    # scrape the default URLs, save output/scraped_results.json
python -m src.demo_cli                       # interactive menu for scraping your own URLs
python -m src.async_basics                   # short demo of coroutines and asyncio.gather
python -m src.run_benchmark                  # benchmark against a local test server
python -m src.run_benchmark --mode network   # benchmark against 20 public websites
```

Tests and code checks:

```bash
python -m pytest
python -m coverage run -m pytest
python -m coverage report
python -m ruff check .
python -m black --check .
```

## How asyncio is used

`asyncio` lets one thread wait on many I/O operations at the same time. A function defined with `async def` is a coroutine function. Calling it returns a coroutine object, which does nothing until it is awaited or scheduled on the event loop. When a coroutine reaches `await` on something slow, such as a network response, it pauses, and the event loop runs other coroutines until the response arrives. This is why a single thread can download many pages at once.

In this project:

- **Event loop:** each entry point starts it once with `asyncio.run(main())`.
- **Concurrent requests:** `iter_fetch_results` in `src/http_client.py` starts worker tasks with `asyncio.create_task()`. The workers share one `aiohttp.ClientSession`, and `max_concurrency` limits how many requests run at once. `asyncio.gather()` waits for the workers to shut down.
- **Timeouts:** every request is wrapped in `asyncio.wait_for()`.
- **Async generators:** `iter_fetch_results` (`src/http_client.py`) and `iter_page_results` (`src/async_generators.py`) `yield` each page as soon as it has been downloaded and processed. `scrape_urls` reads them with `async for`, so progress is printed in completion order, and then returns the results in the original URL order.
- **Decorators:** `@retry` (`src/retry.py`) retries timeouts, connection errors and 5xx responses, but not 4xx responses. `@rate_limit` (`src/rate_limit.py`) enforces a minimum gap between request start times.
- **Error handling:** a URL that fails is saved with `"success": false` and does not stop the other URLs.
- **Data processing:** `src/data_extraction.py` uses regular expressions to find titles and emails, then `map()` and `filter()` to normalise and validate the emails before removing duplicates.
- **Output:** `src/json_writer.py` writes the JSON with `aiofiles` to a `pathlib.Path`. It writes to a temporary file first, so a failed write never damages earlier results.

## Sample JSON output

Output of `python -m src.run_scraper` (`output/scraped_results.json`):

```json
[
    {
        "url": "https://example.com/",
        "success": false,
        "title": null,
        "emails": []
    },
    {
        "url": "https://www.iana.org/",
        "success": true,
        "title": "Internet Assigned Numbers Authority",
        "emails": []
    },
    {
        "url": "https://www.python.org/",
        "success": true,
        "title": "Welcome to Python.org",
        "emails": []
    }
]
```

Results are listed in the same order as the input URLs. `example.com` failed on the test machine because its TLS certificate could not be verified there.

## Performance comparison

`src/benchmark.py` fetches the same URLs in three ways:

- **Sequential:** one request at a time with `urllib`.
- **Threaded:** `urllib` in a `ThreadPoolExecutor`.
- **Async:** the scraper's own `aiohttp` code.

To keep the comparison fair, threaded and async both run up to 10 requests at once. All three use the same 10-second timeout, no retries and the same User-Agent. Each method runs 5 times, and the order of the methods changes each round. The tables show the median time, with the fastest and slowest of the 5 runs.

Test machine: Windows 11, 8 CPUs, Python 3.14.8, measured on 28 October 2026.

### Local test server

25 pages, each delayed by 0.1 seconds (`python -m src.run_benchmark`):

| Method     | Median  | Fastest | Slowest | Successful | Speed-up |
|------------|---------|---------|---------|------------|----------|
| Sequential | 2.787 s | 2.748 s | 2.985 s | 25/25      | 1.00x    |
| Threaded   | 0.359 s | 0.327 s | 0.383 s | 25/25      | 7.77x    |
| Async      | 0.346 s | 0.330 s | 0.371 s | 25/25      | 8.05x    |

### Public websites

20 URLs (`python -m src.run_benchmark --mode network`):

| Method     | Median   | Fastest | Slowest  | Successful | Speed-up |
|------------|----------|---------|----------|------------|----------|
| Sequential | 10.282 s | 8.166 s | 16.888 s | 17/20      | 1.00x    |
| Threaded   | 1.579 s  | 1.155 s | 1.819 s  | 17/20      | 6.51x    |
| Async      | 1.302 s  | 1.052 s | 1.478 s  | 17/20      | 7.90x    |

The same 3 URLs (`example.com`, `example.org` and `example.net`) failed for every method, because of the certificate problem described above.

### What the results show

- Both concurrent versions were 6 to 8 times faster than sequential. Almost all of the time is spent waiting for responses, and they wait for up to 10 at once.
- On the local server, threads and async performed about the same. The difference (0.359 s against 0.346 s) is smaller than the variation between runs.
- On the public websites async was faster (1.30 s against 1.58 s). A likely reason is that `aiohttp` reuses connections to the same host, while `urllib` opens a new connection for every request.
- Async is not automatically faster than threads. Its advantage is that it waits on many requests from a single thread, which matters most when there are hundreds or thousands of them. It does not speed up CPU-heavy work.
- Network timings vary a lot (sequential took between 8.2 and 16.9 seconds), so your results will differ.

Each run saves every measurement and the test conditions to `output/benchmark_results.json`.
