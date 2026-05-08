"""
Test Suite — PDC Assignment
Student: Muhammad Usman Gillani | bsai23062

Covers:
  - X-Student-ID header presence on every response (mandatory one-line check)
  - Circuit Breaker: CLOSED → OPEN transition (first 5 fail normally, 6th fallback instantly)
  - Optimistic Locking: conflict detection (409) and happy path
  - Idempotent Webhook: duplicate suppression
"""

import pytest
import time
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport, ConnectError
from main import app, llm_breaker, documents_db, processed_webhooks, users_db


@pytest.fixture(autouse=True)
def reset_state():
    """Reset all shared state before every test."""
    llm_breaker._reset()
    documents_db.clear()
    documents_db[1] = {"id": 1, "title": "Lecture Notes", "content": "Original content.", "version": 1}
    processed_webhooks.clear()
    users_db.clear()
    users_db["user_001"] = {"user_id": "user_001", "is_premium": True}
    users_db["user_002"] = {"user_id": "user_002", "is_premium": True}
    yield


import pytest_asyncio

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ══════════════════════════════════════════════
# MANDATORY: X-Student-ID header check
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_student_id_header_on_every_response(client):
    """Asserts that X-Student-ID: bsai23062 is present on multiple responses."""
    responses = [
        await client.get("/"),
        await client.get("/circuit-status"),
        await client.get("/documents/1"),
        await client.get("/users/user_001"),
    ]
    for response in responses:
        # Mandatory one-line check for header presence
        assert response.headers.get("X-Student-ID") == "bsai23062", "CRITICAL: Student ID header missing!"


# ══════════════════════════════════════════════
# PROBLEM 3: Circuit Breaker Tests
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_circuit_breaker_six_requests_flow(client):
    """
    Step 5 Test Requirement:
    - Patches the LLM HTTP call to always raise a ConnectionError (or ConnectError).
    - Fires 6 sequential requests to /ask-llm.
    - Asserts first 5 return errors normally (502) but take some time / fail.
    - Asserts 6th returns the fallback response (503) almost instantly because the breaker is OPEN.
    - Includes a one-line check that the X-Student-ID header is present on every response.
    """
    # 1. Patch the raw LLM call to always raise a ConnectError
    with patch("main._call_llm", side_effect=ConnectError("Mock LLM is dead")):
        
        # Fire first 3 requests
        for i in range(1, 4):
            start_time = time.monotonic()
            response = await client.post("/ask-llm", json={"prompt": f"Test {i}", "timeout": 2.0})
            elapsed = time.monotonic() - start_time
            
            # Assert they return errors normally (502 status code as configured in main.py)
            assert response.status_code == 502
            assert response.json()["failures_so_far"] == i
            # Check X-Student-ID header on every response (mandatory one-line check)
            assert response.headers.get("X-Student-ID") == "bsai23062"

        # Circuit should now be OPEN
        assert llm_breaker.state.value == "OPEN"

        # Fire requests 4, 5, 6
        for i in range(4, 7):
            start_time = time.monotonic()
            response = await client.post("/ask-llm", json={"prompt": f"Test {i}", "timeout": 2.0})
            elapsed = time.monotonic() - start_time

            # Assert they return fallback response instantly (503 status code)
            assert response.status_code == 503
            assert response.json()["source"] == "fallback"
            assert response.json()["circuit_state"] == "OPEN"
            assert elapsed < 0.1, f"Request {i} was not instant, took {elapsed:.4f}s"
            # Check X-Student-ID header on the response
            assert response.headers.get("X-Student-ID") == "bsai23062"


@pytest.mark.asyncio
async def test_circuit_reset_and_status(client):
    """Verifies circuit status and manual reset endpoint work correctly."""
    response = await client.get("/circuit-status")
    assert response.status_code == 200
    assert response.json()["state"] == "CLOSED"


# ══════════════════════════════════════════════
# PROBLEM 1: Optimistic Locking Tests
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_document_optimistic_locking(client):
    """
    Simulates concurrent editing (optimistic locking):
    - User A reads doc version 1.
    - User B reads doc version 1.
    - User A writes successfully, bumping version to 2.
    - User B tries to write using stale version 1 -> gets 409 conflict.
    """
    # Happy path update (User A)
    resp_a = await client.put(
        "/documents/1",
        json={"content": "Content edited by User A", "version": 1}
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["document"]["version"] == 2

    # Conflicting update (User B with stale version)
    resp_b = await client.put(
        "/documents/1",
        json={"content": "Content edited by User B", "version": 1}
    )
    assert resp_b.status_code == 409
    assert "Version conflict" in resp_b.json()["detail"]


# ══════════════════════════════════════════════
# PROBLEM 2: Idempotent Webhook Tests
# ══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_webhook_idempotency_checks(client):
    """Verifies that duplicate webhook deliveries are safely ignored."""
    payload = {
        "event_id": "evt_test_idempotency_123",
        "event_type": "subscription.cancelled",
        "user_id": "user_001"
    }

    # 1st delivery -> processed
    resp_1 = await client.post("/webhooks/clerk", json=payload)
    assert resp_1.status_code == 200
    assert resp_1.json()["status"] == "processed"
    assert users_db["user_001"]["is_premium"] is False

    # Simulate reversing premium status manually to check if 2nd delivery is ignored
    users_db["user_001"]["is_premium"] = True

    # 2nd delivery (duplicate) -> ignored
    resp_2 = await client.post("/webhooks/clerk", json=payload)
    assert resp_2.status_code == 200
    assert resp_2.json()["status"] == "already_processed"
    assert users_db["user_001"]["is_premium"] is True  # Unchanged!
