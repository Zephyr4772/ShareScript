"""
content_tools.py — Generate Marp presentation slides and ROADMAP.md
"""
import os
import tempfile
from llm_tools import generate_roadmap


def create_marp_presentation(context: dict, enriched_analysis: dict, readme_content: str) -> str:
    """
    Generate a Marp-compatible markdown slide deck.
    Convert to PDF with: npx @marp-team/marp-cli presentation.md --pdf
    """
    name = context.get("name", "Project").split("/")[-1]
    description = context.get("description", "")
    tagline = enriched_analysis.get("tagline", description) or name
    problem = enriched_analysis.get("problem_solved", "")
    audience = enriched_analysis.get("target_audience", "developers")
    features = enriched_analysis.get("key_features", [])
    tech_stack = enriched_analysis.get("tech_stack", [])
    project_type = enriched_analysis.get("project_type", "project")
    deployment_url = context.get("deployment_url", "")
    repo_url = context.get("url", "")
    stars = context.get("stars", 0)
    language = context.get("language", "")

    # Pre-compute all conditional strings (Python 3.10 can't have backslashes in f-string expressions)
    tech_list = "\n".join(["- **" + t + "**" for t in tech_stack]) or "- Modern web stack"
    feature_list = "\n".join(["- " + f for f in features[:6]]) or "- Core functionality\n- Clean architecture"
    project_type_label = project_type.replace("-", " ").title()
    lang_label = language or "Multi-language"
    audience_label = audience or "developers and teams"
    tagline_lower = tagline.lower() if tagline else "solves this problem elegantly"
    type_prefix = ("a " + project_type.replace("-", " ") + " that ") if project_type != "other" else "a project that "

    if deployment_url:
        demo_slide = "Live at: [" + deployment_url + "](" + deployment_url + ")"
    else:
        demo_slide = "GitHub: [" + repo_url + "](" + repo_url + ")"

    if deployment_url:
        footer_url = "Live: " + deployment_url
    else:
        footer_url = ""

    arch_name = name

    slides = """---
marp: true
theme: default
paginate: true
backgroundColor: '#111827'
color: '#F9FAFB'
style: |
  section {
    font-family: 'Inter', sans-serif;
    font-size: 28px;
    padding: 60px;
  }
  h1 { color: #6366F1; font-size: 56px; }
  h2 { color: #A5B4FC; font-size: 42px; border-bottom: 2px solid #6366F1; padding-bottom: 10px; }
  strong { color: #10B981; }
  code { background: #1F2937; color: #F9FAFB; padding: 4px 8px; border-radius: 4px; }
  a { color: #60A5FA; }
---

# """ + name + """

### """ + tagline + """

> """ + project_type_label + """ · """ + lang_label + """ · """ + str(stars) + """ stars

---

## The Problem

""" + (problem if problem else ("*" + name + " addresses a real pain point for " + audience_label + ".*")) + """

---

## The Solution

**""" + name + """** is """ + type_prefix + tagline_lower + """.

> Built for: """ + audience_label + """

---

## Key Features

""" + feature_list + """

---

## Tech Stack

""" + tech_list + """

---

## Demo

""" + demo_slide + """

*[Show live demo here]*

---

## Architecture

```
""" + arch_name + """/
├── Core application logic
├── UI / Frontend layer
├── Data / API layer
└── Configuration & deployment
```

*[Add architecture diagram if available]*

---

## Getting Started

```bash
git clone """ + repo_url + """
cd """ + name + """
# Install dependencies and run
```

Full instructions in README.md

---

## Roadmap

- v1.0 — Core features shipped
- v1.1 — Performance & polish
- v2.0 — Major feature expansion

---

## Thank You

**""" + name + """**

""" + repo_url + """

""" + footer_url + """

*Built with ShipScript*
"""

    out_dir = tempfile.mkdtemp(prefix="shipscript_slides_")
    out_path = os.path.join(out_dir, "presentation.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(slides)

    return out_path


def create_roadmap(context: dict, enriched_analysis: dict) -> str:
    """Generate ROADMAP.md using the LLM."""
    roadmap_text = generate_roadmap(context, enriched_analysis)

    out_dir = tempfile.mkdtemp(prefix="shipscript_roadmap_")
    out_path = os.path.join(out_dir, "ROADMAP.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(roadmap_text)

    return out_path
