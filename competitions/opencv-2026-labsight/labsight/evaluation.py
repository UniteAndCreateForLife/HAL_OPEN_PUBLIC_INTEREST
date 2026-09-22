from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from .agent import LabSightAgent
from .synthetic import microscopy_scene


@dataclass(frozen=True)
class Scenario:
    name: str
    expected_status: str
    expects_enhancement: bool = False
    blur_sigma: float = 0.0
    illumination_gradient: float = 0.0
    clip_highlights: bool = False


SCENARIOS = (
    Scenario("clean", "accept"),
    Scenario("blurred", "request_recapture_focus", blur_sigma=5.0),
    Scenario("uneven", "accept", expects_enhancement=True, illumination_gradient=1.0),
    Scenario("clipped", "request_recapture_exposure", clip_highlights=True),
)


def evaluate(seeds: int = 10) -> tuple[dict, list[dict]]:
    if seeds < 1:
        raise ValueError("seeds must be >= 1")
    agent = LabSightAgent()
    rows: list[dict] = []
    latencies: list[float] = []

    for scenario in SCENARIOS:
        for seed in range(seeds):
            image = microscopy_scene(
                seed=seed,
                blur_sigma=scenario.blur_sigma,
                illumination_gradient=scenario.illumination_gradient,
                clip_highlights=scenario.clip_highlights,
            )
            start = time.perf_counter()
            result = agent.analyze(image)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
            rows.append(
                {
                    "scenario": scenario.name,
                    "seed": seed,
                    "expected_status": scenario.expected_status,
                    "actual_status": result.status,
                    "correct": result.status == scenario.expected_status,
                    "expects_enhancement": scenario.expects_enhancement,
                    "used_enhancement": result.used_enhancement,
                    "enhancement_correct": result.used_enhancement == scenario.expects_enhancement,
                    "trace_steps": len(result.trace),
                    "latency_ms": round(elapsed_ms, 3),
                    **{f"metric_{k}": v for k, v in result.metrics.to_dict().items()},
                }
            )

    correct = sum(bool(row["correct"]) for row in rows)
    enhancement_correct = sum(bool(row["enhancement_correct"]) for row in rows)
    sorted_latency = sorted(latencies)
    p95_index = min(len(sorted_latency) - 1, max(0, int(len(sorted_latency) * 0.95) - 1))
    major = int(cv2.__version__.split(".")[0])
    summary = {
        "samples": len(rows),
        "decision_accuracy": correct / len(rows),
        "agent_action_accuracy": enhancement_correct / len(rows),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 3),
            "median": round(statistics.median(latencies), 3),
            "p95": round(sorted_latency[p95_index], 3),
            "max": round(max(latencies), 3),
        },
        "runtime": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "opencv5_verified": major >= 5,
        },
        "scope": "synthetic microscopy QC regression corpus; not diagnostic validation",
    }
    return summary, rows


def write_report(output_dir: Path, seeds: int = 10) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary, rows = evaluate(seeds=seeds)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "samples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the HAL LabSight deterministic QC benchmark")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("evaluation/latest"))
    args = parser.parse_args()
    summary = write_report(args.output, seeds=args.seeds)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
