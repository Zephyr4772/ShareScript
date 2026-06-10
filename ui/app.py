"""
ShipScript v2 — Gradio Web UI
Run: python ui/app.py
Opens at http://localhost:7860
"""
import sys
import os
import threading
import queue
import subprocess

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import gradio as gr


OPTION_LABELS = [
    "README + GitHub PR",
    "Social Posts (LinkedIn / Twitter / Dev.to)",
    "Social Card Images (PNG per platform)",
    "Charts & Visuals",
    "Deployment Screenshot",
    "Presentation Slides (Marp)",
    "Roadmap (ROADMAP.md)",
]
DEFAULT_OPTIONS = OPTION_LABELS[:5]  # everything except Marp + Roadmap by default


def run_pipeline(repo_url: str, deployment_url: str, options: list):
    """Generator — yields log lines + final ZIP path."""
    if not repo_url or not repo_url.strip():
        yield "❌ Please enter a GitHub repo URL.\n", None
        return

    log_lines = []

    def log(msg: str):
        log_lines.append(msg)
        return "\n".join(log_lines)

    # Lazy imports (kept inside to allow env to be loaded first)
    from server import (
        analyze_repo, generate_readme, capture_screenshot,
        generate_visuals, generate_social_content, generate_social_cards,
        generate_presentation, generate_roadmap, package_output, create_pr,
    )

    context = {}
    enriched = {}
    readme_content = ""
    visual_paths = {}
    social_posts = {}
    social_cards = {}
    presentation_path = None
    roadmap_path = None
    zip_path = None

    # ── Step 1: Analyze ──────────────────────────────────────────────────────
    yield log("🔍 Step 1/7 — Analyzing repo (deep framework detection)..."), None
    res = analyze_repo(repo_url.strip(), deployment_url.strip() if deployment_url else "")
    if res["status"] != "success":
        yield log(f"❌ analyze_repo failed: {res['message']}"), None
        return

    context = res["context"]
    enriched = context.get("enriched_analysis", {})
    deploy_src = context.get("deployment_url_source", "not_found")
    deploy_url = context.get("deployment_url")

    yield log(
        f"✅ Analyzed: {context.get('name')}\n"
        f"   Language: {context.get('language')} | Stars: {context.get('stars')}\n"
        f"   Frameworks: {', '.join(context.get('detected_frameworks', [])) or 'none'}\n"
        f"   Tech Stack: {', '.join(enriched.get('tech_stack', [])) or 'unknown'}\n"
        f"   Deployment URL: {deploy_url or 'NOT FOUND'} ({deploy_src})\n"
        + ("   ⚠️  No deployment URL found — screenshot will be skipped.\n" if not deploy_url else "")
    ), None

    # ── Step 2: README ───────────────────────────────────────────────────────
    if "README + GitHub PR" in options:
        yield log("📝 Step 2/7 — Generating README..."), None
        res = generate_readme(context)
        if res["status"] == "success":
            readme_content = res["readme"]
            yield log(f"✅ README generated ({len(readme_content)} chars)"), None
        else:
            yield log(f"⚠️  README generation failed: {res}"), None

    # ── Step 3: Visuals ──────────────────────────────────────────────────────
    if "Charts & Visuals" in options:
        yield log("📊 Step 3/7 — Generating charts..."), None
        res = generate_visuals(context)
        if res["status"] == "success":
            visual_paths = {k: v for k, v in res.items()
                           if k in ("language_donut", "tech_stack", "stats_card")}
            generated = [k for k, v in visual_paths.items() if v]
            yield log(f"✅ Charts: {', '.join(generated)}"), None
        else:
            yield log(f"⚠️  generate_visuals failed: {res}"), None

    # ── Step 4: Screenshot ───────────────────────────────────────────────────
    if "Deployment Screenshot" in options:
        yield log("📸 Step 4/7 — Capturing deployment screenshot..."), None
        res = capture_screenshot(context)
        if res.get("screenshot"):
            visual_paths["screenshot"] = res["screenshot"]
            yield log(f"✅ Screenshot: {res['url']} ({res.get('source', '')})"), None
        else:
            yield log(f"⚠️  Screenshot skipped: {res.get('reason', 'unknown')}"), None

    # ── Step 5: Social posts ─────────────────────────────────────────────────
    if "Social Posts (LinkedIn / Twitter / Dev.to)" in options:
        yield log("📣 Step 5/7 — Generating social posts..."), None
        res = generate_social_content(context, "linkedin,twitter,devto")
        if res["status"] == "success":
            social_posts = res["posts"]
            yield log(f"✅ Social posts: {list(social_posts.keys())}"), None
        else:
            yield log(f"⚠️  Social content failed: {res}"), None

    # ── Step 5b: Social card images ──────────────────────────────────────────
    if "Social Card Images (PNG per platform)" in options and social_posts:
        yield log("🎨 Step 5b — Generating social card images..."), None
        res = generate_social_cards(context, social_posts)
        if res["status"] == "success":
            social_cards = res["cards"]
            yield log(f"✅ Social cards: {list(social_cards.keys())}"), None
        else:
            yield log(f"⚠️  Social cards failed: {res}"), None

    # ── Step 6: Presentation ─────────────────────────────────────────────────
    if "Presentation Slides (Marp)" in options:
        yield log("🎯 Step 6/7 — Generating Marp presentation..."), None
        res = generate_presentation(context)
        if res["status"] == "success":
            presentation_path = res["presentation_path"]
            yield log(f"✅ Presentation: {presentation_path}"), None
        else:
            yield log(f"⚠️  Presentation failed: {res}"), None

    # ── Step 6b: Roadmap ─────────────────────────────────────────────────────
    if "Roadmap (ROADMAP.md)" in options:
        yield log("🗺️  Step 6b — Generating roadmap..."), None
        res = generate_roadmap(context)
        if res["status"] == "success":
            roadmap_path = res["roadmap_path"]
            yield log(f"✅ Roadmap: {roadmap_path}"), None
        else:
            yield log(f"⚠️  Roadmap failed: {res}"), None

    # ── Step 7: GitHub PR ────────────────────────────────────────────────────
    if "README + GitHub PR" in options and readme_content:
        yield log("🔀 Step 7/7 — Creating GitHub PR..."), None
        github_pat = os.environ.get("GITHUB_PAT", "")
        if github_pat:
            res = create_pr(repo_url.strip(), readme_content, github_pat)
            if res["status"] == "success":
                yield log(f"✅ PR created: {res['pr_url']}"), None
            else:
                yield log(f"⚠️  PR creation failed: {res['message']}"), None
        else:
            yield log("⚠️  No GITHUB_PAT set — skipping PR creation."), None

    # ── Step 8: Package ZIP ──────────────────────────────────────────────────
    yield log("📦 Packaging everything into ZIP..."), None
    res = package_output(
        context, visual_paths, social_posts, readme_content,
        social_cards=social_cards,
        presentation_path=presentation_path,
        roadmap_path=roadmap_path,
    )
    if res["status"] == "success":
        zip_path = res["zip_path"]
        yield log(f"\n🎉 DONE! ZIP ready: {zip_path}"), zip_path
    else:
        yield log(f"❌ Packaging failed: {res['message']}"), None


