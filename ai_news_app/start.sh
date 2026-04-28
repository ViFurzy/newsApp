#!/bin/bash
set -e

echo "[start] Launching aggregator daemon..."
python main.py &
MAIN_PID=$!

echo "[start] Launching Streamlit dashboard..."
streamlit run dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0

# Streamlit exited — clean up background process
kill "$MAIN_PID" 2>/dev/null || true
wait "$MAIN_PID" 2>/dev/null || true
