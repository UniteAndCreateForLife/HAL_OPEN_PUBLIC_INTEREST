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
from .synthetic import microscopy_scene
from .web import DEMO_HTML

app = FastAPI(title="HAL LabSight", version="0.2.0")
agent = LabSightAgent()
logger = logging.getLogger("labsight.api")


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded PNG/JPEG image bytes")


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    started = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.headers["x-labsight-request-id"] = request_id
    response.headers["server-timing"] = f"labsight;dur={elapsed_ms:.3f}"
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round(elapsed_ms, 3),
            },
            separators=(",", ":"),
        )
    )
    return response


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    return DEMO_HTML


@app.get("/health")
def health() -> dict[str, str | bool]:
    major = int(cv2.__version__.split(".")[0])
    return {
        "status": "ok",
        "service": "hal-labsight",
        "version": "0.2.0",
        "build_sha": os.environ.get("LABSIGHT_BUILD_SHA", "unknown"),
        "opencv": cv2.__version__,
        "numpy": np.__version__,
        "opencv5_verified": major >= 5,
    }


def _analyze_image(image: np.ndarray) -> dict:
    return agent.analyze(image).to_dict()


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    try:
        raw = base64.b64decode(req.image_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid base64 payload") from exc
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise HTTPException(status_code=400, detail="payload is not a decodable image")
    return _analyze_image(image)


@app.get("/demo/analyze/{scenario}")
def analyze_demo(scenario: str) -> dict:
    params = {
        "clean": {},
        "blurred": {"blur_sigma": 5.0},
        "uneven": {"illumination_gradient": 1.0},
        "clipped": {"clip_highlights": True},
    }
    if scenario not in params:
        raise HTTPException(status_code=404, detail="unknown demo scenario")
    image = microscopy_scene(**params[scenario])
    return {"scenario": scenario, **_analyze_image(image)}
