# WSDC Tasks - Phase 1 (Foundation - Serverless)

## 1. Project Management
- [x] Create `.env.example` with placeholders for remote managed services.
- [x] Write a `README.md` guide on setting up Neon (Postgres), Upstash (Redis), and Smee (Webhooks).

## 2. GitHub App (Node.js/Probot)
- [x] Initialize `github-app` directory with `create-probot-app`.
- [x] Implement Redis queue producer (via Remote Upstash Redis) in `index.js` for PR events.
- [x] Forward `installation_id` in job data for worker → GitHub API auth.

## 3. Backend Architecture (Python/FastAPI)
- [x] Initialize `backend` directory with `venv` and `requirements.txt`.
- [x] Create FastAPI `main.py` entrypoint.
- [x] Create Celery `worker.py` to consume Redis queue tasks from the remote Upstash URL.
- [x] Write SQLAlchemy models for `repositories` and `pull_requests` mapping to the PRD schema.
- [x] Add `Finding`, `ProtocolModel`, `SecurityHistory` models (complete PRD schema).
- [x] Set up Alembic for async database migrations.

## 4. Services Layer
- [x] Create `services/git_service.py` — sandboxed repo cloning, SHA-validated diff generation, unified diff parser.
- [x] Create `services/github_client.py` — JWT-based GitHub App auth, installation token caching, PR comment posting, comment formatting.

## 5. Review Pipeline (worker.py)
- [x] Wire full pipeline: clone → diff → stub analysis → comment → return results.
- [x] Graceful degradation when GitHub credentials not configured (dev mode).

## 6. Local Integration & Testing
- [x] Create a `Makefile` or helper scripts to streamline starting the local Python/Node servers without Docker.
- [ ] Test the pipeline end-to-end against the remote services (requires GitHub App + Neon + Upstash credentials).

## 7. Security Hardening (OWASP Top 10 & CVE Compliance)
- [x] Create `config.py` — Pydantic settings with fail-fast validation, TLS enforcement (A02, A05)
- [x] Create `security.py` — API key auth, HMAC webhook validation, security headers, log sanitization, input validators (A01-A10)
- [x] Harden all backend files (main.py, database.py, worker.py, models.py)
- [x] Harden all GitHub App files (index.js, app.yml, Dockerfile, package.json)
- [x] Pin all dependency versions (A06)
