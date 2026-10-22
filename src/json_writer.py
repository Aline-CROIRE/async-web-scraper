import json
from pathlib import Path
from typing import Any

import aiofiles


async def write_json(
    output_path: str | Path,
    data: Any,
) -> None:
    """Serialize data to JSON and write it asynchronously to a file."""
    json_content = json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
    )

    async with aiofiles.open(
        output_path,
        mode="w",
        encoding="utf-8",
    ) as output_file:
        await output_file.write(json_content)
