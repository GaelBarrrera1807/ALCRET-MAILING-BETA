FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip==25.1 \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]