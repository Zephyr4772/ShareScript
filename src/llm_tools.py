import os
import json
from litellm import completion


def _get_model() -> str:
    """Model for text generation (README, roadmap, slides)."""
    return os.environ.get("LLM_MODEL", "ollama/qwen3-next:80b-cloud")


def _get_json_model() -> str:
    """
    Model for structured JSON output (analysis, social posts).
    Defaults to gemma4:31b-cloud — qwen3-next cloud returns empty content for JSON calls.
    Override with JSON_MODEL env var.
    """
    return os.environ.get("JSON_MODEL", "ollama/gemma4:31b-cloud")



import re as _re


def _strip_and_extract_json(text: str) -> str:
    """
    Multi-strategy JSON extractor for thinking models (qwen3, deepseek-r1, etc.).
    Handles <think> blocks, markdown fences, and extracts first valid JSON object/array.
    """
    if not text:
        return ""
    # 1. Strip <think>...</think> blocks
    text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL).strip()
    # 2. Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # 3. If it still doesn't start with { or [, try to find the first JSON object via regex
    if text and text[0] not in ('{', '['):
        match = _re.search(r'(\{.*\}|\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(0)
    return text.strip()


def _call_llm(messages: list, model: str = None, max_tokens: int = 8000) -> str:
    """
    Call LiteLLM and return the text content.
    Handles thinking models where content may be in reasoning_content.
    """
    model = model or _get_model()
    response = completion(model=model, messages=messages, max_tokens=max_tokens)
    msg = response.choices[0].message
    content = msg.content or ""
    # Some thinking model integrations put real output in reasoning_content
    if not content.strip() and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
        content = msg.reasoning_content or ""
    return content




def _ext_summary(ext_counts: dict) -> str:
    """Produce a human-readable extension breakdown."""
    total = sum(ext_counts.values()) or 1
    parts = [f"{ext}: {round(cnt/total*100)}%" for ext, cnt in list(ext_counts.items())[:8]]
    return ", ".join(parts)


def summarize_context_for_llm(context: dict, enriched_analysis: dict = None) -> str:
    """Produces a rich but token-efficient summary for LLM prompts."""
    topics = context.get("topics", [])
    if not isinstance(topics, list):
        topics = list(topics)

    frameworks = context.get("detected_frameworks", [])
    deps = context.get("all_dependencies", [])
    ext_summary = _ext_summary(context.get("file_extension_counts", {}))

    summary = f"""
Project: {context.get("name", "Unknown")}
Description: {context.get("description", "No description provided.")}
Primary Language: {context.get("language", "Unknown")}
Stars: {context.get("stars", 0)} | Forks: {context.get("forks", 0)}
Topics: {", ".join(topics) if topics else "none"}
Deployment URL: {context.get("deployment_url", "Not found")}

Detected Frameworks: {", ".join(frameworks) if frameworks else "none detected"}
Key Dependencies: {", ".join(deps[:30]) if deps else "none"}
File Extension Breakdown: {ext_summary if ext_summary else "unknown"}

README (first 2000 chars):
{context.get("readme", "")[:2000]}

Key Source Files:"""

    for path, content in list(context.get("key_files", {}).items())[:5]:
        summary += f"\n\n--- {path} ---\n{content[:800]}"

    if enriched_analysis:
        summary += f"\n\n--- Enriched Analysis ---\n{json.dumps(enriched_analysis, indent=2)[:1000]}"

    return summary


def analyze_codebase(context: dict) -> dict:
    """
    Deep analysis: what the project does, who it's for, key features, real tech stack.
    Returns structured JSON.
    """
    model = _get_json_model()
    summary = summarize_context_for_llm(context)

    prompt = f"""You are a senior software engineer analyzing a GitHub repository.
Analyze the following repository and return a JSON object with EXACTLY these keys:
- "problem_solved": What real problem does this project solve? (1-2 sentences, specific)
- "target_audience": Who are the primary users? (1 sentence)
- "key_features": Array of 4-6 specific feature strings (be concrete, no generic fluff)
- "tech_stack": Array of the ACTUAL technologies used (look at the detected frameworks and dependencies listed below — DO NOT guess or hallucinate)
- "project_type": One of: "web-app", "mobile-app", "cli-tool", "library", "api", "data-science", "devtool", "other"
- "tagline": A punchy one-liner (max 12 words) that captures what the project does

CRITICAL: Base tech_stack ONLY on what is explicitly listed in detected frameworks and dependencies.
If it's a React + TypeScript project, say React and TypeScript. Do NOT invent Pandas or Docker if they aren't there.

Repository Data:
{summary}

Return ONLY raw valid JSON. No markdown. No explanation."""

    try:
        content = _call_llm(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise code analyst. Respond ONLY with raw valid JSON. No markdown code fences."},
                {"role": "user", "content": prompt},
            ],
        )
        content = _strip_and_extract_json(content)
        return json.loads(content)
    except Exception as e:
        print(f"Error in analyze_codebase: {e}")
        return {}


