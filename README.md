# SiteSage — Chat with any website

Paste a URL, ask anything. SiteSage fetches the page, extracts the readable
content, and lets you chat with it — answers come with citations, powered by
**NVIDIA Nemotron** models served on **Nebius Token Factory**.

Built for the **Nebius x NVIDIA Global AI Hackathon** (Best Apps and Agents track).

## How it works

1. **Ingest** — paste any URL. The backend fetches the page and extracts clean
   article text with `trafilatura`, then chunks it for retrieval.
2. **Summarize** — NVIDIA Nemotron 3 Nano (fast tier) writes a 3-sentence TL;DR
   and suggests follow-up questions.
3. **Chat** — ask anything. Relevant chunks are retrieved with a lightweight
   ranker and passed to Nemotron, which answers *only* from the page and cites
   sources as `[1]`, `[2]`, …
4. **Model routing** — short factual questions go to the fast model
   (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`); long/complex questions are routed
   to the deep reasoning model. You can also force Fast / Deep manually.

Every answer is a **runtime call to the Nebius Token Factory inference API**
(OpenAI-compatible `POST /v1/chat/completions`) using NVIDIA open-source models —
no model is hosted by us.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export NEBIUS_API_KEY="tf-..."   # create one in the Token Factory console
# optional overrides:
# export DEEP_MODEL="nvidia/<deep-model-id>"
# export NEBIUS_BASE_URL="https://api.tokenfactory.nebius.com/v1"
uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/ — no login needed.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `NEBIUS_API_KEY` | — | **Required.** Token Factory API key |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1` | Inference endpoint |
| `FAST_MODEL` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Fast answers, summaries |
| `DEEP_MODEL` | `nvidia/Nemotron-3-Ultra-550b-a55b` | Deep reasoning answers |
| `SITESAGE_DB` | `backend/sitesage.db` | SQLite history file |

## Project layout

```
nebius-hackathon/
├── backend/app.py        # FastAPI: ingest, chat, model routing, SQLite history
├── frontend/             # single-page UI (no build step)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── deploy/sitesage.service  # systemd unit for the demo server
├── requirements.txt
└── README.md
```

## API

- `GET /api/health` — status + whether the LLM key is configured
- `POST /api/ingest` `{url}` — fetch + chunk a page, returns summary & questions
- `POST /api/chat` `{session_id, question, mode: auto|fast|deep}` — cited answer
- `GET /api/sessions` / `DELETE /api/sessions/{id}` — history management

## NVIDIA & Nebius usage

- **NVIDIA**: all language understanding is done by NVIDIA Nemotron open-source
  models (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, deep tier configurable).
- **Nebius Token Factory**: every model call is a runtime request to the Token
  Factory OpenAI-compatible inference API — this is what the app "runs on".
  Token Factory is also why the app needs zero GPU of its own.

## License

MIT — see [LICENSE](LICENSE).
