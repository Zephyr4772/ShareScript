import sys
import os
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server import (
    analyze_repo, generate_readme, generate_visuals, capture_screenshot,
    generate_social_content, generate_social_cards, generate_presentation,
    generate_roadmap, package_output,
)


def main():
    repo_url = "https://github.com/Zephyr4772/gemcart"

    print(f"ShipScript v2 -- Testing against: {repo_url}\n")

    # ── 1. Analyze ──────────────────────────────────────────────────────────
    print("1. analyze_repo...")
    res = analyze_repo(repo_url)
    if res["status"] != "success":
        print("FAILED:", res)
        return
    context = res["context"]
    enriched = context.get("enriched_analysis", {})
    print(f"   [OK] Frameworks detected: {context.get('detected_frameworks')}")
    print(f"   [OK] Language: {context.get('language')}")
    print(f"   [OK] Deployment URL: {context.get('deployment_url')} ({context.get('deployment_url_source')})")
    print(f"   [OK] Tech Stack (LLM): {enriched.get('tech_stack')}")
    print(f"   [OK] Tagline: {enriched.get('tagline')}")
    print(f"   [OK] Project type: {enriched.get('project_type')}")

    # ── 2. README ────────────────────────────────────────────────────────────
    print("\n2. generate_readme...")
    readme_content = ""
    res = generate_readme(context)
    if res["status"] == "success":
        readme_content = res["readme"]
        print(f"   [OK] {len(readme_content)} chars")
        print(f"   Preview: {readme_content[:150].strip()}")
    else:
        print("   FAILED:", res)

    # ── 3. Visuals ───────────────────────────────────────────────────────────
    print("\n3. generate_visuals...")
    visual_paths = {}
    res = generate_visuals(context)
    if res["status"] == "success":
        visual_paths = {k: v for k, v in res.items()
                        if k in ("language_donut", "tech_stack", "stats_card")}
        for k, v in visual_paths.items():
            exists = os.path.exists(v) if v else False
            print(f"   {'[OK]' if exists else '[SKIP]'} {k}: {v}")
    else:
        print("   FAILED:", res)

    # ── 4. Screenshot ────────────────────────────────────────────────────────
    print("\n4. capture_screenshot...")
    res = capture_screenshot(context)
    if res.get("screenshot") and os.path.exists(res["screenshot"]):
        visual_paths["screenshot"] = res["screenshot"]
        print(f"   [OK] {res['screenshot']}")
        print(f"   Source: {res.get('source')}")
    else:
        print(f"   [SKIP] {res.get('reason')}")

    # ── 5. Social posts ──────────────────────────────────────────────────────
    print("\n5. generate_social_content...")
    social_posts = {}
    res = generate_social_content(context, "linkedin,twitter,devto")
    if res["status"] == "success":
        social_posts = res["posts"]
        print(f"   [OK] Platforms: {list(social_posts.keys())}")
        if "twitter" in social_posts:
            preview = str(social_posts['twitter'])[:120].encode('ascii', errors='replace').decode()
            print(f"   Twitter preview: {preview}...")
    else:
        print("   FAILED:", res)

    # ── 5b. Social cards ─────────────────────────────────────────────────────
    print("\n5b. generate_social_cards...")
    social_cards = {}
    if social_posts:
        res = generate_social_cards(context, social_posts)
        if res["status"] == "success":
            social_cards = res["cards"]
            for platform, path in social_cards.items():
                exists = os.path.exists(path) if path else False
                print(f"   {'[OK]' if exists else '[FAIL]'} {platform}: {path}")
        else:
            print("   FAILED:", res)

    # ── 6. Presentation ──────────────────────────────────────────────────────
    print("\n6. generate_presentation...")
    presentation_path = None
    res = generate_presentation(context)
    if res["status"] == "success":
        presentation_path = res["presentation_path"]
        print(f"   [OK] {presentation_path}")
    else:
        print("   FAILED:", res)

    # ── 7. Roadmap ───────────────────────────────────────────────────────────
    print("\n7. generate_roadmap...")
    roadmap_path = None
    res = generate_roadmap(context)
    if res["status"] == "success":
        roadmap_path = res["roadmap_path"]
        print(f"   [OK] {roadmap_path}")
    else:
        print("   FAILED:", res)

    # ── 8. Package ZIP ───────────────────────────────────────────────────────
    print("\n8. package_output...")
    res = package_output(
        context, visual_paths, social_posts, readme_content,
        social_cards=social_cards,
        presentation_path=presentation_path,
        roadmap_path=roadmap_path,
    )
    if res["status"] == "success":
        zip_path = res["zip_path"]
        print(f"\nSUCCESS! ZIP at: {zip_path}")
        print(f"Exists: {os.path.exists(zip_path)}")
    else:
        print("FAILED:", res)


if __name__ == "__main__":
    main()
