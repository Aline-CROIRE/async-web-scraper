import json

import pytest

from src import demo_cli, run_benchmark, run_scraper

RESULTS = [
    {
        "url": "https://example.com/",
        "success": True,
        "title": "Example Domain",
        "emails": [],
    },
]

BENCHMARK_RESULTS = {
    method: {
        "elapsed_seconds": 0.1,
        "min_seconds": 0.1,
        "max_seconds": 0.1,
        "successful_requests": 3,
        "runs": [{"elapsed_seconds": 0.1, "successful_requests": 3}],
    }
    for method in ("sequential", "threaded", "async")
}


async def fake_scrape_urls(urls, **kwargs):
    return RESULTS


async def fake_benchmark_fetching(urls, **kwargs):
    return BENCHMARK_RESULTS


@pytest.fixture
def unwritable_path(tmp_path):
    """A path whose parent is a regular file, so it can never be written."""
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("x", encoding="utf-8")
    return blocking_file / "results.json"


@pytest.mark.asyncio
async def test_run_scraper_saves_results_and_succeeds(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "output" / "scraped_results.json"
    monkeypatch.setattr(run_scraper, "scrape_urls", fake_scrape_urls)
    monkeypatch.setattr(run_scraper, "OUTPUT_PATH", output_path)

    assert await run_scraper.main() == 0

    assert json.loads(output_path.read_text(encoding="utf-8")) == RESULTS
    assert "JSON saved to:" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_run_scraper_reports_save_failure_after_showing_results(
    unwritable_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(run_scraper, "scrape_urls", fake_scrape_urls)
    monkeypatch.setattr(run_scraper, "OUTPUT_PATH", unwritable_path)

    assert await run_scraper.main() == 1

    captured = capsys.readouterr()
    assert "Example Domain" in captured.out
    assert "JSON saved to:" not in captured.out
    assert "Could not save results to" in captured.err


@pytest.mark.asyncio
async def test_run_benchmark_saves_results_and_succeeds(
    tmp_path,
    monkeypatch,
    capsys,
):
    output_path = tmp_path / "output" / "benchmark_results.json"
    monkeypatch.setattr(run_benchmark, "benchmark_fetching", fake_benchmark_fetching)
    monkeypatch.setattr(run_benchmark, "OUTPUT_PATH", output_path)

    assert await run_benchmark.main([]) == 0

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["results"] == BENCHMARK_RESULTS
    assert saved["conditions"]["mode"] == "local"
    assert saved["conditions"]["url_count"] == 25
    assert "Results saved to:" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_run_benchmark_reports_save_failure_after_showing_results(
    unwritable_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(run_benchmark, "benchmark_fetching", fake_benchmark_fetching)
    monkeypatch.setattr(run_benchmark, "OUTPUT_PATH", unwritable_path)

    assert await run_benchmark.main([]) == 1

    captured = capsys.readouterr()
    assert "sequential" in captured.out
    assert "Results saved to:" not in captured.out
    assert "Could not save results to" in captured.err


def use_default_cli_answers(monkeypatch):
    """Answer the URL and concurrency prompts with their defaults."""
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))


@pytest.mark.asyncio
async def test_demo_cli_saves_results(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "output" / "scraped_results.json"
    use_default_cli_answers(monkeypatch)
    monkeypatch.setattr(demo_cli, "scrape_urls", fake_scrape_urls)
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", output_path)

    await demo_cli.scrape_interactively()

    assert json.loads(output_path.read_text(encoding="utf-8")) == RESULTS
    assert "JSON saved to:" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_demo_cli_reports_save_failure_without_crashing(
    unwritable_path,
    monkeypatch,
    capsys,
):
    use_default_cli_answers(monkeypatch)
    monkeypatch.setattr(demo_cli, "scrape_urls", fake_scrape_urls)
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", unwritable_path)

    await demo_cli.scrape_interactively()

    output = capsys.readouterr().out
    assert "Example Domain" in output
    assert "Could not save results to" in output
    assert "JSON saved to:" not in output


def test_run_scraper_show_progress_reports_success_and_failure(capsys):
    run_scraper.show_progress(RESULTS[0])
    run_scraper.show_progress({**RESULTS[0], "success": False})

    assert capsys.readouterr().out == (
        "  done: https://example.com/\n  failed: https://example.com/\n"
    )


@pytest.mark.asyncio
async def test_run_benchmark_network_mode_uses_public_url_list(
    tmp_path,
    monkeypatch,
):
    received = {}

    async def recording_benchmark_fetching(urls, **kwargs):
        received["urls"] = urls
        received["options"] = kwargs
        return BENCHMARK_RESULTS

    output_path = tmp_path / "benchmark_results.json"
    monkeypatch.setattr(
        run_benchmark,
        "benchmark_fetching",
        recording_benchmark_fetching,
    )
    monkeypatch.setattr(run_benchmark, "OUTPUT_PATH", output_path)

    exit_code = await run_benchmark.main(
        ["--mode", "network", "--repetitions", "2", "--concurrency", "4"]
    )

    assert exit_code == 0
    assert received["urls"] == run_benchmark.NETWORK_URLS
    assert len(run_benchmark.NETWORK_URLS) >= 20
    assert received["options"] == {"repetitions": 2, "concurrency": 4, "timeout": 10.0}
    conditions = json.loads(output_path.read_text(encoding="utf-8"))["conditions"]
    assert conditions["mode"] == "network"
    assert conditions["latency_seconds"] is None


@pytest.mark.parametrize(
    "argv",
    [
        ["--repetitions", "0"],
        ["--concurrency", "-1"],
        ["--pages", "two"],
        ["--latency", "-0.5"],
        ["--latency", "nan"],
        ["--latency", "inf"],
        ["--timeout", "0"],
        ["--mode", "cloud"],
    ],
)
def test_run_benchmark_rejects_invalid_arguments(argv, capsys):
    with pytest.raises(SystemExit) as exit_info:
        run_benchmark.parse_args(argv)

    assert exit_info.value.code == 2
    assert "error: argument" in capsys.readouterr().err


def test_run_benchmark_format_results_shows_speed_up():
    results = {
        "sequential": {
            "elapsed_seconds": 2.0,
            "min_seconds": 1.9,
            "max_seconds": 2.1,
            "successful_requests": 20,
        },
        "threaded": {
            "elapsed_seconds": 0.5,
            "min_seconds": 0.4,
            "max_seconds": 0.6,
            "successful_requests": 20,
        },
        "async": {
            "elapsed_seconds": 0.0,
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "successful_requests": 19,
        },
    }

    table = run_benchmark.format_results(results, url_count=20)

    lines = table.splitlines()
    assert lines[0].split() == [
        "Method",
        "Median",
        "Min",
        "Max",
        "Successful",
        "Speed-up",
    ]
    assert lines[1].split()[-1] == "1.00x"
    assert lines[2].split()[-1] == "4.00x"
    assert lines[3].split()[-1] == "n/a"
    assert "19/20" in lines[3]
