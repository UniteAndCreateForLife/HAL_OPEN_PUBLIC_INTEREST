from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from submission_gate import BRIEF, RULES, build_receipt

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "evidence" / "application_packet"
TOPIC_HEADINGS = {
    "problem": "Problem",
    "target customer": "Target customer",
    "market need": "Market need",
    "MVP description": "MVP description",
    "live or recorded demonstration": "Demonstration",
    "current stage": "Current stage",
    "users/pilots/revenue/validation where available": "Users, pilots, revenue, validation",
    "business model": "Business model",
    "pricing approach": "Pricing approach",
    "technology architecture": "Technology architecture",
    "data privacy": "Data privacy",
    "security": "Security",
    "responsible-AI considerations": "Responsible AI",
    "scale-up plan": "Scale-up plan",
    "founder/core-team profile": "Founder / core team",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def parse_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        if line.startswith("## "):
            current = normalize_heading(line[3:])
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {
        name: "\n".join(lines).strip()
        for name, lines in sections.items()
        if "\n".join(lines).strip()
    }


def extract_application_fields(
    brief_text: str, rules: dict[str, Any]
) -> dict[str, str]:
    sections = parse_sections(brief_text)
    fields: dict[str, str] = {}
    missing: list[str] = []
    for topic in rules["required_application_topics"]:
        heading = TOPIC_HEADINGS.get(topic)
        value = sections.get(normalize_heading(heading or ""), "")
        if not heading or not value:
            missing.append(topic)
        else:
            fields[topic] = value
    if missing:
        raise ValueError(f"missing application field content: {', '.join(missing)}")
    return fields


def human_gate_map(rules: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for gate in rules["human_gates"]:
        key = normalize_heading(gate).replace(" ", "_")
        result[key] = (
            "REQUIRES_HUMAN_ACTION"
            if gate == "final form submission"
            else "REQUIRES_HUMAN_ATTESTATION"
        )
    return result


def build_packet() -> dict[str, Any]:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    brief_text = BRIEF.read_text(encoding="utf-8")
    readiness = build_receipt()
    claims = readiness["claims"]
    if not claims or any(value is not False for value in claims.values()):
        raise ValueError("readiness receipt contains unsupported positive claim")
    return {
        "schema_version": 1,
        "scope": "prepared_application_fields_not_submission_or_eligibility_attestation",
        "source_commit": git_head(),
        "competition": rules["competition"],
        "stream": rules["stream"],
        "deadline": rules["deadline"],
        "startup_prize_inr": rules["startup_prize_inr"],
        "application_fields": extract_application_fields(brief_text, rules),
        "human_gates": human_gate_map(rules),
        "claims": claims,
        "application_brief_sha256": sha256(BRIEF),
        "rules_snapshot_sha256": sha256(RULES),
    }


def verify_packet(
    packet: dict[str, Any], expected_head: str | None = None
) -> dict[str, Any]:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    head = expected_head or git_head()
    if packet.get("source_commit") != head:
        raise ValueError("application packet source commit drift")
    if packet.get("deadline") != rules["deadline"]:
        raise ValueError("application packet deadline drift")
    if packet.get("startup_prize_inr") != rules["startup_prize_inr"]:
        raise ValueError("application packet prize drift")
    if packet.get("application_brief_sha256") != sha256(BRIEF):
        raise ValueError("application brief SHA-256 drift")
    if packet.get("rules_snapshot_sha256") != sha256(RULES):
        raise ValueError("rules snapshot SHA-256 drift")
    fields = packet.get("application_fields") or {}
    expected_topics = rules["required_application_topics"]
    if list(fields) != expected_topics:
        raise ValueError("application field set/order drift")
    if any(
        not isinstance(fields[name], str) or not fields[name].strip()
        for name in expected_topics
    ):
        raise ValueError("application packet contains empty field content")
    expected_gates = human_gate_map(rules)
    if packet.get("human_gates") != expected_gates:
        raise ValueError("application packet human-gate drift")
    expected_claims = {
        "submitted": False,
        "finalist": False,
        "awarded": False,
        "paid": False,
        "production_deployed": False,
        "institutional_pilot": False,
    }
    if packet.get("claims") != expected_claims:
        raise ValueError(
            "application packet contains unsupported competition-state claim"
        )
    return {
        "status": "PASS",
        "source_commit": head,
        "field_count": len(fields),
        "human_gate_count": len(expected_gates),
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Global Smart Campus 2026 — Application Field Packet",
        "",
        f"Source commit: `{packet['source_commit']}`",
        f"Deadline: {packet['deadline']}",
        f"Startup-stream prize: INR {packet['startup_prize_inr']:,} (competitive; not guaranteed)",
        "",
        "> Preparation artifact only. It does not submit the application or make eligibility, finalist, award, payment, deployment, pilot, or revenue claims.",
        "",
    ]
    for topic, value in packet["application_fields"].items():
        lines.extend([f"## {topic}", "", value, ""])
    lines.extend(["## Human-only gates", ""])
    for gate, state in packet["human_gates"].items():
        lines.append(f"- {gate}: `{state}`")
    lines.extend(["", "## Competition-status claims", ""])
    for name, value in packet["claims"].items():
        lines.append(f"- {name}: `{str(value).lower()}`")
    lines.append("")
    return "\n".join(lines)


def write_packet(out_dir: Path) -> dict[str, Any]:
    packet = build_packet()
    verification = verify_packet(packet)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "APPLICATION_FIELDS.json"
    md_path = out_dir / "APPLICATION_FIELDS.md"
    json_path.write_text(
        json.dumps(packet, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md_path.write_text(render_markdown(packet), encoding="utf-8", newline="\n")
    return {
        **verification,
        "json": str(json_path),
        "json_sha256": sha256(json_path),
        "markdown": str(md_path),
        "markdown_sha256": sha256(md_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify a form-ready Smart Campus application packet."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        packet = json.loads(args.verify.read_text(encoding="utf-8"))
        print(json.dumps(verify_packet(packet), sort_keys=True))
        return 0
    print(json.dumps(write_packet(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
