"""SiteSage backend — chat with any website, powered by NVIDIA Nemotron on Nebius Token Factory."""
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager

import httpx
import trafilatura
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------- config ---
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.environ.get(
    "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1"
).rstrip("/")
# NVIDIA open-source models served on Nebius Token Factory.
FAST_MODEL = os.environ.get("FAST_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
DEEP_MODEL = os.environ.get("DEEP_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")
DB_PATH = os.environ.get("SITESAGE_DB", os.path.join(os.path.dirname(__file__), "sitesage.db"))
FETCH_TIMEOUT = 25
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
TOP_K = 5

# ------------------------------------------------------------------- db ---
def init_db() -> None:
    with db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS sessions(
                 id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT,
                 created_at REAL NOT NULL)"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS chunks(
                 session_id TEXT NOT NULL, idx INTEGER NOT NULL,
                 text TEXT NOT NULL,
                 PRIMARY KEY(session_id, idx))"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS messages(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 session_id TEXT NOT NULL, role TEXT NOT NULL,
                 content TEXT NOT NULL, model TEXT, created_at REAL NOT NULL)"""
        )

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()

# --------------------------------------------------------------- llm ------
def chat_completion(messages, model, max_tokens=1024, temperature=0.3):
    """Runtime call to NVIDIA Nemotron via Nebius Token Factory (OpenAI-compatible)."""
    if not NEBIUS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="NEBIUS_API_KEY is not configured on the server.",
        )
    try:
        resp = httpx.post(
            f"{NEBIUS_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {NEBIUS_API_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=90,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Token Factory request failed: {exc}")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Token Factory error {resp.status_code}: {resp.text[:300]}",
        )
    return resp.json()["choices"][0]["message"]["content"].strip()

# ------------------------------------------------------------ ingest ------
def fetch_page(url: str):
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        # fallback: plain httpx fetch
        try:
            r = httpx.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True,
                          headers={"User-Agent": "SiteSage/1.0 (hackathon demo)"})
            r.raise_for_status()
            downloaded = r.text
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Could not fetch URL: {exc}")
    text = trafilatura.extract(downloaded, include_comments=False) or ""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 200:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from this URL (need at least 200 chars).",
        )
    title_match = re.search(r"<title[^>]*>(.*?)</title>", downloaded, re.I | re.S)
    title = (title_match.group(1).strip()[:120] if title_match else url)
    title = re.sub(r"\s+", " ", title)
    return title, text

def chunk_text(text: str):
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        # try to break on paragraph boundary
        if end < n:
            brk = text.rfind("\n\n", start, end)
            if brk > start + CHUNK_SIZE // 2:
                end = brk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - CHUNK_OVERLAP
    return chunks

def rank_chunks(query: str, chunks):
    """Simple token-overlap ranking (fast, no extra deps)."""
    qtokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for i, ch in enumerate(chunks):
        ctokens = set(re.findall(r"[a-z0-9]+", ch.lower()))
        overlap = len(qtokens & ctokens)
        # small bonus for earlier chunks (usually intro / key content)
        score = overlap - i * 0.01
        scored.append((score, i))
    scored.sort(reverse=True)
    return [i for _, i in scored[:TOP_K] if _ > 0] or [s[1] for s in scored[:TOP_K]]

def build_context(session_id: str, idxs):
    with db() as con:
        rows = con.execute(
            "SELECT idx, text FROM chunks WHERE session_id=? ORDER BY idx",
            (session_id,),
        ).fetchall()
    by_idx = {i: t for i, t in rows}
    parts = []
    for n, i in enumerate(idxs, 1):
        if i in by_idx:
            parts.append(f"[{n}] {by_idx[i]}")
    return "\n\n".join(parts)

# ---------------------------------------------------------------- app -----
app = FastAPI(title="SiteSage")

class IngestReq(BaseModel):
    url: str = Field(..., max_length=2000)

class ChatReq(BaseModel):
    session_id: str
    question: str = Field(..., max_length=2000)
    mode: str = Field("auto", pattern="^(auto|fast|deep)$")

class SessionOut(BaseModel):
    id: str
    url: str
    title: str

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "llm_configured": bool(NEBIUS_API_KEY),
        "fast_model": FAST_MODEL,
        "deep_model": DEEP_MODEL,
    }

@app.post("/api/ingest")
def ingest(req: IngestReq):
    url = req.url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    title, text = fetch_page(url)
    chunks = chunk_text(text)
    sid = uuid.uuid4().hex[:12]
    with db() as con:
        con.execute(
            "INSERT INTO sessions(id, url, title, created_at) VALUES(?,?,?,?)",
            (sid, url, title, time.time()),
        )
        con.executemany(
            "INSERT INTO chunks(session_id, idx, text) VALUES(?,?,?)",
            [(sid, i, c) for i, c in enumerate(chunks)],
        )
    # suggested questions via the fast Nemotron model (cheap)
    suggested = []
    try:
        out = chat_completion(
            [
                {"role": "system", "content": "You suggest questions."},
                {
                    "role": "user",
                    "content": (
                        "This is the start of a web page titled '%s':\n\n%s\n\n"
                        "Suggest 3 short, specific questions a reader would ask about this page. "
                        "Reply with one question per line, no numbering, no extra text."
                        % (title, text[:1500])
                    ),
                },
            ],
            model=FAST_MODEL,
            max_tokens=150,
        )
        suggested = [l.strip("- •\t ") for l in out.splitlines() if l.strip()][:3]
    except HTTPException:
        pass
    # TL;DR via the fast model
    summary = ""
    try:
        summary = chat_completion(
            [
                {"role": "system", "content": "You write concise summaries."},
                {
                    "role": "user",
                    "content": f"Summarize this web page in 3 sentences or fewer:\n\n{text[:4000]}",
                },
            ],
            model=FAST_MODEL,
            max_tokens=200,
        )
    except HTTPException:
        pass
    return {
        "session_id": sid,
        "url": url,
        "title": title,
        "chunks": len(chunks),
        "chars": len(text),
        "summary": summary,
        "suggested": suggested,
    }

@app.post("/api/chat")
def chat(req: ChatReq):
    with db() as con:
        row = con.execute(
            "SELECT url, title FROM sessions WHERE id=?", (req.session_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Unknown session.")
        chunks = [r[0] for r in con.execute(
            "SELECT text FROM chunks WHERE session_id=? ORDER BY idx", (req.session_id,)
        )]
        history = con.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 6",
            (req.session_id,),
        ).fetchall()
    idxs = rank_chunks(req.question, chunks)
    context = build_context(req.session_id, idxs)
    # model routing: "deep" for long/complex questions, fast otherwise
    mode = req.mode
    if mode == "auto":
        mode = "deep" if len(req.question.split()) > 12 or "?" in req.question and len(req.question) > 120 else "fast"
    model = DEEP_MODEL if mode == "deep" else FAST_MODEL
    hist_text = "\n".join(f"{r}: {c[:300]}" for r, c in reversed(history))
    answer = chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are SiteSage, a precise assistant that answers questions about a web page. "
                    "Use ONLY the page excerpts below. Cite sources with [1], [2] etc. matching the excerpt numbers. "
                    "If the excerpts don't contain the answer, say so briefly instead of guessing."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Page excerpts:\n{context}\n\n"
                    f"Recent conversation:\n{hist_text}\n\n"
                    f"Question: {req.question}\nAnswer concisely with citations."
                ),
            },
        ],
        model=model,
        max_tokens=800,
    )
    with db() as con:
        con.execute(
            "INSERT INTO messages(session_id, role, content, model, created_at) VALUES(?,?,?,?,?)",
            (req.session_id, "user", req.question, None, time.time()),
        )
        con.execute(
            "INSERT INTO messages(session_id, role, content, model, created_at) VALUES(?,?,?,?,?)",
            (req.session_id, "assistant", answer, model, time.time()),
        )
    return {"answer": answer, "model": model, "mode": mode, "sources": [i + 1 for i in range(len(idxs))]}

@app.get("/api/sessions")
def list_sessions():
    with db() as con:
        rows = con.execute(
            "SELECT id, url, title FROM sessions ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return [{"id": r[0], "url": r[1], "title": r[2]} for r in rows]

@app.delete("/api/sessions/{sid}")
def delete_session(sid: str):
    with db() as con:
        con.execute("DELETE FROM messages WHERE session_id=?", (sid,))
        con.execute("DELETE FROM chunks WHERE session_id=?", (sid,))
        con.execute("DELETE FROM sessions WHERE id=?", (sid,))
    return {"ok": True}

# serve the single-page frontend (index.html at /, plus style.css / app.js)
FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
