FROM python:3.12-slim
WORKDIR /app
COPY requirements-competition.txt .
RUN python -m pip install --no-cache-dir -r requirements-competition.txt
COPY labsight ./labsight
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).read()"
CMD ["uvicorn", "labsight.api:app", "--host", "0.0.0.0", "--port", "8080"]
