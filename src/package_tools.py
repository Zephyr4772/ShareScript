import os
import json
import zipfile
import tempfile
from pathlib import Path


def create_zip_package(
    context: dict,
    visuals: dict,
    social_posts: dict,
    social_cards: dict,
    readme_content: str,
    presentation_path: str = None,
    roadmap_path: str = None,
) -> dict:
    """
    Bundle all generated assets into a single ZIP file.
    Returns {"status": "success", "zip_path": str}
    """
    try:
        repo_name = context.get("name", "repo").replace("/", "_")
        out_dir = tempfile.mkdtemp(prefix="shipscript_zip_")
        zip_path = os.path.join(out_dir, f"{repo_name}_launch_kit.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # README
            if readme_content:
                zf.writestr(f"{repo_name}/README_improved.md", readme_content)

            # Social posts (text)
            for platform, post_text in social_posts.items():
                if post_text:
                    if isinstance(post_text, (dict, list)):
                        post_text = json.dumps(post_text, indent=2)
                    zf.writestr(
                        f"{repo_name}/social_posts/{platform}.txt",
                        str(post_text),
                    )

            # Social card images
            for platform, card_path in social_cards.items():
                if card_path and os.path.exists(card_path):
                    zf.write(card_path, f"{repo_name}/social_cards/social_card_{platform}.png")

            # Charts
            for key in ["language_donut", "tech_stack", "stats_card"]:
                path = visuals.get(key)
                if path and os.path.exists(path):
                    zf.write(path, f"{repo_name}/visuals/{key}.png")

            # Screenshot
            screenshot = visuals.get("screenshot")
            if screenshot and os.path.exists(screenshot):
                zf.write(screenshot, f"{repo_name}/visuals/deployment_screenshot.png")

            # Presentation slides
            if presentation_path and os.path.exists(presentation_path):
                zf.write(presentation_path, f"{repo_name}/presentation.md")

            # Roadmap
            if roadmap_path and os.path.exists(roadmap_path):
                zf.write(roadmap_path, f"{repo_name}/ROADMAP.md")

            # Context JSON (useful for debugging / passing to other tools)
            context_export = {k: v for k, v in context.items()
                              if k not in ("key_files", "enriched_analysis")}
            zf.writestr(
                f"{repo_name}/context.json",
                json.dumps(context_export, indent=2),
            )

        return {"status": "success", "zip_path": zip_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}
