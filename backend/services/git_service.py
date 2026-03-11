"""
WSDC Git Service — Sandboxed repo cloning and diff extraction.

Security hardening:
- OWASP A10 (SSRF): Clone URL allowlisted to github.com only
- OWASP A03 (Injection): All subprocess args passed as lists (no shell=True)
- Temp directory isolation with automatic cleanup
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from security import validate_repo_id, validate_git_sha

logger = logging.getLogger("wsdc.git_service")

# ── Constants ──

GITHUB_CLONE_BASE = "https://x-access-token:{token}@github.com/{repo}.git"
MAX_CLONE_DEPTH = 50
CLONE_TIMEOUT_SECONDS = 60
DIFF_TIMEOUT_SECONDS = 30


# ── Data Types ──


@dataclass
class DiffHunk:
    """A single hunk from a unified diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    """Parsed diff for a single file."""
    file_path: str
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)
    hunks: list[DiffHunk] = field(default_factory=list)


# ── Context Manager ──


@contextmanager
def sandboxed_clone(repo_full_name: str, token: str):
    """
    Clone a repo into an isolated temp directory and clean up on exit.

    Usage:
        with sandboxed_clone("owner/repo", token) as repo_dir:
            # repo_dir is the path to the cloned repo
            ...
        # auto-cleaned after exiting

    Security:
        - Validates repo name format (OWASP A10)
        - Only clones from github.com (OWASP A10)
        - Shallow clone to limit disk usage
        - Temp dir deleted on exit
    """
    if not validate_repo_id(repo_full_name):
        raise ValueError(f"Invalid repo name format: {repo_full_name!r}")

    if not token:
        raise ValueError("Installation token is required for cloning")

    tmp_dir = tempfile.mkdtemp(prefix="wsdc_clone_")
    clone_url = GITHUB_CLONE_BASE.format(token=token, repo=repo_full_name)

    try:
        logger.info("Cloning %s (depth=%d) into %s", repo_full_name, MAX_CLONE_DEPTH, tmp_dir)

        result = subprocess.run(
            [
                "git", "clone",
                "--depth", str(MAX_CLONE_DEPTH),
                "--single-branch",
                clone_url,
                tmp_dir,
            ],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
            # OWASP A03: Never use shell=True with user-controlled input
            shell=False,
            # Don't inherit env that might have credentials
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": os.environ.get("HOME", "/tmp"),
                "GIT_TERMINAL_PROMPT": "0",  # Never prompt for credentials
            },
        )

        if result.returncode != 0:
            # Sanitize error message — don't leak the token
            error_msg = result.stderr.replace(token, "[REDACTED]") if result.stderr else "Unknown error"
            raise RuntimeError(f"Git clone failed: {error_msg}")

        logger.info("Clone completed for %s", repo_full_name)
        yield tmp_dir

    finally:
        # Always clean up
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.info("Cleaned up clone directory: %s", tmp_dir)


# ── Git Operations ──


def fetch_base_sha(repo_dir: str, base_sha: str) -> None:
    """
    Fetch the base SHA so we can diff against it.
    Needed because shallow clones may not include the base commit.
    """
    if not validate_git_sha(base_sha):
        raise ValueError(f"Invalid base SHA: {base_sha!r}")

    result = subprocess.run(
        ["git", "fetch", "origin", base_sha, "--depth", str(MAX_CLONE_DEPTH)],
        capture_output=True,
        text=True,
        timeout=CLONE_TIMEOUT_SECONDS,
        cwd=repo_dir,
        shell=False,
    )

    if result.returncode != 0:
        logger.warning("Could not fetch base SHA %s: %s", base_sha[:12], result.stderr)


def get_solidity_diff(repo_dir: str, base_sha: str, head_sha: str) -> str:
    """
    Generate a unified diff of Solidity files between two commits.

    Returns raw unified diff string (empty string if no .sol changes).

    Security:
        - SHAs validated before use (OWASP A03)
        - No shell=True (OWASP A03)
    """
    if not validate_git_sha(base_sha):
        raise ValueError(f"Invalid base SHA: {base_sha!r}")
    if not validate_git_sha(head_sha):
        raise ValueError(f"Invalid head SHA: {head_sha!r}")

    result = subprocess.run(
        ["git", "diff", base_sha, head_sha, "--", "*.sol"],
        capture_output=True,
        text=True,
        timeout=DIFF_TIMEOUT_SECONDS,
        cwd=repo_dir,
        shell=False,
    )

    if result.returncode != 0:
        logger.warning("Git diff failed: %s", result.stderr)
        return ""

    return result.stdout


def get_changed_files(repo_dir: str, base_sha: str, head_sha: str) -> list[str]:
    """Return list of changed .sol file paths between two commits."""
    if not validate_git_sha(base_sha) or not validate_git_sha(head_sha):
        raise ValueError("Invalid SHA format")

    result = subprocess.run(
        ["git", "diff", "--name-only", base_sha, head_sha, "--", "*.sol"],
        capture_output=True,
        text=True,
        timeout=DIFF_TIMEOUT_SECONDS,
        cwd=repo_dir,
        shell=False,
    )

    if result.returncode != 0:
        return []

    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


# ── Diff Parsing ──

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_FILE_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)")


def parse_unified_diff(raw_diff: str) -> list[FileDiff]:
    """
    Parse a unified diff into structured FileDiff objects.

    Returns a list of FileDiff with per-file added/removed line numbers and hunks.
    """
    if not raw_diff.strip():
        return []

    files: list[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None
    current_new_line = 0
    current_old_line = 0

    for line in raw_diff.split("\n"):
        # New file
        file_match = _DIFF_FILE_HEADER.match(line)
        if file_match:
            current_file = FileDiff(file_path=file_match.group(2))
            files.append(current_file)
            current_hunk = None
            continue

        # New hunk
        hunk_match = _HUNK_HEADER.match(line)
        if hunk_match and current_file is not None:
            current_hunk = DiffHunk(
                old_start=int(hunk_match.group(1)),
                old_count=int(hunk_match.group(2) or "1"),
                new_start=int(hunk_match.group(3)),
                new_count=int(hunk_match.group(4) or "1"),
            )
            current_file.hunks.append(current_hunk)
            current_old_line = current_hunk.old_start
            current_new_line = current_hunk.new_start
            continue

        if current_hunk is None or current_file is None:
            continue

        # Diff lines
        if line.startswith("+") and not line.startswith("+++"):
            current_file.added_lines.append(current_new_line)
            current_hunk.lines.append(line)
            current_new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            current_file.removed_lines.append(current_old_line)
            current_hunk.lines.append(line)
            current_old_line += 1
        elif line.startswith(" "):
            current_hunk.lines.append(line)
            current_old_line += 1
            current_new_line += 1

    return files
