import os
from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from github_tools import fetch_repo_context

mcp = FastMCP("ShipScript")


@mcp.tool()
def analyze_repo(repo_url: str, deployment_url: str = "") -> dict:
    """
    Analyzes a GitHub repository and returns a rich context object.
    Detects frameworks, tech stack, and deployment URL automatically.

    Args:
        repo_url: Full GitHub URL (e.g., https://github.com/owner/repo)
        deployment_url: Optional — override auto-detected deployment URL
    """
    try:
        context = fetch_repo_context(repo_url, user_deployment_url=deployment_url or None)
        from llm_tools import analyze_codebase
        enriched = analyze_codebase(context)
        context["enriched_analysis"] = enriched
        return {"status": "success", "context": context}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def generate_readme(context: dict) -> dict:
    """Generates an improved README.md based on deep repo analysis."""
    enriched = context.get("enriched_analysis", {})
    if not enriched:
        return {"status": "error", "message": "Run analyze_repo first — enriched_analysis missing."}
    from llm_tools import generate_readme_content
    readme_md = generate_readme_content(context, enriched)
    return {"status": "success", "readme": readme_md}


@mcp.tool()
def capture_screenshot(context: dict) -> dict:
    """Screenshots the verified deployment URL stored in context."""
    from visual_tools import capture_screenshot as _screenshot
    return _screenshot(context)


@mcp.tool()
def generate_visuals(context: dict) -> dict:
    """Generates language donut, tech stack chart, and stats card PNGs."""
    from visual_tools import generate_all_charts
    return generate_all_charts(context)


@mcp.tool()
def generate_social_content(context: dict, platforms: str = "linkedin,twitter,devto") -> dict:
    """Generates social media posts for the specified platforms."""
    enriched = context.get("enriched_analysis", {})
    if not enriched:
        return {"status": "error", "message": "Run analyze_repo first — enriched_analysis missing."}
    from llm_tools import generate_social_posts
    platform_list = [p.strip() for p in platforms.split(",")]
    posts = generate_social_posts(context, platform_list, enriched)
    return {"status": "success", "posts": posts}


@mcp.tool()
def generate_social_cards(context: dict, social_posts: dict) -> dict:
    """Generates styled PNG social card images (LinkedIn, Twitter, Dev.to)."""
    from visual_tools import generate_social_cards as _gen_cards
    import tempfile
    out_dir = tempfile.mkdtemp(prefix="shipscript_cards_")
    cards = _gen_cards(context, social_posts, out_dir)
    return {"status": "success", "cards": cards}


@mcp.tool()
def generate_presentation(context: dict) -> dict:
    """Generates a Marp-compatible markdown slide deck."""
    enriched = context.get("enriched_analysis", {})
    readme = context.get("readme", "")
    from content_tools import create_marp_presentation
    path = create_marp_presentation(context, enriched, readme)
    return {"status": "success", "presentation_path": path}


@mcp.tool()
def generate_roadmap(context: dict) -> dict:
    """Generates a realistic ROADMAP.md using LLM analysis."""
    enriched = context.get("enriched_analysis", {})
    from content_tools import create_roadmap
    path = create_roadmap(context, enriched)
    return {"status": "success", "roadmap_path": path}


@mcp.tool()
def create_pr(repo_url: str, readme_content: str, github_pat: str) -> dict:
    """Creates a PR with the generated README. Requires a GitHub PAT with repo scope."""
    from github_tools import create_readme_pr
    return create_readme_pr(repo_url, readme_content, github_pat)


@mcp.tool()
def package_output(
    context: dict,
    visuals: dict,
    social_posts: dict,
    readme_content: str,
    social_cards: dict = None,
    presentation_path: str = None,
    roadmap_path: str = None,
) -> dict:
    """Bundles all generated content into a ZIP file."""
    from package_tools import create_zip_package
    return create_zip_package(
        context, visuals, social_posts,
        social_cards or {},
        readme_content,
        presentation_path,
        roadmap_path,
    )


if __name__ == "__main__":
    mcp.run()
