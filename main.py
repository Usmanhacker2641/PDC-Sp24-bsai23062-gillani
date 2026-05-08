"""
StudySync Backend - FastAPI Application
Student: Muhammad Usman Gillani | bsai23062

Implements:
  - Circuit Breaker for LLM API calls (Problem 3: Fault Tolerance)
  - X-Student-ID middleware header on every response
  - Optimistic Locking for concurrent document edits (Problem 1: Sync)
  - Idempotent Webhook handler (Problem 2: Coordination)
"""

import os
import time
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from circuit_breaker import CircuitBreaker, CircuitOpenError

# Manual .env loader to avoid external dependencies
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ──────────────────────────────────────────────
# In-memory "database" (simulates SQLite/Postgres)
# ──────────────────────────────────────────────
documents_db: dict[int, dict] = {
    1: {"id": 1, "title": "Lecture Notes", "content": "Original content.", "version": 1},
}

processed_webhooks: set[str] = set()   # idempotency store


# ──────────────────────────────────────────────
# Circuit Breaker instance (shared across requests)
# ──────────────────────────────────────────────
llm_breaker = CircuitBreaker(
    failure_threshold=5,     # trip after 5 failures
    cooldown_seconds=30.0,   # reopen after 30 seconds (standard cooldown)
    success_threshold=1,
)

# Mock LLM URL — replace with real endpoint if needed
LLM_API_URL = "http://localhost:9999/generate"   # intentionally unreachable for demo


# ──────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("StudySync backend starting up...")
    yield
    print("StudySync backend shutting down.")


app = FastAPI(
    title="StudySync API",
    description="Resilient distributed backend — PDC Assignment",
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# MANDATORY MIDDLEWARE — X-Student-ID header
# ──────────────────────────────────────────────
@app.middleware("http")
async def add_student_id_header(request: Request, call_next):
    """
    Injects X-Student-ID: bsai23062 into EVERY response.
    Required by assignment — missing this = zero for Part 3.
    """
    response = await call_next(request)
    response.headers["X-Student-ID"] = "bsai23062"
    return response


# ──────────────────────────────────────────────
# Root
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "StudySync API is running",
        "student": "Muhammad Usman Gillani",
        "id": "bsai23062",
    }


# ══════════════════════════════════════════════
# PROBLEM 3 — FAULT TOLERANCE (Circuit Breaker)
# ══════════════════════════════════════════════

class LLMRequest(BaseModel):
    prompt: str
    timeout: float = 5.0   # seconds before we consider LLM hung


async def _call_llm(prompt: str, timeout: float) -> dict:
    """Raw LLM call. Call real Gemini API if key is present and not a demo question, otherwise hit unreachable mock URL."""
    # For demo simulations (using prompt starting with 'Question'), we bypass real Gemini to force a failure and show the circuit tripping.
    if GEMINI_API_KEY and not prompt.strip().startswith("Question"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            res_json = response.json()
            # Extract content text from Gemini payload structure
            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return {"text": text}
    else:
        # Fallback to unreachable URL (causes timeout/refusal for breaker demos)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                LLM_API_URL,
                json={"prompt": prompt},
            )
            response.raise_for_status()
            return response.json()


FALLBACK_RESPONSE = {
    "answer": "AI suggestions are temporarily unavailable. Please try again later.",
    "source": "fallback",
    "circuit_state": "OPEN",
}


@app.post("/ask-llm")
async def ask_llm(body: LLMRequest):
    """
    Protected LLM endpoint.
    - Circuit CLOSED  → calls LLM normally
    - Circuit OPEN    → returns fallback immediately (no hanging)
    - Circuit HALF_OPEN → sends one trial call
    """
    try:
        result = await llm_breaker.call(_call_llm, body.prompt, body.timeout)
        return {
            "answer": result.get("text", ""),
            "source": "llm",
            "circuit_state": llm_breaker.state.value,
        }

    except CircuitOpenError as e:
        # Breaker is OPEN → return fallback, do NOT wait for LLM
        return JSONResponse(
            status_code=503,
            content={**FALLBACK_RESPONSE, "detail": str(e)},
        )

    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        # LLM call failed — breaker has already recorded this failure
        return JSONResponse(
            status_code=502,
            content={
                "answer": "LLM call failed.",
                "error": str(e),
                "circuit_state": llm_breaker.state.value,
                "failures_so_far": llm_breaker.failure_count,
            },
        )


@app.get("/circuit-status")
async def circuit_status():
    """Inspect current circuit breaker state — useful for demo."""
    return llm_breaker.get_status()


@app.post("/circuit-reset")
async def circuit_reset():
    """Manually reset circuit breaker and databases — useful for demo."""
    llm_breaker._reset()
    # Reset simulated databases back to clean startup state
    documents_db[1] = {"id": 1, "title": "Lecture Notes", "content": "Original content.", "version": 1}
    if "user_001" in users_db:
        users_db["user_001"]["is_premium"] = True
    processed_webhooks.clear()
    return {
        "message": "Circuit breaker and databases reset to initial states",
        "state": llm_breaker.state.value
    }


# ══════════════════════════════════════════════
# PROBLEM 1 — SYNCHRONIZATION (Optimistic Locking)
# ══════════════════════════════════════════════

class DocumentUpdate(BaseModel):
    content: str
    version: int   # client must send the version it last read


@app.get("/documents/{doc_id}")
async def get_document(doc_id: int):
    doc = documents_db.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.put("/documents/{doc_id}")
async def update_document(doc_id: int, body: DocumentUpdate):
    """
    Optimistic Locking: update only if version matches.
    Returns 409 Conflict if another user already updated the doc.
    """
    doc = documents_db.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # ← This is the atomic check that prevents the Lost Update anomaly
    if doc["version"] != body.version:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Version conflict: expected version {body.version}, "
                f"but current version is {doc['version']}. "
                "Re-fetch the document and retry."
            ),
        )

    # Safe to update — no concurrent modification detected
    doc["content"] = body.content
    doc["version"] += 1
    documents_db[doc_id] = doc

    return {"message": "Document updated", "document": doc}


# ══════════════════════════════════════════════
# PROBLEM 2 — COORDINATION (Idempotent Webhook)
# ══════════════════════════════════════════════

class WebhookPayload(BaseModel):
    event_id: str          # Clerk's unique event identifier
    event_type: str        # e.g. "subscription.cancelled"
    user_id: str
    data: Optional[dict] = None


# Simulated users table
users_db: dict[str, dict] = {
    "user_001": {"user_id": "user_001", "is_premium": True},
    "user_002": {"user_id": "user_002", "is_premium": True},
}


@app.post("/webhooks/clerk")
async def clerk_webhook(payload: WebhookPayload):
    """
    Idempotent webhook handler.
    Uses event_id as idempotency key — safe to call multiple times.
    """
    # ← Idempotency check: have we already processed this event?
    if payload.event_id in processed_webhooks:
        return {
            "status": "already_processed",
            "event_id": payload.event_id,
            "message": "Duplicate webhook ignored (idempotent).",
        }

    if payload.event_type == "subscription.cancelled":
        user = users_db.get(payload.user_id)
        if user:
            user["is_premium"] = False
            users_db[payload.user_id] = user

    # Mark event as processed (in production: inside a DB transaction)
    processed_webhooks.add(payload.event_id)

    return {
        "status": "processed",
        "event_id": payload.event_id,
        "event_type": payload.event_type,
        "user": users_db.get(payload.user_id),
    }


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