def generate_readme_content(context: dict, enriched_analysis: dict) -> str:
    """Generate a high-quality README.md using real project data."""
    model = _get_model()
    summary = summarize_context_for_llm(context, enriched_analysis)

    tech_stack = enriched_analysis.get("tech_stack", [])
    project_type = enriched_analysis.get("project_type", "project")
    tagline = enriched_analysis.get("tagline", context.get("description", ""))
    deployment_url = context.get("deployment_url", "")

    prompt = f"""Write a high-quality, professional README.md for this GitHub repository.

Project tagline: {tagline}
Project type: {project_type}
Real tech stack: {", ".join(tech_stack)}
Live URL: {deployment_url if deployment_url else "N/A"}

Include these sections:
1. Title + tagline (use the real tagline above)
2. Badges (build status, license, version — use placeholder badge URLs)
3. Brief description of what it actually does (use problem_solved from analysis)
4. Key Features (use the key_features from analysis — be specific, no fluff)
5. Tech Stack (list ONLY the real stack: {", ".join(tech_stack)})
6. Getting Started (installation + first run command — infer from key files if possible)
7. Usage (one realistic example)
8. Contributing (standard template)
9. License

Repository Data:
{summary}

Return ONLY valid markdown. No preamble, no explanation."""

    try:
        content = _call_llm(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return content
    except Exception as e:
        print(f"Error in generate_readme_content: {e}")
        return "# README\n\nError generating README content."


def generate_social_posts(context: dict, platforms: list, enriched_analysis: dict) -> dict:
    """Generate platform-specific social posts. Returns {platform: post_text}."""
    model = _get_json_model()
    summary = summarize_context_for_llm(context, enriched_analysis)

    tagline = enriched_analysis.get("tagline", context.get("description", ""))
    tech_stack = enriched_analysis.get("tech_stack", [])
    key_features = enriched_analysis.get("key_features", [])
    deployment_url = context.get("deployment_url", "")
    repo_url = context.get("url", "")
    project_name = context.get("name", "").split("/")[-1]

    prompt = f"""Generate social media launch posts for this project.

Project: {project_name}
Tagline: {tagline}
Tech stack: {", ".join(tech_stack)}
Key features: {", ".join(key_features[:4])}
Live URL: {deployment_url if deployment_url else repo_url}
GitHub: {repo_url}

Generate posts for: {", ".join(platforms)}

LinkedIn: Professional tone. 3 paragraphs. Start with a hook about the problem it solves.
End with the live URL and GitHub link. Include 5 relevant hashtags.

Twitter: A 5-tweet thread. Tweet 1 = hook. Tweet 2 = problem. Tweet 3 = solution + stack.
Tweet 4 = key features (use bullet points). Tweet 5 = CTA with links.
Format as: "1/ text\\n2/ text\\n..." etc.

Devto: An article intro. Title, subtitle, 2-paragraph intro that would make a developer click.
End with "Read more at: {repo_url}"

Return ONLY raw valid JSON with keys: "linkedin", "twitter", "devto".
No markdown. No code fences."""

    try:
        content = _call_llm(
            model=model,
            messages=[
                {"role": "system", "content": "You are a developer-focused copywriter. Respond ONLY with raw valid JSON. No markdown code fences."},
                {"role": "user", "content": prompt},
            ],
        )
        content = _strip_and_extract_json(content)
        return json.loads(content)
    except Exception as e:
        print(f"Error in generate_social_posts: {e}")
        return {}


def generate_roadmap(context: dict, enriched_analysis: dict) -> str:
    """Generate a realistic ROADMAP.md for the project."""
    model = _get_model()
    summary = summarize_context_for_llm(context, enriched_analysis)

    prompt = f"""Generate a realistic 3-month development roadmap for this project as a ROADMAP.md file.

Base it on what the project currently does and what's logically missing or improvable.
Structure as:
- ## v1.0 — Current State (what already exists)
- ## v1.1 — Month 1 (quick wins: bug fixes, polish, low-hanging features)
- ## v1.2 — Month 2 (core new features)
- ## v2.0 — Month 3 (major milestone)

Use GitHub-style task checkboxes: - [ ] item
Be specific to THIS project. Do not write generic placeholder roadmaps.

Repository Data:
{summary}

Return ONLY valid markdown."""

    try:
        content = _call_llm(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return content
    except Exception as e:
        print(f"Error in generate_roadmap: {e}")
        return "# Roadmap\n\nError generating roadmap."