# ── Gradio UI ─────────────────────────────────────────────────────────────────

LOGO = "🚀"
TITLE = "ShipScript"
DESCRIPTION = "Paste a GitHub repo URL and get: README, social posts, charts, screenshots, slides, and a ZIP bundle — all in one click."

custom_css = """
#title { font-size: 2.5em; font-weight: 800; color: #6366F1; }
#desc { color: #9CA3AF; font-size: 1.05em; margin-bottom: 1em; }
.gr-button-primary { background: #6366F1 !important; border: none !important; }
.gr-button-primary:hover { background: #4F46E5 !important; }
#log-box textarea { font-family: 'Fira Mono', monospace; font-size: 13px; background: #111827; color: #D1FAE5; }
"""

with gr.Blocks(title="ShipScript", theme=gr.themes.Soft(), css=custom_css) as demo:
    gr.HTML(f'<div id="title">{LOGO} {TITLE}</div>')
    gr.HTML(f'<div id="desc">{DESCRIPTION}</div>')

    with gr.Row():
        with gr.Column(scale=3):
            repo_url = gr.Textbox(
                label="GitHub Repo URL",
                placeholder="https://github.com/owner/repo",
                lines=1,
            )
            deployment_url = gr.Textbox(
                label="Deployment URL (optional — leave blank to auto-detect)",
                placeholder="https://myapp.vercel.app",
                lines=1,
            )

        with gr.Column(scale=2):
            options = gr.CheckboxGroup(
                choices=OPTION_LABELS,
                value=DEFAULT_OPTIONS,
                label="What to generate",
            )

    run_btn = gr.Button("🚀 Run ShipScript", variant="primary", size="lg")

    log_output = gr.Textbox(
        label="Progress",
        lines=20,
        interactive=False,
        elem_id="log-box",
        show_copy_button=True,
    )

    zip_file = gr.File(label="Download Output ZIP", interactive=False)

    gr.HTML("""
    <details style="margin-top:1em; color:#6B7280;">
    <summary>💡 Tips</summary>
    <ul>
      <li>Deployment URL is auto-detected via Vercel API + HTTP ping. Override it if wrong.</li>
      <li>Presentation Slides requires <code>npx @marp-team/marp-cli presentation.md --pdf</code> to convert to PDF.</li>
      <li>Social Card Images are 1200×627px PNGs ready for LinkedIn, Twitter, and Dev.to.</li>
      <li>All output is bundled in a ZIP you can download below.</li>
    </ul>
    </details>
    """)

    run_btn.click(
        fn=run_pipeline,
        inputs=[repo_url, deployment_url, options],
        outputs=[log_output, zip_file],
    )

demo.queue()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, inbrowser=True)
