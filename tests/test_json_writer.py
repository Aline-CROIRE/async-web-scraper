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


@pytest.mark.asyncio
async def test_write_json_creates_missing_parent_directories(tmp_path):
    output_file = tmp_path / "nested" / "deeper" / "results.json"

    saved_path = await write_json(output_file, [1, 2, 3])

    assert saved_path == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == [1, 2, 3]


@pytest.mark.asyncio
async def test_write_json_accepts_string_paths(tmp_path):
    output_file = tmp_path / "results.json"

    saved_path = await write_json(str(output_file), {"ok": True})

    assert saved_path == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == {"ok": True}


@pytest.mark.asyncio
async def test_write_json_replaces_existing_file(tmp_path):
    output_file = tmp_path / "results.json"
    await write_json(output_file, {"version": 1})

    await write_json(output_file, {"version": 2})

    assert json.loads(output_file.read_text(encoding="utf-8")) == {"version": 2}
    assert [path.name for path in tmp_path.iterdir()] == ["results.json"]


@pytest.mark.asyncio
async def test_failed_write_keeps_previous_file_and_removes_temp_file(
    tmp_path,
    monkeypatch,
):
    output_file = tmp_path / "results.json"
    await write_json(output_file, {"version": "previous"})

    async def failing_replace(source, destination):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("src.json_writer.aiofiles.os.replace", failing_replace)

    with pytest.raises(OSError, match="No space left"):
        await write_json(output_file, {"version": "new"})

    assert json.loads(output_file.read_text(encoding="utf-8")) == {
        "version": "previous"
    }
    assert [path.name for path in tmp_path.iterdir()] == ["results.json"]


@pytest.mark.asyncio
async def test_non_serializable_data_does_not_touch_existing_file(tmp_path):
    output_file = tmp_path / "results.json"
    await write_json(output_file, {"version": "previous"})

    with pytest.raises(TypeError):
        await write_json(output_file, {"invalid": object()})

    assert json.loads(output_file.read_text(encoding="utf-8")) == {
        "version": "previous"
    }
    assert [path.name for path in tmp_path.iterdir()] == ["results.json"]


@pytest.mark.asyncio
async def test_write_json_raises_os_error_when_parent_is_a_file(tmp_path):
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("x", encoding="utf-8")

    with pytest.raises(OSError):
        await write_json(blocking_file / "results.json", [])
