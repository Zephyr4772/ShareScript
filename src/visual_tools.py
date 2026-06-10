import os
import tempfile
import matplotlib.pyplot as plt
from playwright.sync_api import sync_playwright

def get_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="shipscript_visuals_")

def generate_language_donut(context: dict, output_dir: str) -> str:
    languages = context.get('languages', {})
    if not languages:
        return None
    
    labels = list(languages.keys())
    sizes = list(languages.values())
    
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
    ax.axis('equal')
    plt.title("Language Breakdown")
    
    out_path = os.path.join(output_dir, "language_breakdown.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    return out_path

def generate_tech_stack_graphic(enriched_analysis: dict, output_dir: str) -> str:
    tech_stack = enriched_analysis.get('tech_stack', [])
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]
    elif isinstance(tech_stack, dict):
        tech_stack = list(tech_stack.keys())
        
    if not tech_stack:
        return None
        
    fig, ax = plt.subplots(figsize=(8, len(tech_stack) * 0.5 + 1))
    ax.axis('off')
    
    for i, tech in enumerate(tech_stack):
        ax.text(0.5, 1 - (i * 0.15), str(tech), fontsize=14, ha='center', va='center',
                bbox=dict(facecolor='lightblue', alpha=0.5, boxstyle='round,pad=0.5'))
                
    plt.title("Core Tech Stack", fontsize=16, pad=20)
    out_path = os.path.join(output_dir, "tech_stack.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    return out_path

def generate_stats_card(context: dict, output_dir: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis('off')
    
    stats_text = (
        f"Repo: {context.get('name', 'N/A')}\n\n"
        f"⭐ Stars: {context.get('stars', 0)}\n"
        f"🍴 Forks: {context.get('forks', 0)}\n"
        f"💻 Primary Language: {context.get('language', 'N/A')}\n"
    )
    topics = context.get('topics', [])
    if topics:
        stats_text += f"\n🏷️ Topics: {', '.join(topics[:5])}"
        
    ax.text(0.5, 0.5, stats_text, fontsize=14, ha='center', va='center',
            bbox=dict(facecolor='#f0f0f0', alpha=0.8, boxstyle='round,pad=1'))
            
    out_path = os.path.join(output_dir, "stats_card.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    return out_path

def generate_all_charts(context: dict) -> dict:
    enriched = context.get('enriched_analysis', {})
    out_dir = get_temp_dir()
    
    if not enriched:
        print("--> WARNING: enriched_analysis is empty. Check LLM_MODEL and your API key in .env.")
    
    return {
        "status": "success",
        "output_dir": out_dir,
        "language_donut": generate_language_donut(context, out_dir),
        "tech_stack": generate_tech_stack_graphic(enriched, out_dir),
        "stats_card": generate_stats_card(context, out_dir)
    }

def determine_deployment_url(context: dict) -> str:
    homepage = context.get('homepage')
    if homepage and homepage.startswith("http"):
        return homepage
        
    url = context.get('url', '')
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) >= 2:
        owner, repo = parts[0], parts[1]
        
        key_files = context.get('key_files', {})
        if "vercel.json" in key_files:
            return f"https://{repo}.vercel.app"
            
        return f"https://{owner}.github.io/{repo}"
        
    return None

def capture_screenshot(context: dict) -> dict:
    url = determine_deployment_url(context)
    if not url:
        return {"status": "success", "screenshot": None, "reason": "No deployment URL found"}
        
    out_dir = get_temp_dir()
    out_path = os.path.join(out_dir, "deployment_screenshot.png")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.screenshot(path=out_path)
            browser.close()
        return {"status": "success", "screenshot": out_path, "url": url}
    except Exception as e:
        return {"status": "success", "screenshot": None, "reason": f"Screenshot failed: {str(e)}"}
