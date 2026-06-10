import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Ensure src is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from server import analyze_repo, generate_readme, generate_visuals, capture_screenshot, generate_social_content, package_output

def main():
    repo_url = "https://github.com/Zephyr4772/eduedu"
    print(f"Testing against: {repo_url}\n")
    
    print("1. analyze_repo...")
    repo_res = analyze_repo(repo_url)
    if repo_res["status"] != "success":
        print("analyze_repo failed:", repo_res)
        return
    context = repo_res["context"]
    enriched = context.get("enriched_analysis")
    print(f"-> Success! Enriched analysis returned data: {bool(enriched)}")
    if not enriched:
        print("-> WARNING: enriched_analysis is empty. Azure credentials may be missing or failing.")
    else:
        print(f"   Tech Stack detected: {enriched.get('tech_stack')}")
        
    print("\n2. generate_readme...")
    readme_res = generate_readme(context)
    readme_content = ""
    if readme_res["status"] == "success":
        readme_content = readme_res["readme"]
        print(f"-> Success! Generated {len(readme_content)} chars of README.")
    else:
        print("-> generate_readme failed:", readme_res)

    print("\n3. generate_visuals...")
    visuals_res = generate_visuals(context)
    visual_paths = {}
    if visuals_res["status"] == "success":
        visual_paths = {k: v for k, v in visuals_res.items() if k in ["language_donut", "tech_stack", "stats_card"]}
        print(f"-> Success! Generated visual paths:")
        for k, v in visual_paths.items():
            exists = os.path.exists(v) if v else False
            print(f"   {k}: {v} (Exists: {exists})")
    else:
        print("-> generate_visuals failed:", visuals_res)
        
    print("\n4. capture_screenshot...")
    screenshot_res = capture_screenshot(context)
    if screenshot_res["status"] == "success":
        scr_path = screenshot_res.get("screenshot")
        if scr_path and os.path.exists(scr_path):
            print(f"-> Success! Screenshot saved to {scr_path}")
            visual_paths["screenshot"] = scr_path
        else:
            print(f"-> No screenshot captured. Reason: {screenshot_res.get('reason')}")
    else:
        print("-> capture_screenshot failed:", screenshot_res)
        
    print("\n5. generate_social_content...")
    social_res = generate_social_content(context, "linkedin,twitter,devto")
    social_posts = {}
    if social_res["status"] == "success":
        social_posts = social_res["posts"]
        print(f"-> Success! Generated posts for: {list(social_posts.keys())}")
    else:
        print("-> generate_social_content failed:", social_res)
        
    print("\n6. package_output...")
    pkg_res = package_output(context, visual_paths, social_posts, readme_content)
    if pkg_res["status"] == "success":
        zip_path = pkg_res["zip_path"]
        print(f"-> Success! ZIP created at {zip_path}")
        print(f"   ZIP exists: {os.path.exists(zip_path)}")
    else:
        print("-> package_output failed:", pkg_res)

if __name__ == "__main__":
    main()
