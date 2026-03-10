"""
WSDC Celery Worker — Consumes PR review jobs from Redis queue.

Security hardening applied:
- OWASP A08: JSON-only serialization (no pickle — CVE-2020-10199 class)
- OWASP A09: Structured logging with sanitization
- OWASP A10: Input validation on task parameters (prevents SSRF)
"""

import logging

from celery import Celery
from dotenv import load_dotenv

from config import get_settings
from security import validate_repo_id, validate_git_sha, sanitize_log_message

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wsdc.worker")

settings = get_settings()

# Initialize Celery connected to the Upstash Redis instance
app = Celery(
    "wsdc_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    # OWASP A08 — JSON-only serialization; never allow pickle (deserialization attack vector)
    task_serializer="json",
    accept_content=["json"],  # Reject all non-JSON content types
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Broker connection security
    broker_use_ssl=settings.REDIS_URL.startswith("rediss://"),
    # Task execution limits (DoS protection)
    task_soft_time_limit=120,  # 2 minute soft limit
    task_time_limit=180,  # 3 minute hard kill
    # Retry limits
    task_max_retries=3,
    task_default_retry_delay=30,
    # Worker security
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (prevent memory leaks)
)


@app.task(name="wsdc.process_pr_event", bind=True, max_retries=3)
def process_pr_event(
    self, repo_id: str, pr_number: int, head_sha: str, base_sha: str
):
    """
    Background worker task triggered by the Node.js Probot App.

    All inputs are validated before any processing to prevent:
    - SSRF via crafted repo_id (OWASP A10)
    - Injection via crafted SHA values (OWASP A03)
    """
    # ── Input Validation (OWASP A03, A10) ──
    if not validate_repo_id(repo_id):
        logger.error(
            "Rejected invalid repo_id: %s",
            sanitize_log_message(str(repo_id)[:100]),
        )
        return {"status": "rejected", "reason": "invalid repo_id format"}

    if not isinstance(pr_number, int) or pr_number <= 0 or pr_number > 999999:
        logger.error("Rejected invalid pr_number: %s", pr_number)
        return {"status": "rejected", "reason": "invalid pr_number"}

    if not validate_git_sha(head_sha) or not validate_git_sha(base_sha):
        logger.error("Rejected invalid SHA values for PR #%d", pr_number)
        return {"status": "rejected", "reason": "invalid SHA format"}

    # ── Safe to proceed ──
    logger.info("Worker processing PR #%d for repo %s", pr_number, repo_id)
    logger.info("Diffing %s -> %s", base_sha[:12], head_sha[:12])

    # 1. Clone Repo & Sandbox
    # 2. AST Diff Analysis
    # 3. Static Analysis (Slither)
    # 4. AI Context
    # 5. Comment Posting

    return {"status": "success", "findings": 0}
