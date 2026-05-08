Muhammad Usman Gillani | bsai23062

# PDC-Sp24-bsai23062-Gillani
### Building Resilient Distributed Systems — PDC Assignment

**Course:** Parallel and Distributed Computing (PDC)  
**Student:** Muhammad Usman Gillani  
**ID:** bsai23062  

---

## What This Implements

This repo contains a minimal FastAPI backend that solves all three distributed systems problems from the StudySync scenario:

| Problem | Pattern | File |
|---|---|---|
| Lost Update (Sync) | Optimistic Locking (version column) | `app/main.py` |
| Dropped Webhook (Coordination) | Idempotent Handler + event_id dedup | `app/main.py` |
| LLM Hanging (Fault Tolerance) | Circuit Breaker with Fallback | `app/circuit_breaker.py` |

Every response includes the mandatory `X-Student-ID: bsai23062` header via FastAPI middleware.

---

## Setup & Run

### 1. Clone and install dependencies

```bash
git clone https://github.com/<your-username>/PDC-Sp24-bsai23062-Gillani.git
cd PDC-Sp24-bsai23062-Gillani

pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

---

## Run Tests

```bash
pytest test_circuit_breaker.py -v
```

Expected output: all tests pass, including the mandatory header check.

---

## Run Demo Script

With the server running in one terminal, open a second terminal and run:

```bash
python demo.py
```

This demonstrates:
- **BEFORE**: LLM calls hanging on each failure
- **AFTER**: Circuit breaker trips open, fallback returned in <10ms
- **Bonus**: Optimistic lock 409 conflict and idempotent webhook

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/ask-llm` | LLM call (circuit breaker protected) |
| GET | `/circuit-status` | Inspect breaker state |
| POST | `/circuit-reset` | Reset breaker to CLOSED |
| GET | `/documents/{id}` | Get document |
| PUT | `/documents/{id}` | Update document (optimistic lock) |
| POST | `/webhooks/clerk` | Receive Clerk webhook (idempotent) |
| GET | `/users/{id}` | Get user |

---

## Project Structure

```
PDC-Sp24-bsai23062-Gillani/
├── main.py            ← FastAPI app + all 3 problem solutions
├── circuit_breaker.py ← Circuit Breaker class
├── test_circuit_breaker.py ← Full test suite
├── demo.py            ← Before/after demo script
├── requirements.txt
└── README.md
```
