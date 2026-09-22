from __future__ import annotations

import base64

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agent import LabSightAgent

app = FastAPI(title="HAL LabSight", version="0.1.0")
agent = LabSightAgent()


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded PNG/JPEG image bytes")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hal-labsight", "opencv": cv2.__version__}


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
    return agent.analyze(image).to_dict()
