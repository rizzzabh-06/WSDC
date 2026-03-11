"""
WSDC Metrics Service — Feature 4.8 (Attack Surface Diffing).
Calculates semantic security metrics (external calls, public functions, assembly) from the AST.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import PullRequest

logger = logging.getLogger("wsdc.metrics_service")


def calculate_attack_surface(repo_dir: str) -> Dict[str, int]:
    """
    Parses the current repository state to extract attack surface metrics.
    Uses the Slither Python API to traverse the AST.
    """
    try:
        from slither.slither import Slither
        
        logger.info("Calculating attack surface metrics for %s", repo_dir)
        slither = Slither(repo_dir)
        
        metrics = {
            "public_functions": 0,
            "external_calls": 0,
            "assembly_blocks": 0,
        }
        
        for contract in slither.contracts:
            # Only count implemented functionality, ignore interfaces/libraries usually
            if contract.is_interface:
                continue
                
            for function in contract.functions_declared:
                if function.visibility in ["public", "external"]:
                    metrics["public_functions"] += 1
                if function.contains_assembly:
                    metrics["assembly_blocks"] += 1
                    
                # Count high-level (contract.foo()) and low-level (.call, .delegatecall) external calls
                external_calls = len(function.high_level_calls) + len(function.low_level_calls)
                metrics["external_calls"] += external_calls
                
        logger.info("Attack surface calculated: %s", metrics)
        return metrics
        
    except Exception as e:
        logger.error("Failed to calculate attack surface: %s", str(e))
        return {}


async def get_baseline_attack_surface(session: AsyncSession, repo_uuid: str, base_sha: str) -> Optional[Dict[str, int]]:
    """
    Fetches the attack surface metrics of the most recently reviewed PR for this repo
    to serve as the baseline for delta comparison.
    Ideally, this matches `base_sha`, but as a fallback, we just take the latest merged/reviewed PR.
    """
    stmt = (
        select(PullRequest)
        .where(PullRequest.repo_id == repo_uuid, PullRequest.status == "reviewed")
        .order_by(PullRequest.reviewed_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    baseline_pr = result.scalars().first()
    
    if baseline_pr and baseline_pr.attack_surface_delta:
        # We stored the *head* metrics in the previous PR's delta JSON as 'current_metrics'
        return baseline_pr.attack_surface_delta.get("current_metrics")
        
    return None


def build_delta_table(current: Dict[str, int], baseline: Optional[Dict[str, int]]) -> str:
    """
    Builds a GitHub Markdown table visualizing the shift in attack surface.
    """
    if not current:
        return ""
        
    baseline = baseline or {k: 0 for k in current.keys()}
    
    rows = []
    for metric, current_val in current.items():
        base_val = baseline.get(metric, 0)
        delta = current_val - base_val
        
        # Formatting visually
        metric_name = metric.replace("_", " ").title()
        if delta > 0:
            delta_str = f"🔴 +{delta}"
        elif delta < 0:
            delta_str = f"🟢 {delta}"
        else:
            delta_str = "⚪ 0"
            
        rows.append(f"| {metric_name} | {base_val} | {current_val} | {delta_str} |")
        
    table_header = (
        "| Metric | Baseline | Current | Delta |\n"
        "|--------|----------|---------|-------|\n"
    )
    
    return "### 📊 Attack Surface Shift\n\n" + table_header + "\n".join(rows) + "\n"
