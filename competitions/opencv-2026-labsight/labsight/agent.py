from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

import numpy as np

from .metrics import ImageMetrics, compute_metrics, improve_illumination

Action = Literal[
    "accept",
    "request_recapture_focus",
    "request_recapture_exposure",
    "enhance_and_reanalyze",
    "human_review",
]


@dataclass(frozen=True)
class AgentConfig:
    min_focus_variance: float = 85.0
    max_illumination_cv: float = 0.18
    max_saturation_fraction: float = 0.08
    min_foreground_fraction: float = 0.002
    max_foreground_fraction: float = 0.55
    min_edge_density: float = 0.002


@dataclass
class TraceStep:
    step: int
    observation: dict[str, float | int]
    decision: Action
    reason: str


@dataclass
class AnalysisResult:
    status: Action
    metrics: ImageMetrics
    trace: list[TraceStep] = field(default_factory=list)
    used_enhancement: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "metrics": self.metrics.to_dict(),
            "trace": [asdict(step) for step in self.trace],
            "used_enhancement": self.used_enhancement,
        }


class LabSightAgent:
    """Auditable perception -> decision -> action loop."""

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()

    def _decide(self, metrics: ImageMetrics, allow_enhance: bool) -> tuple[Action, str]:
        c = self.config
        if metrics.saturation_fraction > c.max_saturation_fraction:
            return "request_recapture_exposure", "too many clipped dark/bright pixels"
        if metrics.focus_variance < c.min_focus_variance:
            return "request_recapture_focus", "focus score is below acceptance threshold"
        if metrics.illumination_cv > c.max_illumination_cv and allow_enhance:
            return "enhance_and_reanalyze", "illumination is uneven; run CLAHE and re-measure"
        if metrics.illumination_cv > c.max_illumination_cv:
            return "request_recapture_exposure", "illumination remains uneven after correction"
        if not (c.min_foreground_fraction <= metrics.foreground_fraction <= c.max_foreground_fraction):
            return "human_review", "segmentation occupancy is outside the expected QC range"
        if metrics.edge_density < c.min_edge_density:
            return "human_review", "insufficient visual structure for reliable automated QC"
        return "accept", "image passes deterministic microscopy QC gates"

    def analyze(self, image: np.ndarray) -> AnalysisResult:
        trace: list[TraceStep] = []
        metrics = compute_metrics(image)
        action, reason = self._decide(metrics, allow_enhance=True)
        trace.append(TraceStep(1, metrics.to_dict(), action, reason))

        if action != "enhance_and_reanalyze":
            return AnalysisResult(status=action, metrics=metrics, trace=trace)

        enhanced = improve_illumination(image)
        metrics2 = compute_metrics(enhanced)
        action2, reason2 = self._decide(metrics2, allow_enhance=False)
        trace.append(TraceStep(2, metrics2.to_dict(), action2, reason2))
        return AnalysisResult(
            status=action2,
            metrics=metrics2,
            trace=trace,
            used_enhancement=True,
        )
