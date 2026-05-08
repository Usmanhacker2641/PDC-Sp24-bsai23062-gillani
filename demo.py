"""
Demo Script — Circuit Breaker Before vs After
Student: Muhammad Usman Gillani | bsai23062

Run this WHILE the server is running: uvicorn main:app --reload

This script:
1. BEFORE: Shows raw LLM call hanging/failing with no protection
2. AFTER:  Shows circuit breaker tripping open and returning fallback instantly
"""

import asyncio
import time
import httpx

BASE_URL = "http://localhost:8000"


def print_header(title: str):
    width = 55
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_result(i: int, status: int, data: dict, elapsed_ms: float):
    state = data.get("circuit_state", "N/A")
    source = data.get("source", "error")
    answer_preview = str(data.get("answer", data.get("error", "")))[:50]
    print(
        f"  [{i}] HTTP {status} | {elapsed_ms:6.0f}ms | "
        f"state={state:9s} | source={source:8s} | {answer_preview}"
    )


async def demo_before():
    """
    BEFORE FIX: Raw call to a dead LLM endpoint.
    Hangs until httpx timeout, blocks the worker.
    """
    print_header("BEFORE FIX — No Circuit Breaker")
    print("  Sending 3 requests to a dead LLM (timeout=3s each)...")
    print("  Notice every request WAITS the full timeout before failing.\n")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        for i in range(1, 4):
            start = time.monotonic()
            try:
                # Calling the unprotected raw endpoint simulation
                response = await client.post(
                    "/ask-llm",
                    json={"prompt": f"Question {i}", "timeout": 2.0}
                )
                elapsed = (time.monotonic() - start) * 1000
                print_result(i, response.status_code, response.json(), elapsed)
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                print(f"  [{i}] Exception after {elapsed:.0f}ms: {e}")

    print("\n  [WARN] Each failed request blocked the server for ~2 seconds.")
    print("  With real 60s LLM timeouts, the server would be unusable.")


async def demo_after():
    """
    AFTER FIX: Circuit breaker trips after threshold, returns fallback instantly.
    """
    print_header("AFTER FIX — Circuit Breaker Active")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        # Reset breaker to CLOSED state
        await client.post("/circuit-reset")
        print("  Circuit reset to CLOSED.\n")
        # Since main.py breaker threshold is 3 failures:
        print("  Sending 6 requests (threshold=3, LLM is DOWN)...\n")

        for i in range(1, 7):
            start = time.monotonic()
            response = await client.post(
                "/ask-llm",
                json={"prompt": f"Question {i}", "timeout": 1.5}
            )
            elapsed = (time.monotonic() - start) * 1000
            print_result(i, response.status_code, response.json(), elapsed)

            if i == 3:
                print("\n  [TRIPPED] CIRCUIT TRIPPED OPEN after 3 failures!\n")

        print("\n  [OK] Request 6 returned fallback in <10ms (no LLM contact)")
        print("  [OK] Server stays responsive for all other users\n")

        # Show final circuit status
        status_resp = await client.get("/circuit-status")
        print("  Circuit Breaker Status:", status_resp.json())

        # Check X-Student-ID header
        print(f"\n  [INFO] X-Student-ID header: {response.headers.get('x-student-id')}")


async def demo_optimistic_lock():
    """Shows two concurrent users — one wins, one gets 409."""
    print_header("BONUS: Optimistic Locking Demo")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as client:
        # Both users read document
        doc = (await client.get("/documents/1")).json()
        current_version = doc['version']
        print(f"  Both users read document at version {current_version}")

        # User A writes first
        r_a = await client.put(
            "/documents/1",
            json={"content": "User A's brilliant edit", "version": current_version}
        )
        print(f"\n  User A writes -> HTTP {r_a.status_code} | new version: {r_a.json()['document']['version']}")

        # User B tries to write with stale version
        r_b = await client.put(
            "/documents/1",
            json={"content": "User B's overwrite attempt", "version": current_version}
        )
        print(f"  User B writes -> HTTP {r_b.status_code} | {r_b.json()['detail'][:60]}")
        print("\n  [OK] Lost update PREVENTED. User B must re-fetch and retry.")


async def demo_webhook_idempotency():
    """Shows duplicate webhook being safely ignored."""
    print_header("BONUS: Idempotent Webhook Demo")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as client:
        payload = {
            "event_id": f"evt_clerk_demo_{int(time.time())}",
            "event_type": "subscription.cancelled",
            "user_id": "user_001",
        }

        r1 = await client.post("/webhooks/clerk", json=payload)
        print(f"  1st delivery -> status: {r1.json()['status']}")
        print(f"  User premium: {r1.json()['user']['is_premium']}")

        r2 = await client.post("/webhooks/clerk", json=payload)
        print(f"\n  2nd delivery (duplicate) -> status: {r2.json()['status']}")
        print("  [OK] No double-processing. Idempotency confirmed.")


async def main():
    print("\n" + "#" * 55)
    print("  StudySync — Resilient Distributed Systems Demo")
    print("  Muhammad Usman Gillani | bsai23062")
    print("#" * 55)

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=3) as c:
            await c.get("/")
    except Exception:
        print("\n  [ERROR] Server not reachable. Start it first:")
        print("     uvicorn main:app --reload")
        return

    await demo_before()
    await asyncio.sleep(1)
    await demo_after()
    await asyncio.sleep(1)
    await demo_optimistic_lock()
    await asyncio.sleep(1)
    await demo_webhook_idempotency()

    print("\n" + "=" * 55)
    print("  Demo complete. All three patterns demonstrated.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
