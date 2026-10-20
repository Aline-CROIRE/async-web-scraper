# Async Web Scraper

A Python project for learning asynchronous web scraping with `asyncio` and `aiohttp`.

## Requirements

- Python 3.11+
- aiohttp
- aiofiles
- pytest
- pytest-asyncio

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Planned Features

- Asynchronous HTTP requests
- Concurrent fetching with `asyncio.gather()`
- Task management with `asyncio.create_task()`
- Async generators and decorators
- Data extraction using regular expressions
- JSON output
- Performance comparison: sequential, threaded, and asynchronous execution

## Testing

Run the tests with:

```powershell
python -m pytest -v
```

## Performance Benchmark

Benchmark results will be added after implementing and testing the three approaches.

## Sample Output

A sample JSON output will be included after the scraper is implemented.