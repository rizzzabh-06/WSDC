"""
WSDC Celery Worker — PR review pipeline orchestrator.

Pipeline: clone → Diff → Slither → AI Enhancement → Comment → Persist.

Security hardening:
- OWASP A08: JSON-only serialization
- OWASP A09: Structured logging
- OWASP A10: Input validation
"""

import asyncio
import logging

from celery import Celery
from dotenv import load_dotenv

from config import get_settings
from security import validate_repo_id, validate_git_sha, sanitize_log_message
from services.slither_service import FindingDetail

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wsdc.worker")

settings = get_settings()

app = Celery(
    "wsdc_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl={"ssl_cert_reqs": "none"} if settings.REDIS_URL.startswith("rediss://") else False,
    redis_backend_use_ssl={"ssl_cert_reqs": "none"} if settings.REDIS_URL.startswith("rediss://") else False,
    task_soft_time_limit=300,  # 5 minutes (Slither + LLM can take time)
    task_time_limit=360,
    task_max_retries=3,
    task_default_retry_delay=30,
)


def _run_async(coro):
    """Run an async coroutine from synchronous Celery context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Pipeline Steps ──

def _step_clone_and_diff(repo_full_name: str, head_sha: str, base_sha: str, token: str):
    from services.git_service import sandboxed_clone, fetch_base_sha, get_changed_files, get_solidity_diff, parse_unified_diff

    # We return the tmp_dir context manager so the caller can keep it open for Slither
    # instead of closing it immediately.
    ctx = sandboxed_clone(repo_full_name, token)
    repo_dir = ctx.__enter__()
    
    try:
        fetch_base_sha(repo_dir, base_sha)
        changed_files = get_changed_files(repo_dir, base_sha, head_sha)
        
        if not changed_files:
            return ctx, repo_dir, [], []
            
        raw_diff = get_solidity_diff(repo_dir, base_sha, head_sha)
        file_diffs = parse_unified_diff(raw_diff)
        
        return ctx, repo_dir, changed_files, file_diffs
    except Exception:
        ctx.__exit__(None, None, None)
        raise


def _step_slither_analysis(repo_dir: str, file_diffs: list) -> list[FindingDetail]:
    from services.slither_service import run_slither_on_repo, parse_slither_json, filter_findings_by_diff
    
    raw_json = run_slither_on_repo(repo_dir)
    all_findings = parse_slither_json(raw_json)
    
    logger.info("Slither found %d total issues before filtering", len(all_findings))
    
    filtered = filter_findings_by_diff(all_findings, file_diffs)
    logger.info("Retained %d findings after diff filtering", len(filtered))
    
    return filtered


async def _step_ai_enhancement(findings: list[FindingDetail], file_diffs: list, repo_name: str) -> list[dict]:
    """Enhance findings concurrently using OpenAI."""
    from services.ai_service import generate_tiered_explanation, format_inline_comment
    
    diff_map = {fd.file_path: fd for fd in file_diffs}
    tasks = []
    
    # Fire off all LLM requests concurrently
    for f in findings:
        fd = diff_map.get(f.file_path)
        if fd:
            tasks.append(generate_tiered_explanation(f, fd, repo_name))
        else:
            # Fallback if somehow there's no diff context
            tasks.append(asyncio.sleep(0, result=None))
            
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    enhanced = []
    for f, ai_res in zip(findings, results):
        if isinstance(ai_res, Exception):
            logger.error("AI generation failed for %s: %s", f.title, ai_res)
            ai_res = None
            
        comment_body = format_inline_comment(f, ai_res)
        
        enhanced.append({
            "category": f.category,
            "severity": f.severity,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "title": f.title,
            "description": f.description,
            "comment_body": comment_body,     # Stored for GitHub posting
            "ai_data": ai_res                 # Stored for DB persistence
        })
        
    return enhanced


async def _step_post_comments(
    installation_id: int,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    changed_files: list,
    enhanced_findings: list[dict],
):
    from services.github_client import GitHubClient, format_summary_comment

    if not settings.APP_ID or not settings.PRIVATE_KEY:
        return []

    client = GitHubClient(app_id=settings.APP_ID, private_key=settings.PRIVATE_KEY)
    posted_comments = []

    # 1. Post inline comments for each finding
    for f in enhanced_findings:
        if not f["line_number"]:
            continue
            
        comment_id = await client.post_review_comment(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_sha=head_sha,
            file_path=f["file_path"],
            line=f["line_number"],
            body=f["comment_body"]
        )
        if comment_id:
            posted_comments.append(comment_id)
            f["github_comment_id"] = comment_id  # Attach to save to DB

    # 2. Post PR Summary
    severity_counts = {}
    for f in enhanced_findings:
        sev = f.get("severity", "informational")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    summary_body = format_summary_comment(
        repo_full_name=f"{owner}/{repo}",
        pr_number=pr_number,
        sol_files_changed=len(changed_files),
        findings_count=len(enhanced_findings),
        findings_by_severity=severity_counts,
    )

    await client.post_pr_comment(
        installation_id=installation_id,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        body=summary_body,
    )
    
    return posted_comments


async def _step_persist_results(repo_id: str, pr_number: int, head_sha: str, base_sha: str, findings: list[dict]):
    """Save PR and findings to PostgreSQL."""
    # Note: Full asyncpg persistence will be added here.
    # We are deferring the full sqlalchemy session logic to verify the pipeline core first, 
    # but the stubs and models are ready.
    logger.info("Persisting %d findings to database for PR #%d", len(findings), pr_number)


# ── Main Task ──

@app.task(name="wsdc.process_pr_event", bind=True, max_retries=3)
def process_pr_event(
    self,
    repo_id: str,
    pr_number: int,
    head_sha: str,
    base_sha: str,
    installation_id: int = 0,
):
    if not validate_repo_id(repo_id) or not validate_git_sha(head_sha):
        return {"status": "rejected"}

    parts = repo_id.split("/", 1)
    owner, repo = parts

    logger.info("Review pipeline started for %s PR #%d", repo_id, pr_number)

    try:
        # Clone (Context holds dir open for Slither)
        if settings.APP_ID and settings.PRIVATE_KEY and installation_id:
            from services.github_client import GitHubClient
            gh_client = GitHubClient(app_id=settings.APP_ID, private_key=settings.PRIVATE_KEY)
            clone_token = _run_async(gh_client._get_installation_token(installation_id))
            ctx, repo_dir, changed_files, file_diffs = _step_clone_and_diff(repo_id, head_sha, base_sha, clone_token)
        else:
            logger.warning("No GitHub credentials — aborting pipeline")
            return {"status": "aborted"}

        try:
            if not changed_files:
                logger.info("No Solidity changes — pipeline complete")
                return {"status": "success", "findings": 0}

            # Analysis
            raw_findings = _step_slither_analysis(repo_dir, file_diffs)
            
        finally:
            # Clean up clone immediately after analysis
            ctx.__exit__(None, None, None)

        # AI Enhancement
        enhanced_findings = _run_async(_step_ai_enhancement(raw_findings, file_diffs, repo_id))
        
        # Post Comments
        _run_async(_step_post_comments(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            changed_files=changed_files,
            enhanced_findings=enhanced_findings
        ))
        
        # Persist
        _run_async(_step_persist_results(repo_id, pr_number, head_sha, base_sha, enhanced_findings))

    except Exception as e:
        logger.error("Pipeline failed: %s", sanitize_log_message(str(e)))
        raise self.retry(exc=e, countdown=30)

    return {
        "status": "success",
        "repo_id": repo_id,
        "pr_number": pr_number,
        "findings_count": len(enhanced_findings)
    }
