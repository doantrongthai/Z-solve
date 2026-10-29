FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt || pip install -r requirements.txt

COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY scripts/ /app/scripts/
COPY pyproject.toml .

RUN pip install --no-deps -e .

CMD ["python", "scripts/run_pipeline.py", "--split", "public_test", "--output", "/result/submission.jsonl"]

