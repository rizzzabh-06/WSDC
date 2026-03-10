# WSDC Tasks - Phase 1 (Foundation - Serverless)

## 1. Project Management
- [x] Create `.env.example` with placeholders for remote managed services.
- [x] Write a `README.md` guide on setting up Neon (Postgres), Upstash (Redis), and Smee (Webhooks).

## 2. GitHub App (Node.js/Probot)
- [x] Initialize `github-app` directory with `create-probot-app`.
- [x] Implement Redis queue producer (via Remote Upstash Redis) in `index.js` for PR events.

## 3. Backend Architecture (Python/FastAPI)
- [x] Initialize `backend` directory with `venv` and `requirements.txt`.
- [x] Create FastAPI `main.py` entrypoint.
- [x] Create Celery `worker.py` to consume Redis queue tasks from the remote Upstash URL.
- [x] Write SQLAlchemy models for `repositories` and `pull_requests` mapping to the PRD schema, pointing to the remote Neon DB.

## 4. Local Integration & Testing
- [x] Create a `Makefile` or helper scripts to streamline starting the local Python/Node servers without Docker.
- [ ] Test the pipeline end-to-end against the remote services.

## 5. Security Hardening (OWASP Top 10 & CVE Compliance)
- [x] Create `config.py` — Pydantic settings with fail-fast validation, TLS enforcement (A02, A05)
- [x] Create `security.py` — API key auth, HMAC webhook validation, security headers, log sanitization, input validators (A01, A02, A03, A04, A09, A10)
- [x] Harden `main.py` — Auth middleware, rate limiting, CORS, request ID tracing, strict input validation (A01, A03, A04, A05, A07, A09)
- [x] Harden `database.py` — Remove insecure fallback, connection pool limits, disable echo in production (A02, A03, A05)
- [x] Harden `worker.py` — Input validation, JSON-only serialization, task timeouts (A08, A09, A10)
- [x] Harden `models.py` — CheckConstraint on status, safe `__repr__`, string length limits (A01, A03)
- [x] Pin all dependency versions in `requirements.txt` and `package.json` (A06)
- [x] Fix `app.yml` — Enable `pull_request` events, add `pull_requests: write` + `contents: read` permissions (A01)
- [x] Harden `index.js` — Input validation, error handling, safe logging (A03, A04, A09, A10)
- [x] Harden `Dockerfile` — Non-root user, healthcheck (A05, CVE-2019-5736)
- [x] Update `.env.example` with `WSDC_API_KEY`, `ENVIRONMENT`, `CORS_ORIGINS` (A05)
