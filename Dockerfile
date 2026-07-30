# Backend container for BryantPathfinder (FastAPI).
# Build context is the repo root so both backend/ and data/ are available at the
# relative layout the app expects (data dir resolves to <app-parent>/data).
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY data ./data

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
# Serve the on-disk section snapshot on boot instead of scraping Bryant's live
# Banner server on every cold start. Refresh seats via POST /api/refresh-sections
# (e.g. a scheduled job) during the registration window.
ENV PATHFINDER_SKIP_LIVE_FETCH=1

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
