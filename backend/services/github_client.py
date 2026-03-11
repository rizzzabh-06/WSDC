"""
WSDC GitHub Client — Async GitHub API for posting PR comments.

Security hardening:
- OWASP A02: JWT signed with App private key, tokens never logged
- OWASP A09: Safe logging — no tokens or keys in output
- OWASP A10: HTTPS only for GitHub API calls
"""

import logging
import time
from typing import Optional

import httpx
import jwt

logger = logging.getLogger("wsdc.github_client")

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubClient:
    """
    Async GitHub API client for WSDC.

    Uses GitHub App JWT authentication → installation access tokens
    to post PR comments and review comments.
    """

    def __init__(self, app_id: str, private_key: str):
        """
        Args:
            app_id: GitHub App ID
            private_key: PEM-encoded private key for JWT signing
        """
        if not app_id or not private_key:
            raise ValueError("GitHub App ID and private key are required")

        self._app_id = app_id
        self._private_key = private_key
        self._token_cache: dict[int, tuple[str, float]] = {}  # installation_id -> (token, expiry)

    # ── JWT & Token Management (OWASP A02) ──

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication (valid 10 minutes)."""
        now = int(time.time())
        payload = {
            "iat": now - 60,       # Issued 60s ago to account for clock drift
            "exp": now + (10 * 60),  # Expires in 10 minutes
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def _get_installation_token(self, installation_id: int) -> str:
        """
        Get or refresh an installation access token.
        Caches tokens until 5 minutes before expiry.
        """
        # Check cache
        if installation_id in self._token_cache:
            token, expiry = self._token_cache[installation_id]
            if time.time() < expiry - 300:  # 5 minute buffer
                return token

        # Request new token
        app_jwt = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": GITHUB_API_VERSION,
                },
                timeout=10.0,
            )
            resp.raise_for_status()

        data = resp.json()
        token = data["token"]
        # GitHub installation tokens expire in 1 hour
        expiry = time.time() + 3600

        self._token_cache[installation_id] = (token, expiry)
        logger.info("Obtained installation token for installation %d", installation_id)

        return token

    def _auth_headers(self, token: str) -> dict[str, str]:
        """Standard GitHub API headers with bearer token."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    # ── PR Comments ──

    async def post_pr_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> Optional[int]:
        """
        Post a top-level comment on a PR (issue comment).

        Returns the comment ID on success, None on failure.
        """
        token = await self._get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self._auth_headers(token),
                json={"body": body},
                timeout=10.0,
            )

        if resp.status_code == 201:
            comment_id = resp.json().get("id")
            logger.info(
                "Posted PR comment on %s/%s#%d (comment_id=%s)",
                owner, repo, pr_number, comment_id,
            )
            return comment_id
        else:
            logger.error(
                "Failed to post PR comment on %s/%s#%d: %d %s",
                owner, repo, pr_number, resp.status_code, resp.text[:200],
            )
            return None

    async def post_review_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        file_path: str,
        line: int,
        body: str,
        side: str = "RIGHT",
    ) -> Optional[int]:
        """
        Post an inline review comment on a specific line in a PR diff.

        Args:
            side: "LEFT" for removed lines, "RIGHT" for added lines

        Returns the comment ID on success, None on failure.
        """
        token = await self._get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                headers=self._auth_headers(token),
                json={
                    "body": body,
                    "commit_id": commit_sha,
                    "path": file_path,
                    "line": line,
                    "side": side,
                },
                timeout=10.0,
            )

        if resp.status_code == 201:
            comment_id = resp.json().get("id")
            logger.info(
                "Posted inline comment on %s/%s#%d %s:%d",
                owner, repo, pr_number, file_path, line,
            )
            return comment_id
        else:
            logger.error(
                "Failed to post inline comment on %s/%s#%d: %d %s",
                owner, repo, pr_number, resp.status_code, resp.text[:200],
            )
            return None

    async def update_pr_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        comment_id: int,
        body: str,
    ) -> bool:
        """Update an existing PR comment."""
        token = await self._get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/comments/{comment_id}",
                headers=self._auth_headers(token),
                json={"body": body},
                timeout=10.0,
            )

        if resp.status_code == 200:
            logger.info("Updated comment %d on %s/%s", comment_id, owner, repo)
            return True
        else:
            logger.error(
                "Failed to update comment %d: %d %s",
                comment_id, resp.status_code, resp.text[:200],
            )
            return False


# ── Comment Formatting ──


def format_summary_comment(
    repo_full_name: str,
    pr_number: int,
    sol_files_changed: int,
    findings_count: int,
    findings_by_severity: dict[str, int],
) -> str:
    """
    Format the PR summary comment posted after a review.
    Uses GitHub Markdown with collapsible details.
    """
    severity_badges = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "informational": "⚪",
    }

    if findings_count == 0:
        return (
            "## 🛡️ WSDC Security Review Complete\n\n"
            f"**{sol_files_changed} Solidity file(s)** analyzed — **no security issues found**.\n\n"
            "✅ All clear! This PR looks safe from a security perspective.\n\n"
            "---\n"
            "*Powered by [WSDC](https://github.com/wsdc) — Web3 Security Development Co-Pilot*"
        )

    # Build severity breakdown
    severity_lines = []
    for sev in ("critical", "high", "medium", "low", "informational"):
        count = findings_by_severity.get(sev, 0)
        if count > 0:
            badge = severity_badges.get(sev, "⚪")
            severity_lines.append(f"| {badge} **{sev.capitalize()}** | {count} |")

    severity_table = "| Severity | Count |\n|----------|-------|\n" + "\n".join(severity_lines)

    return (
        "## 🛡️ WSDC Security Review Complete\n\n"
        f"**{sol_files_changed} Solidity file(s)** analyzed — "
        f"**{findings_count} issue(s)** found.\n\n"
        f"{severity_table}\n\n"
        "<details>\n<summary>📋 What to do next</summary>\n\n"
        "- Review each inline comment below\n"
        "- Fix critical/high issues before merging\n"
        "- Use `/wsdc accept-risk` to acknowledge accepted risks\n"
        "- Use `/wsdc explain` for deeper context on any finding\n\n"
        "</details>\n\n"
        "---\n"
        "*Powered by [WSDC](https://github.com/wsdc) — Web3 Security Development Co-Pilot*"
    )
