from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .agent import LabSightAgent
from .observability import emit_qc_metrics
from .runtime import (
    EXPECTED_CV2_VERSION,
    EXPECTED_OPENCV_DISTRIBUTION,
    competition_runtime_info,
)
from .synthetic import microscopy_scene
from .web import DEMO_HTML

EXPECTED_OPENCV_VERSION = EXPECTED_OPENCV_DISTRIBUTION

app = FastAPI(title="HAL LabSight", version="0.4.0")
agent = LabSightAgent()
logger = logging.getLogger("labsight.api")


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded PNG/JPEG image bytes")


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.headers["x-labsight-request-id"] = request_id
    response.headers["server-timing"] = f"labsight;dur={elapsed_ms:.3f}"
    logger.info(json.dumps({
        "event": "http_request",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "elapsed_ms": round(elapsed_ms, 3),
    }, separators=(",", ":")))
    return response


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    return DEMO_HTML


def _competition_runtime_verified(distribution_version: str | None, runtime_version: str) -> bool:
    """Verify both wheel revision and OpenCV core version."""
    return (
        distribution_version == EXPECTED_OPENCV_DISTRIBUTION
        and runtime_version == EXPECTED_CV2_VERSION
    )


@app.get("/health")
def health() -> dict[str, str | bool | None]:
    runtime = competition_runtime_info()
    return {
        "status": "ok",
        "service": "hal-labsight",
        "version": "0.4.0",
        "build_sha": os.environ.get("LABSIGHT_BUILD_SHA", "unknown"),
        "opencv": str(runtime["opencv_runtime"]),
        "opencv_runtime_version": str(runtime["opencv_runtime"]),
        "opencv_distribution": runtime["opencv_distribution"],
        "opencv_distribution_version": runtime["opencv_distribution"],
        "expected_opencv": EXPECTED_OPENCV_VERSION,
        "expected_cv2": EXPECTED_CV2_VERSION,
        "numpy": np.__version__,
        "opencv5_verified": bool(runtime["opencv5_verified"]),
    }


def _analyze_image(image: np.ndarray, *, request_id: str = "unknown", source: str = "upload") -> dict:
    started = time.perf_counter()
    result = agent.analyze(image).to_dict()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    trace = result.get("trace", [])
    logger.info(json.dumps({
        "event": "qc_decision",
        "request_id": request_id,
        "source": source,
        "decision": result.get("status"),
        "used_enhancement": bool(result.get("used_enhancement")),
        "agent_steps": len(trace),
        "analysis_ms": round(elapsed_ms, 3),
        "opencv": cv2.__version__,
        "build_sha": os.environ.get("LABSIGHT_BUILD_SHA", "unknown"),
    }, separators=(",", ":")))
    emit_qc_metrics(
        decision=str(result.get("status")),
        source=source,
        used_enhancement=bool(result.get("used_enhancement")),
        agent_steps=len(trace),
        analysis_ms=elapsed_ms,
    )
    return result


@app.post("/analyze")
def analyze(req: AnalyzeRequest, request: Request) -> dict:
    try:
        raw = base64.b64decode(req.image_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid base64 payload") from exc
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise HTTPException(status_code=400, detail="payload is not a decodable image")
    return _analyze_image(image, request_id=request.state.request_id, source="upload")


@app.get("/demo/analyze/{scenario}")
def analyze_demo(scenario: str, request: Request) -> dict:
    params = {
        "clean": {},
        "blurred": {"blur_sigma": 5.0},
        "uneven": {"illumination_gradient": 1.0},
        "clipped": {"clip_highlights": True},
    }
    if scenario not in params:
        raise HTTPException(status_code=404, detail="unknown demo scenario")
    image = microscopy_scene(**params[scenario])
    return {"scenario": scenario, **_analyze_image(
        image,
        request_id=request.state.request_id,
        source=f"demo:{scenario}",
    )}
