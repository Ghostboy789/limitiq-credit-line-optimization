FROM python:3.15.2-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get upgrade --yes && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    pip uninstall --yes setuptools wheel && \
    addgroup --system app && adduser --system --ingroup app app

COPY limitiq ./limitiq
COPY models/behavioral_candidate.joblib models/behavioral_metadata.json \
     models/behavioral_feature_schema.json models/global_metadata.json \
     ./models/
COPY release ./release
COPY data/processed/behavioral_demo_portfolio.csv ./data/processed/behavioral_demo_portfolio.csv
COPY reports ./reports
COPY docs ./docs
COPY LICENSE README.md ./

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=3)"
CMD ["sh", "-c", "uvicorn limitiq.web:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
