import json

import pytest

from src import demo_cli

RESULTS = [
    {
        "url": "https://example.com/",
        "success": True,
        "title": "Example Domain",
        "emails": ["info@example.com"],
    },
    {
        "url": "https://unavailable.example/",
        "success": False,
        "title": None,
        "emails": [],
    },
]


def answer_prompts(monkeypatch, *answers):
    """Make input() return the given answers in order."""
    remaining = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(remaining))


def test_get_urls_uses_defaults_when_input_is_empty(monkeypatch):
    answer_prompts(monkeypatch, "")

    urls = demo_cli.get_urls()

    assert urls == demo_cli.DEFAULT_URLS
    assert urls is not demo_cli.DEFAULT_URLS  # A copy, so callers cannot mutate it.


def test_get_urls_keeps_valid_unique_urls_and_skips_invalid_ones(
    monkeypatch,
    capsys,
):
    answer_prompts(
        monkeypatch,
        " https://a.example/ , ftp://files.example, not a url, "
        "https://a.example/, http://b.example:8080/page, https://bad.example:0/, "
        "http://[broken",
    )

    urls = demo_cli.get_urls()

    assert urls == ["https://a.example/", "http://b.example:8080/page"]
    output = capsys.readouterr().out
    assert "Skipping invalid URL: ftp://files.example" in output
    assert "Skipping invalid URL: not a url" in output
    assert "Skipping invalid URL: https://bad.example:0/" in output
    assert "Skipping invalid URL: http://[broken" in output


def test_get_concurrency_defaults_to_five(monkeypatch):
    answer_prompts(monkeypatch, "")

    assert demo_cli.get_concurrency() == 5


def test_get_concurrency_asks_again_until_value_is_valid(monkeypatch, capsys):
    answer_prompts(monkeypatch, "many", "0", "11", "7")

    assert demo_cli.get_concurrency() == 7

    output = capsys.readouterr().out
    assert output.count("Please enter a whole number.") == 1
    assert output.count("Choose a number between 1 and 10.") == 2


def test_display_results_shows_each_result_and_summary(capsys):
    demo_cli.display_results(RESULTS)

    output = capsys.readouterr().out
    assert "[1/2] https://example.com/" in output
    assert "Status: SUCCESS" in output
    assert "- info@example.com" in output
    assert "[2/2] https://unavailable.example/" in output
    assert "Status: FAILED" in output
    assert "Title: Not found" in output
    assert "Completed: 1/2 websites successful" in output


def test_show_progress_reports_success_and_failure(capsys):
    demo_cli.show_progress(RESULTS[0])
    demo_cli.show_progress(RESULTS[1])

    assert capsys.readouterr().out == (
        "  done: https://example.com/\n  failed: https://unavailable.example/\n"
    )


@pytest.mark.asyncio
async def test_scrape_interactively_returns_when_no_valid_urls(monkeypatch, capsys):
    async def unexpected_scrape(urls, **kwargs):
        raise AssertionError("scrape_urls should not be called")

    answer_prompts(monkeypatch, "not a url")
    monkeypatch.setattr(demo_cli, "scrape_urls", unexpected_scrape)

    await demo_cli.scrape_interactively()

    assert "No valid URLs were provided" in capsys.readouterr().out


def test_view_saved_results_when_no_file_exists(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", tmp_path / "missing.json")

    demo_cli.view_saved_results()

    assert "No saved results found" in capsys.readouterr().out


def test_view_saved_results_prints_saved_json(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "results.json"
    output_path.write_text(json.dumps(RESULTS), encoding="utf-8")
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", output_path)

    demo_cli.view_saved_results()

    output = capsys.readouterr().out
    assert "Saved results from" in output
    assert '"title": "Example Domain"' in output


def test_view_saved_results_reports_invalid_json(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "results.json"
    output_path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", output_path)

    demo_cli.view_saved_results()

    assert "Could not read saved results" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_main_menu_handles_every_choice(tmp_path, monkeypatch, capsys):
    scraped = []

    async def fake_scrape_interactively():
        scraped.append(True)

    monkeypatch.setattr(demo_cli, "scrape_interactively", fake_scrape_interactively)
    monkeypatch.setattr(demo_cli, "OUTPUT_PATH", tmp_path / "missing.json")
    answer_prompts(monkeypatch, "1", "2", "9", "3")

    await demo_cli.main()

    output = capsys.readouterr().out
    assert scraped == [True]
    assert "No saved results found" in output
    assert "Invalid choice. Please enter 1, 2, or 3." in output
    assert "Goodbye!" in output


@pytest.mark.asyncio
async def test_main_menu_reports_invalid_scraper_configuration(monkeypatch, capsys):
    async def broken_scrape_interactively():
        raise ValueError("max_concurrency must be at least 1")

    monkeypatch.setattr(
        demo_cli,
        "scrape_interactively",
        broken_scrape_interactively,
    )
    answer_prompts(monkeypatch, "1", "3")

    await demo_cli.main()

    output = capsys.readouterr().out
    assert "Invalid scraper configuration: max_concurrency must be at least 1" in output
    assert "Goodbye!" in output
