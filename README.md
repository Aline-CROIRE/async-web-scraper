# Async Web Scraper

An asynchronous web scraping application built with Python. It fetches web pages concurrently, extracts page titles and email addresses, handles request failures, and saves structured results as JSON.

## Features

- **Asynchronous HTTP requests:** Fetch multiple web pages without waiting for each network request to finish before starting another.
- **HTML data extraction:** Extract page titles and email addresses from fetched HTML.
- **Email normalization:** Normalize extracted email addresses and remove duplicates.
- **Bounded concurrency:** Limit the number of requests running concurrently.
- **Timeout handling:** Prevent requests from waiting indefinitely.
- **Retry handling:** Retry eligible temporary failures.
- **Rate limiting:** Control the pace of requests.
- **Error handling:** Record failed requests while allowing other URLs to be processed.
- **JSON output:** Save scraping results to a JSON file.
- **Interactive CLI:** Enter URLs, configure concurrency, view results, and inspect previously saved output.
- **Automated testing:** Validate functionality and error handling with pytest.

## Project Structure

```text
async-web-scraper/
├── src/
│   ├── __init__.py
│   ├── async_basics.py
│   ├── async_generators.py
│   ├── data_extraction.py
│   ├── demo_cli.py
│   ├── http_client.py
│   ├── json_writer.py
│   ├── rate_limit.py
│   ├── retry.py
│   ├── run_benchmark.py
│   └── run_scraper.py
├── tests/
│   ├── test_async_basics.py
│   ├── test_async_generators.py
│   ├── test_benchmark.py
│   ├── test_data_extraction.py
│   ├── test_http_client.py
│   ├── test_json_writer.py
│   ├── test_rate_limit.py
│   ├── test_retry.py
│   └── test_scraper.py
├── output/
│   └── scraped_results.json
├── requirements.txt
└── README.md
```


## Requirements

- Python 3.11 or newer, compatible with the project's dependencies
- pip
- Git (for cloning and version control)

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/Aline-CROIRE/async-web-scraper.git
cd async-web-scraper
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, follow your organization's approved setup instructions or activate the environment using another supported method.

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Usage

There are two ways to run the scraper.

### 1. Run the default scraper

```powershell
python -m src.run_scraper
```

This runs the configured default URLs, extracts page titles and email addresses, displays a summary, and saves the results to:

```text
output/scraped_results.json
```

To change the default websites, edit the `URLS` list in `src/run_scraper.py`.

### 2. Run the interactive CLI

```powershell
python -m src.demo_cli
```

The interactive menu provides three options:

1. **Scrape websites:** Enter URLs or use the default demo websites.
2. **View previous results:** Display the JSON results saved by the most recent run.
3. **Exit:** Close the application.

When scraping websites, enter full HTTP or HTTPS URLs separated by commas. For example:

```text
https://example.com/, https://www.python.org/
```

Then select the maximum number of concurrent requests, from 1 to 10. Press Enter to use the default value of 5.

The interactive CLI uses the same scraping implementation as the default runner. This keeps the user interface separate from the core scraping logic.

## Output

Scraping results are saved to:

```text
output/scraped_results.json
```

Each result contains information such as the URL, whether the request succeeded, the extracted page title, and the list of email addresses found.

A simplified example of one result is:

```json
{
  "url": "https://example.com/",
  "success": true,
  "title": "Example Domain",
  "emails": []
}
```

This example illustrates the general result structure; the exact fields and values depend on the implementation and the website being scraped.

## Run the Tests

Run all automated tests:

```powershell
python -m pytest -v
```

Run the test suite with coverage:

```powershell
python -m coverage run -m pytest
python -m coverage report -m
```

Check code quality with Ruff:

```powershell
python -m ruff check src tests
```

Check formatting with Black:

```powershell
python -m black --check src tests
```

## Benchmark

Run the benchmark module to compare the implemented approaches:

```powershell
python -m src.run_benchmark
```

Review the benchmark output to understand how different approaches perform. Actual timings depend on network conditions, server response times, and the test URLs.

## How It Works

1. The runner or interactive CLI obtains the URLs to scrape.
2. The scraper coordinates the scraping workflow.
3. The HTTP client fetches the pages asynchronously, applying the configured request controls.
4. The extraction module parses the returned HTML and extracts titles and email addresses.
5. The scraper collects successful and failed results.
6. The JSON writer saves the results to the output file.
7. The runner displays a summary of the scraping process.

## Key Python Concepts

This project demonstrates:

- `async` and `await` for asynchronous programming.
- `asyncio` for coordinating concurrent tasks.
- Asynchronous HTTP requests with `aiohttp`.
- Exception handling and timeouts.
- Retry strategies and rate limiting.
- HTML parsing and regular expressions.
- JSON serialization and file handling.
- Separation of concerns and modular design.
- Automated testing with pytest.
- Code quality and formatting with Ruff and Black.
- Git branching, commits, and collaborative development workflows.

## Responsible Scraping

- Scrape only websites you are permitted to access.
- Review a website's Terms of Service and `robots.txt` guidance before scraping.
- Respect rate limits and avoid sending excessive requests.
- Do not attempt to bypass authentication, access controls, or anti-bot protections.
- Avoid collecting or publishing personal or sensitive information.
- A successful HTTP response does not guarantee that a page contains extractable titles or email addresses.

## License

Add a license file if you intend to distribute this project under an open-source license. Until then, no particular open-source license is implied.
