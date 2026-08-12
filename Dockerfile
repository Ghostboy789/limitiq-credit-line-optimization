FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    addgroup --system app && adduser --system --ingroup app app

COPY limitiq ./limitiq
COPY models ./models
COPY data/processed/global_demo_portfolio.csv ./data/processed/global_demo_portfolio.csv
COPY reports ./reports
COPY docs ./docs
COPY LICENSE README.md ./

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=3)"
CMD ["sh", "-c", "uvicorn limitiq.web:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
