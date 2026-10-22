import json

import pytest

from src.json_writer import write_json


@pytest.mark.asyncio
async def test_write_json_saves_data(tmp_path):
    output_file = tmp_path / "results.json"
    data = {
        "title": "Example Page",
        "emails": ["alice@example.com", "bob@example.org"],
    }

    await write_json(output_file, data)

    saved_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert saved_data == data


@pytest.mark.asyncio
async def test_write_json_preserves_unicode(tmp_path):
    output_file = tmp_path / "results.json"
    data = {"title": "Muraho, Kigali! 👋"}

    await write_json(output_file, data)

    saved_text = output_file.read_text(encoding="utf-8")
    assert "Kigali" in saved_text
    assert "👋" in saved_text
    assert json.loads(saved_text) == data


@pytest.mark.asyncio
async def test_write_json_rejects_non_serializable_data(tmp_path):
    output_file = tmp_path / "results.json"

    with pytest.raises(TypeError):
        await write_json(output_file, {"invalid": object()})
