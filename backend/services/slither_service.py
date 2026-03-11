"""
WSDC Slither Service — Static analysis execution and diff filtering.

Security Context:
- OWASP A03 (Injection): No shell=True, arguments passed safely to subprocess
- OWASP A08 (Data Integrity): Validates JSON structure of Slither output
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, Any

from config import get_settings
from services.git_service import FileDiff

logger = logging.getLogger("wsdc.slither_service")

# ── Data Types ──

@dataclass
class FindingDetail:
    """A detected vulnerability, ready to map to DB Finding."""
    title: str
    description: str
    category: str
    severity: str
    file_path: str
    line_number: Optional[int]
    status: str = "open"


# ── Execution ──

def run_slither_on_repo(repo_dir: str) -> str:
    """
    Run Slither static analysis on the local repo directory and return JSON.
    Uses SLITHER_CMD from config.
    """
    settings = get_settings()
    # Slither standard usage: `slither <target> --json <output>`
    # Instead of writing to a file, we output to stdout with `-` and capture it
    cmd = [settings.SLITHER_CMD, ".", "--json", "-"]
    
    logger.info("Running Slither analysis in %s", repo_dir)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,  # 3 minutes max
        cwd=repo_dir,
        shell=False,
    )
    
    # Slither often returns non-zero if issues are found, so we don't strict-fail on code.
    # But if standard output is empty, there was an execution failure.
    if not result.stdout.strip():
        logger.warning("Slither execution failed or returned no output: %s", result.stderr)
        return ""
        
    return result.stdout


# ── Parsing & Filtering ──

def parse_slither_json(json_output: str) -> list[FindingDetail]:
    """
    Parse raw Slither --json output into FindingDetail objects.
    """
    if not json_output:
        return []
        
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Slither output as JSON: %s", str(e))
        return []

    # Valid Slither JSON has a 'results' -> 'detectors' array
    detectors = data.get("results", {}).get("detectors", [])
    if not detectors:
        return []
        
    findings = []
    
    for det in detectors:
        check_name = det.get("check", "Unknown")
        impact = det.get("impact", "Informational")  # High, Medium, Low, Informational
        severity_map = {
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Informational": "informational"
        }
        severity = severity_map.get(impact, "informational")
        
        description = det.get("description", "")
        # The primary elements involved
        elements = det.get("elements", [])
        
        # We need a primary file and line to attach the comment to
        file_path = "unknown"
        line_number = None
        
        # Pick the first relevant source code element
        for el in elements:
            if "source_mapping" in el:
                sm = el["source_mapping"]
                lines = sm.get("lines", [])
                filename = sm.get("filename_relative") or sm.get("filename_absolute")
                
                if filename and lines:
                    file_path = filename
                    line_number = lines[0]  # Just take the first line
                    break
                    
        # Skip findings without a concrete file attached, or we map them to "unknown"
        if file_path == "unknown":
            continue
            
        findings.append(FindingDetail(
            title=check_name,
            description=description,
            category=check_name,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
        ))
        
    return findings


def filter_findings_by_diff(
    findings: list[FindingDetail], 
    file_diffs: list[FileDiff]
) -> list[FindingDetail]:
    """
    Filter findings to only include those intersecting with changed lines.
    
    A finding is kept if its file_path is modified AND its line_number is within
    any added or modified hunk of the unified diff.
    """
    # Create lookup map for diffs: {"contracts/Vault.sol": [Hunk, Hunk]}
    diff_map = {fd.file_path: fd for fd in file_diffs}
    
    filtered = []
    
    for f in findings:
        # Check if the file was modified at all
        if f.file_path not in diff_map:
            continue
            
        fd = diff_map[f.file_path]
        
        # Check if the finding's line number intersects with an added/modified line
        # We look at the added_lines (which contains newly inserted lines + modified lines)
        if f.line_number in fd.added_lines:
            filtered.append(f)
            continue
            
        # Also check hunks for broader context. Sometimes Slither flags a function signature
        # line while the actual change was inside the function body.
        # We'll allow a small buffer window (e.g. +/- 2 lines from a hunk bounds).
        added = False
        for hunk in fd.hunks:
            if hunk.new_start - 2 <= f.line_number <= hunk.new_start + hunk.new_count + 2:
                filtered.append(f)
                added = True
                break
                
        if not added:
            # Drop finding — it's in a changed file but not in a changed area
            pass
            
    return filtered
