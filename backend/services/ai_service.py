"""
WSDC AI Context Layer — OpenAI integration for tiered PR comments.

Security Context:
- Uses OpenAI API with structured JSON output parsing.
- Does not expose secret API keys anywhere.
"""

import json
import logging
from typing import Optional, Dict, Any

from google import genai
from google.genai import types
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
3. Concrete fix recommendations and tradeoffs. If the fix requires modifying the code, you MUST format the code replacement using a GitHub Markdown Suggestion block exactly like this:
```suggestion
// your corrected lines of code
```
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
    finding: dict, 
    file_diff: FileDiff,
    repo_name: str,
    protocol_context: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Generate a 3-tier explanation using Gemini.
    Extracts the relevant hunk from the FileDiff to append to the prompt.
    """
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — falling back to basic explanation")
        return None

    # Find the relevant code snippet
    code_context = ""
    for hunk in file_diff.hunks:
        if hunk.new_start - 2 <= finding.get("line_number") <= hunk.new_start + hunk.new_count + 2:
            code_context = "\n".join(hunk.lines)
            break
            
    if not code_context:
        code_context = "// Code snippet not available in immediate diff context."

    prompt = f"""
Repository: {repo_name}
Protocol Context: {protocol_context}

Vulnerability Category: {finding.get('category')}
Severity: {finding.get('severity')}
File: {file_diff.file_path}:{finding.get('line_number')}
Slither Generic Description: {finding.get('description')}

Regression Warning: {finding.get('regression_note')}

### Recent Code Changes (Git Diff Hunk)
```diff
{code_context}
```

Please generate the explanation matching the required JSON schema.
"""

    # Note: Using sync client wrapped in async here as google-genai async support relies on asyncio
    # For a high throughput production app, you might want to fully manage the async client loop.
    client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())
    
    try:
        logger.info("Generating AI explanation for %s on %s...", finding.category, file_diff.file_path)
        
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=TieredExplanation,
                temperature=0.2,
            ),
        )
        
        content = response.text
        if not content:
            return None
            
        parsed = json.loads(content)
        # Validate structure via Pydantic
        explanation = TieredExplanation(**parsed)
        
        return explanation.model_dump()
        
    except Exception as e:
        logger.error("AI explanation generation failed: %s", str(e))
        return None


def format_inline_comment(finding: dict, ai_explanation: Optional[Dict[str, Any]]) -> str:
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
    badge = severity_badges.get(finding.get("severity"), "⚪")
    
    regression_banner = f"\n> [!CAUTION]\n> **{finding.get('regression_note')}**\n\n" if finding.get("is_regression") else ""
    
    if not ai_explanation:
        # Fallback if AI fails or is disabled
        return (
            f"### {badge} {finding.get('title')}\n\n"
            f"{regression_banner}"
            f"**Generic description:** {finding.get('description')}\n\n"
            "*AI explanation unavailable or disabled.*"
        )
        
    summary = ai_explanation["summary"]
    context = ai_explanation["context"]
    fix = ai_explanation["fix"]
    owasp = ", ".join(ai_explanation["owasp_mapping"])
    
    # 3-level collapsible structure (PRD 4.5) + Interactive fixes
    return f"""### {badge} {finding.get('title')}
{regression_banner}**{summary}**

<details open>
<summary><b>Context & Exploit Scenario</b></summary>

{context}
</details>

<details>
<summary><b>Fix & Tradeoffs</b></summary>

{fix}

*Tags: {owasp}*
</details>"""
