FROM python:3.12-slim
WORKDIR /app
COPY requirements-competition.txt .
RUN pip install --no-cache-dir -r requirements-competition.txt
COPY labsight ./labsight
EXPOSE 8080
CMD ["uvicorn", "labsight.api:app", "--host", "0.0.0.0", "--port", "8080"]
