import contextlib
import json
import secrets
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os


async def write_json(
    output_path: str | Path,
    data: Any,
) -> Path:
    """Serialize data to JSON and write it asynchronously to a file.

    Missing parent directories are created. The JSON is written to a
    temporary file that atomically replaces the target only after a
    complete write, so a failure never leaves a truncated file behind.

    Raises TypeError or ValueError if the data cannot be serialized, and
    OSError if the file cannot be written.
    """
    path = Path(output_path)

    # Serialize first so invalid data never touches the filesystem.
    json_content = json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
    )

    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")

    try:
        async with aiofiles.open(
            temp_path,
            mode="w",
            encoding="utf-8",
        ) as output_file:
            await output_file.write(json_content)

        await aiofiles.os.replace(temp_path, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            await aiofiles.os.remove(temp_path)
        raise

    return path
