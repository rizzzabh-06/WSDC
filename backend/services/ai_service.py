"""
WSDC AI Context Layer — OpenAI integration for tiered PR comments.

Security Context:
- Uses OpenAI API with structured JSON output parsing.
- Does not expose secret API keys anywhere.
"""

import json
import logging
from typing import Optional, Dict, Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from config import get_settings
from services.git_service import FileDiff
from services.slither_service import FindingDetail

logger = logging.getLogger("wsdc.ai_service")


# ── Structured Output Models ──

class TieredExplanation(BaseModel):
    """The structured 3-level comment format expected by the frontend."""
    summary: str = Field(description="Level 1: One-line summary of the vulnerability")
    context: str = Field(description="Level 2: Protocol-specific explanation and exploit scenario")
    fix: str = Field(description="Level 3: Full code fix options with tradeoffs")
    owasp_mapping: list[str] = Field(description="List of OWASP/ASVS categories (e.g. ['A01', 'SC-05'])")


# ── Prompts ──

SYSTEM_PROMPT = """
You are WSDC, an expert Web3 Security Development Co-Pilot. 
You are analyzing a static analysis finding (from Slither) on a newly submitted Pull Request.

Your goal is to explain this finding in the context of the code changes, providing:
1. A clear, dense 1-line summary.
2. An exploit scenario contextualized to the provided code snippet.
3. Concrete fix recommendations (code if possible) and tradeoffs.
4. The relevant OWASP Smart Contract Top 10 category.

Return ONLY a valid JSON object matching this schema:
{
  "summary": "string",
  "context": "string",
  "fix": "string",
  "owasp_mapping": ["string"]
}

Be educational, precise, and avoid generic boilerplate.
"""


# ── Service Actions ──

async def generate_tiered_explanation(
    finding: FindingDetail, 
    file_diff: FileDiff,
    repo_name: str
) -> Optional[Dict[str, Any]]:
    """
    Generate a 3-tier explanation using OpenAI.
    Extracts the relevant hunk from the FileDiff to append to the prompt.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — falling back to basic explanation")
        return None

    # Find the relevant code snippet
    code_context = ""
    for hunk in file_diff.hunks:
        if hunk.new_start - 2 <= finding.line_number <= hunk.new_start + hunk.new_count + 2:
            code_context = "\n".join(hunk.lines)
            break
            
    if not code_context:
        code_context = "// Code snippet not available in immediate diff context."

    prompt = f"""
Repository: {repo_name}
Vulnerability Category: {finding.category}
Severity: {finding.severity}
File: {file_diff.file_path}:{finding.line_number}
Slither Generic Description: {finding.description}

### Recent Code Changes (Git Diff Hunk)
```diff
{code_context}
```

Generate the tiered explanation JSON.
"""

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
    
    try:
        logger.info("Generating AI explanation for %s on %s...", finding.category, file_diff.file_path)
        
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",  # standardizing on modern fast gpt-4
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800,
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
            
        parsed = json.loads(content)
        # Validate structure via Pydantic
        explanation = TieredExplanation(**parsed)
        
        return explanation.model_dump()
        
    except Exception as e:
        logger.error("AI explanation generation failed: %s", str(e))
        return None


def format_inline_comment(finding: FindingDetail, ai_explanation: Optional[Dict[str, Any]]) -> str:
    """
    Format the multi-level inline PR comment for GitHub.
    """
    severity_badges = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "informational": "⚪",
    }
    badge = severity_badges.get(finding.severity, "⚪")
    
    if not ai_explanation:
        # Fallback if AI fails or is disabled
        return (
            f"### {badge} {finding.title}\n\n"
            f"**Generic description:** {finding.description}\n\n"
            "*AI explanation unavailable or disabled.*"
        )
        
    summary = ai_explanation["summary"]
    context = ai_explanation["context"]
    fix = ai_explanation["fix"]
    owasp = ", ".join(ai_explanation["owasp_mapping"])
    
    # 3-level collapsible structure (PRD 4.5)
    return f"""### {badge} {finding.title}
**{summary}**

<details open>
<summary><b>Context & Exploit Scenario</b></summary>

{context}
</details>

<details>
<summary><b>Fix & Tradeoffs</b></summary>

{fix}

*Tags: {owasp}*
</details>"""
