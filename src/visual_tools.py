import os
import tempfile
from typing import Optional
import plotly.graph_objects as go
from playwright.sync_api import sync_playwright

# ── Tech stack brand colors ───────────────────────────────────────────────────
TECH_COLORS = {
    "React": "#61DAFB", "Next.js": "#000000", "Vue.js": "#42B883",
    "Angular": "#DD0031", "Svelte": "#FF3E00", "TypeScript": "#3178C6",
    "JavaScript": "#F7DF1E", "Python": "#3776AB", "FastAPI": "#009688",
    "Django": "#092E20", "Flask": "#000000", "Node.js": "#339933",
    "Tailwind CSS": "#06B6D4", "Prisma": "#2D3748", "Supabase": "#3ECF8E",
    "Firebase": "#FFCA28", "PostgreSQL": "#4169E1", "MongoDB": "#47A248",
    "Rust": "#CE422B", "Go": "#00ADD8", "Java": "#ED8B00", "C#": "#239120",
}

PLATFORM_CONFIGS = {
    "linkedin": {"w": 1200, "h": 627,  "color": "#0077B5", "accent": "#004471"},
    "twitter":  {"w": 1200, "h": 675,  "color": "#1DA1F2", "accent": "#0d8fd9"},
    "devto":    {"w": 1000, "h": 420,  "color": "#0a0a0a", "accent": "#3b49df"},
}


def _get_temp_dir() -> str:
    return tempfile.mkdtemp(prefix="shipscript_v2_")


def _pick_colors(languages: dict, detected_frameworks: list) -> list:
    """Return a list of brand-accurate hex colors for detected tech."""
    colors = []
    for tech in list(languages.keys()) + detected_frameworks:
        c = TECH_COLORS.get(tech)
        if c and c not in colors:
            colors.append(c)
    # Fill with a nice palette if we ran out
    fallback = ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#3B82F6"]
    while len(colors) < 8:
        colors.extend(fallback)
    return colors


# ── Chart: Language donut ────────────────────────────────────────────────────

def generate_language_donut(context: dict, out_dir: str) -> Optional[str]:
    languages = context.get("languages", {})
    if isinstance(languages, dict):
        languages = {k: v for k, v in languages.items() if isinstance(v, (int, float)) and v > 0}
    if not languages:
        return None

    labels = list(languages.keys())
    values = list(languages.values())
    colors = _pick_colors(languages, [])[:len(labels)]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#111827", width=2)),
        textinfo="label+percent",
        textfont=dict(size=14, color="white"),
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="white", family="Inter, sans-serif"),
        showlegend=False,
        margin=dict(t=50, b=20, l=20, r=20),
        title=dict(text="Language Breakdown", font=dict(size=18, color="white"), x=0.5),
        annotations=[dict(
            text=f"{labels[0]}", x=0.5, y=0.5, font_size=16,
            showarrow=False, font=dict(color="white"),
        )],
    )

    out_path = os.path.join(out_dir, "language_donut.png")
    fig.write_image(out_path, width=600, height=500, scale=2)
    return out_path


# ── Chart: Tech stack bar chart ───────────────────────────────────────────────

def generate_tech_stack_chart(context: dict, out_dir: str) -> Optional[str]:
    enriched = context.get("enriched_analysis", {})
    tech_stack = enriched.get("tech_stack", [])
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]
    if not tech_stack:
        tech_stack = context.get("detected_frameworks", [])
    if not tech_stack:
        return None

    colors = [TECH_COLORS.get(t, "#6366F1") for t in tech_stack]

    fig = go.Figure(go.Bar(
        y=tech_stack,
        x=[1] * len(tech_stack),
        orientation="h",
        marker=dict(color=colors, line=dict(color="#1F2937", width=1)),
        text=tech_stack,
        textposition="inside",
        textfont=dict(size=14, color="white", family="Inter, sans-serif"),
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#1F2937",
        font=dict(color="white", family="Inter, sans-serif"),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(t=50, b=20, l=20, r=20),
        title=dict(text="Tech Stack", font=dict(size=18, color="white"), x=0.5),
        height=max(300, len(tech_stack) * 55 + 80),
    )

    out_path = os.path.join(out_dir, "tech_stack.png")
    fig.write_image(out_path, width=700, scale=2)
    return out_path


# ── Chart: Stats card ────────────────────────────────────────────────────────

def generate_stats_card(context: dict, out_dir: str) -> Optional[str]:
    name = context.get("name", "Unknown Repo")
    lang = context.get("language") or "Unknown"
    stars = context.get("stars", 0)
    forks = context.get("forks", 0)
    topics = context.get("topics", [])
    frameworks = context.get("detected_frameworks", [])

    fig = go.Figure()
    fig.add_annotation(text=name.split("/")[-1], x=0.5, y=0.85,
                       font=dict(size=26, color="white", family="Inter, sans-serif"),
                       showarrow=False, xref="paper", yref="paper")
    fig.add_annotation(text=f"<b>{stars}</b> stars  |  <b>{forks}</b> forks  |  {lang}",
                       x=0.5, y=0.60,
                       font=dict(size=16, color="#9CA3AF"),
                       showarrow=False, xref="paper", yref="paper")

    if frameworks:
        fig.add_annotation(text=" · ".join(frameworks[:5]),
                           x=0.5, y=0.38,
                           font=dict(size=14, color="#6366F1"),
                           showarrow=False, xref="paper", yref="paper")

    if topics:
        fig.add_annotation(text="  ".join([f"#{t}" for t in topics[:6]]),
                           x=0.5, y=0.18,
                           font=dict(size=12, color="#10B981"),
                           showarrow=False, xref="paper", yref="paper")

    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        margin=dict(t=20, b=20, l=20, r=20),
        width=700, height=300,
    )
    fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=1, xref="paper", yref="paper",
                  line=dict(color="#6366F1", width=3))

    out_path = os.path.join(out_dir, "stats_card.png")
    fig.write_image(out_path, width=700, height=300, scale=2)
    return out_path


