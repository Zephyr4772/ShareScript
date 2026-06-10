import os
import json
from dotenv import load_dotenv
load_dotenv()
from mcp.server.fastmcp import FastMCP
from github_tools import fetch_repo_context

# Initialize FastMCP server
mcp = FastMCP("ShipScript")

@mcp.tool()
def analyze_repo(repo_url: str) -> dict:
    """
    Analyzes a GitHub repository and returns a structured context object.
    This context should be passed into all subsequent ShipScript tools.
    
    Args:
        repo_url: The full URL to the GitHub repository (e.g., https://github.com/owner/repo)
    """
    try:
        context = fetch_repo_context(repo_url)
        from llm_tools import analyze_codebase
        enriched = analyze_codebase(context)
        context["enriched_analysis"] = enriched
        return {"status": "success", "context": context}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Stub out the other tools to be implemented in future phases
@mcp.tool()
def generate_readme(context: dict) -> dict:
    """Generates an improved README based on the repo context."""
    enriched = context.get("enriched_analysis", {})
    if not enriched:
        return {"status": "error", "message": "Run analyze_repo first — enriched_analysis is missing."}
        
    from llm_tools import generate_readme_content
    readme_md = generate_readme_content(context, enriched)
    return {"status": "success", "readme": readme_md}

@mcp.tool()
def capture_screenshot(context: dict) -> dict:
    """Captures a deployment screenshot based on the repo context."""
    from visual_tools import capture_screenshot
    return capture_screenshot(context)

@mcp.tool()
def generate_visuals(context: dict) -> dict:
    """Generates all charts (language, tech stack, stats) based on repo context."""
    from visual_tools import generate_all_charts
    return generate_all_charts(context)

@mcp.tool()
def generate_social_content(context: dict, platforms: str = "linkedin,twitter,devto") -> dict:
    """Generates social media content (Twitter, Dev.to) based on the repo context."""
    enriched = context.get("enriched_analysis", {})
    if not enriched:
        return {"status": "error", "message": "Run analyze_repo first — enriched_analysis is missing."}
        
    from llm_tools import generate_social_posts
    platform_list = [p.strip() for p in platforms.split(",")]
    posts = generate_social_posts(context, platform_list, enriched)
    return {"status": "success", "posts": posts}

@mcp.tool()
def create_pr(repo_url: str, readme_content: str, github_pat: str) -> dict:
    """Creates a PR with the generated README. Requires a GitHub PAT with repo scope."""
    from github_tools import create_readme_pr
    return create_readme_pr(repo_url, readme_content, github_pat)

@mcp.tool()
def package_output(context: dict, visuals: dict, social_posts: dict, readme_content: str) -> dict:
    """Packages all generated content into a ZIP file. Output is a local file path."""
    from package_tools import create_zip_package
    return create_zip_package(context, visuals, social_posts, readme_content)

if __name__ == "__main__":
    mcp.run()
