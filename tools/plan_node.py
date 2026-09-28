from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hal_public_interest.node import build_node_plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a local-only HAL Node plan without contacting a provider."
    )
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--route-id", default="ollama-local")
    parser.add_argument("--audit-ledger", default="audit/node-events.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = build_node_plan(
        args.model,
        endpoint=args.endpoint,
        route_id=args.route_id,
        audit_ledger=args.audit_ledger,
    )
    encoded = json.dumps(plan.to_dict(), indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
