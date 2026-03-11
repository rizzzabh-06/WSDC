"""
WSDC History Service — Feature 4.7 (Security History & Regression Tracking).
Tracks finding categories across PRs and identifies if a "fixed" issue reappears.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from models import SecurityHistory, Finding, PullRequest

logger = logging.getLogger("wsdc.history_service")


async def update_security_history(
    session: AsyncSession, 
    repo_uuid: str, 
    pr_uuid: str, 
    findings: List[Dict[str, Any]]
):
    """
    Upserts the security history table counts for each finding category found in this PR.
    """
    # Track unique categories in this PR run
    categories_seen = {f.get("category") for f in findings if f.get("category")}
    
    for category in categories_seen:
        stmt = select(SecurityHistory).where(
            SecurityHistory.repo_id == repo_uuid,
            SecurityHistory.category == category
        )
        result = await session.execute(stmt)
        history = result.scalars().first()
        
        if history:
            history.occurrences += 1
            history.last_seen_pr_id = pr_uuid
            history.last_seen_at = func.now()
            logger.debug("Incremented history for %s (now %d)", category, history.occurrences)
        else:
            new_history = SecurityHistory(
                repo_id=repo_uuid,
                category=category,
                occurrences=1,
                last_seen_pr_id=pr_uuid,
            )
            session.add(new_history)
            logger.debug("Created initial history for %s", category)
            
    await session.commit()
    logger.info("Updated security history for PR %s", pr_uuid)


async def detect_regressions(
    session: AsyncSession, 
    repo_uuid: str, 
    current_findings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Checks if a finding's category/file pair was previously marked 'fixed' in this repo.
    Mutates the current_findings dicts to include `is_regression: bool`.
    """
    if not current_findings:
        return current_findings
        
    for f in current_findings:
        category = f.get("category")
        file_path = f.get("file_path")
        
        f["is_regression"] = False
        
        if not category or not file_path:
            continue
            
        # Check if there is any 'fixed' finding in the same repo, same file, same category
        stmt = (
            select(Finding)
            .join(Finding.pull_request)
            .where(
                PullRequest.repo_id == repo_uuid,
                Finding.category == category,
                Finding.file_path == file_path,
                Finding.status == "fixed"
            )
            .limit(1)
        )
        
        result = await session.execute(stmt)
        past_fixed_finding = result.scalars().first()
        
        if past_fixed_finding:
            f["is_regression"] = True
            f["regression_note"] = f"⚠️ REGRESSION: This {category} issue was previously marked fixed in PR #{past_fixed_finding.pull_request.pr_number}."
            logger.warning("Detected regression for %s in %s", category, file_path)
            
    return current_findings
