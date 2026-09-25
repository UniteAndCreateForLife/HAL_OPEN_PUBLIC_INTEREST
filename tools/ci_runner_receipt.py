from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a source-bound public runner receipt.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    source_sha = os.environ.get("SOURCE_SHA", "").strip()
    if not source_sha:
        raise SystemExit("SOURCE_SHA is required")

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": args.schema,
        "source_sha": source_sha,
        "runner_label": args.label,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "external_provider_call": False,
        "paid_runner_requested": False,
        "secrets_required": False,
    }
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
