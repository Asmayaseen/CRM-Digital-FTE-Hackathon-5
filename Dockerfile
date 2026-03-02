FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY production/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# HuggingFace Spaces uses port 7860; fallback to 8000 locally
EXPOSE 7860
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
