# Deploying BryantPathfinder to a real URL

Goal: a link a Bryant student can open on their phone and get a schedule — no
clone, no localhost. The pilot runs on the **key-free MajorPicker path**, which
never sends student records anywhere, so it costs ~$0/user and sidesteps FERPA.

Two pieces: the **backend** (FastAPI, on Render) and the **frontend** (Next.js,
on Vercel).

---

## 0. Before you deploy anything (do this tonight)

1. **Rotate your API keys.** The live keys in `backend/.env` were surfaced during
   the audit. Generate new ones and delete the old:
   - Anthropic: https://console.anthropic.com/settings/keys
   - Groq: https://console.groq.com/keys
2. **Set a hard spend cap** on the Anthropic account (Billing → Limits) so a
   stranger or crawler cannot run up your card. The key-free path won't spend,
   but the cap is your safety net.

---

## 1. Backend → Render (Docker, free tier)

The repo now has a `Dockerfile` and `render.yaml` at the root.

1. Push this branch to GitHub.
2. Render dashboard → **New → Blueprint** → pick this repo. It reads `render.yaml`.
3. Fill the secrets it prompts for (marked `sync: false`):
   - `ANTHROPIC_API_KEY` — your rotated key (only needed if `LLM_PROVIDER=anthropic`)
   - `GROQ_API_KEY` — your rotated key (only needed if `LLM_PROVIDER=groq`)
   - `ALLOWED_ORIGINS` — leave blank for now; set it after step 2 to your Vercel URL
4. Deploy. When it's live you get a URL like `https://bryantpathfinder-api.onrender.com`.
   Confirm `GET /api/health` returns `{"status":"ok", ...}`.

Defaults already set in `render.yaml`:
- `PATHFINDER_SKIP_LIVE_FETCH=1` — serves the disk snapshot on boot (no dependency
  on Bryant's Banner server at cold start). Refresh seats with a scheduled
  `POST /api/refresh-sections` during registration week.
- `PATHFINDER_DISABLE_UPLOAD=1` — turns off the audit screenshot/paste endpoints
  (the FERPA-sensitive paths) so the pilot only exposes the key-free path. Flip to
  `0` later, once a data agreement + auth exist, to re-enable "AI reads your audit."

---

## 2. Frontend → Vercel

1. Vercel → **New Project** → import this repo → set **Root Directory** to `frontend`.
2. Add an environment variable:
   - `NEXT_PUBLIC_API_BASE = https://<your-render-backend-url>`
   (This is baked in at build time, so it must be set before/at build. Redeploy if
   you change it.)
3. Deploy. You get a URL like `https://bryantpathfinder.vercel.app`.
4. Go back to Render and set `ALLOWED_ORIGINS` to that exact Vercel URL, then
   redeploy the backend so CORS allows the browser calls.

---

## 3. Distribute

Make a QR code that points at the Vercel URL. That single code — on a flyer, a
slide, an advisor's door — is the whole distribution primitive for the pilot.

---

## What's deliberately deferred (say so to the provost)

- **SSO + a sanctioned Banner/Degree Works feed** — the two things only Bryant can
  grant. They let audits be fetched instead of pasted, and retire the scraper.
- **Re-enabling the upload path** — gated off until a data-processing agreement and
  authentication exist. This is the honest, IT-endorsable posture.
- **Per-term rollover + live seat refresh** — the active term is currently fixed;
  seat data refreshes only on a manual/scheduled `/api/refresh-sections` call.
