# Digest observed and validated on 2026-09-22 (Debian 13 / Python 3.12).
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
WORKDIR /app
ARG LABSIGHT_BUILD_SHA=unknown
ENV LABSIGHT_BUILD_SHA=${LABSIGHT_BUILD_SHA} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.revision=${LABSIGHT_BUILD_SHA}
# The required non-headless OpenCV wheel links these even for CPU-only QC.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0t64 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-competition.txt .
RUN python -m pip install --no-cache-dir -r requirements-competition.txt \
    && python -m pip check
COPY labsight ./labsight
# Fail the build, not the deployed service, for missing native libraries/pins.
RUN python -c "from labsight.runtime import competition_runtime_info; r = competition_runtime_info(); print(r); assert r['opencv5_verified'], r"
USER 65532:65532
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).read()"
CMD ["uvicorn", "labsight.api:app", "--host", "0.0.0.0", "--port", "8080"]
