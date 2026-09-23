from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_lf(path: Path, payload: Any, *, sort_keys: bool = True) -> None:
    """Write deterministic UTF-8 JSON with LF bytes on every platform."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n",
        encoding="utf-8",
        newline="\n",
    )
