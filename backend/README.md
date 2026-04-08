# BryantPathfinder Backend

FastAPI backend for BryantPathfinder. Serves the constraint solver, Claude Vision audit parsing, and schedule generation API.

## Quick Start (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add your Anthropic API key
uvicorn app.main:app --reload --port 8000
```

## Quick Start (bash / macOS / Linux)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Anthropic API key
uvicorn app.main:app --reload --port 8000
```

## Verify

Open http://localhost:8000/api/health in a browser. You should see:

```json
{"status": "ok", "sections_loaded": 291, "term": "Fall 2026", "anthropic_api": "reachable"}
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status and section count |
| POST | `/api/parse-audit` | Parse a Degree Works screenshot via Claude Vision |
| POST | `/api/generate-schedules` | Generate 3 ranked, conflict-free schedules |
| GET | `/api/sample-audit` | Return Owen's pre-parsed audit fixture (demo fallback) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude Vision and schedule explanations |