# ── Social card images (Pillow) ───────────────────────────────────────────────

def generate_social_cards(context: dict, social_posts: dict, out_dir: str) -> dict:
    """Generate styled PNG social cards per platform using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed — skipping social cards.")
        return {}

    enriched = context.get("enriched_analysis", {})
    project_name = context.get("name", "").split("/")[-1]
    tagline = enriched.get("tagline", context.get("description", ""))
    tech_stack = enriched.get("tech_stack", [])
    results = {}

    def _wrap(text: str, max_chars: int) -> list:
        words = text.split()
        lines, line = [], ""
        for w in words:
            if len(line) + len(w) + 1 <= max_chars:
                line = (line + " " + w).strip()
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines

    for platform, cfg in PLATFORM_CONFIGS.items():
        if platform not in social_posts:
            continue

        W, H = cfg["w"], cfg["h"]
        bg_color = cfg["color"]
        accent = cfg["accent"]

        img = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(img)

        # Gradient top bar
        for i in range(10):
            alpha = int(80 * (1 - i / 10))
            draw.rectangle([(0, i * 4), (W, (i + 1) * 4)], fill=accent)

        # Accent left stripe
        draw.rectangle([(0, 0), (8, H)], fill="#ffffff20")

        # Project name (large)
        try:
            font_large = ImageFont.truetype("arial.ttf", 64)
            font_med = ImageFont.truetype("arial.ttf", 32)
            font_small = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            font_large = ImageFont.load_default()
            font_med = font_large
            font_small = font_large

        name_display = project_name.upper()
        draw.text((60, 60), name_display, fill="white", font=font_large)

        # Tagline (wrapped)
        tagline_lines = _wrap(tagline, 60)[:3]
        y = 145
        for line in tagline_lines:
            draw.text((60, y), line, fill="#E5E7EB", font=font_med)
            y += 44

        # Tech stack pills
        x_pill = 60
        y_pill = H - 130
        for tech in tech_stack[:6]:
            pill_color = TECH_COLORS.get(tech, "#374151")
            tw = len(tech) * 14 + 24
            draw.rounded_rectangle([(x_pill, y_pill), (x_pill + tw, y_pill + 36)],
                                   radius=8, fill=pill_color)
            draw.text((x_pill + 12, y_pill + 8), tech, fill="white", font=font_small)
            x_pill += tw + 12
            if x_pill > W - 200:
                break

        # GitHub URL
        repo_url = context.get("url", "")
        draw.text((60, H - 70), repo_url, fill="#9CA3AF", font=font_small)

        # Platform watermark (bottom right)
        platform_label = platform.upper()
        pw = len(platform_label) * 14 + 20
        draw.text((W - pw - 30, H - 55), platform_label, fill="#ffffff60", font=font_med)

        # Bottom border
        draw.rectangle([(0, H - 6), (W, H)], fill="#ffffff30")

        out_path = os.path.join(out_dir, f"social_card_{platform}.png")
        img.save(out_path)
        results[platform] = out_path

    return results


# ── Screenshot ───────────────────────────────────────────────────────────────

def capture_screenshot(context: dict) -> dict:
    """Screenshot the deployment URL stored in context."""
    url = context.get("deployment_url")
    source = context.get("deployment_url_source", "not_found")

    if not url:
        return {
            "status": "success",
            "screenshot": None,
            "reason": f"No deployment URL found (source: {source}). Pass deployment_url manually.",
        }

    out_dir = _get_temp_dir()
    out_path = os.path.join(out_dir, "deployment_screenshot.png")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, timeout=20000, wait_until="networkidle")
            page.screenshot(path=out_path, full_page=False)
            browser.close()
        return {"status": "success", "screenshot": out_path, "url": url, "source": source}
    except Exception as e:
        return {"status": "success", "screenshot": None, "reason": f"Screenshot failed: {e}"}


# ── Orchestrator ─────────────────────────────────────────────────────────────

def generate_all_charts(context: dict) -> dict:
    """Generate all chart PNGs. Returns paths (None if skipped)."""
    out_dir = _get_temp_dir()
    enriched = context.get("enriched_analysis", {})

    if not enriched:
        print("--> WARNING: enriched_analysis empty — some charts may be skipped.")

    return {
        "status": "success",
        "output_dir": out_dir,
        "language_donut": generate_language_donut(context, out_dir),
        "tech_stack": generate_tech_stack_chart(context, out_dir),
        "stats_card": generate_stats_card(context, out_dir),
    }
