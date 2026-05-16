# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY main.py dashboard.py vNews_logo.ico start.sh ./
COPY .streamlit/ .streamlit/

RUN sed -i 's/\r//' start.sh && chmod +x start.sh && mkdir -p /app/data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["./start.sh"]
