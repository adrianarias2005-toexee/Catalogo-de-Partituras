#!/bin/bash
cd "$(dirname "$0")"
source .env 2>/dev/null || true
python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
