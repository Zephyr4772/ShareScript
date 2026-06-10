# ShipScript: Master Handoff Document

> [!IMPORTANT]
> **To any AI Agent (Antigravity/Claude/etc) reading this file:** 
> This is the state of the ShipScript codebase. Your goal is to help the team finalize the project and prepare it for demo. Read the architecture and progress below before making any changes.

## 🚀 The Concept
**ShipScript** is a Marketing & Launch-as-a-Service tool for Developers. 
Given a single GitHub repository URL, it acts as a reasoning agent that:
1. Understands the codebase, framework, tech stack, and what problem it solves.
2. Generates an improved README and automatically opens a GitHub PR.
3. Generates a 3-month `ROADMAP.md` and a 9-slide Marp markdown presentation.
4. Generates visual charts (Tech Stack, Language Breakdown) using Plotly (Dark Theme).
5. Writes social media posts (LinkedIn, Twitter, Dev.to) and creates stunning gradient social cards using Pillow.
6. Captures screenshots of the deployed project.
7. Packages everything into a clean `.zip` file for the developer to download via a responsive Gradio UI.

## 🏗️ Architecture & Tool Signatures
The system is built on Python and `FastMCP` but is now exposed via a powerful **Gradio UI** for the hackathon demo.
**Crucial State Model:** To prevent hitting the GitHub API repeatedly, state is passed forward. 
- `analyze_repo` runs *once*, fetching the codebase, performing deep framework detection (reading `package.json`/`requirements.txt`), detecting deployment URLs, and generating an `enriched_analysis` via a JSON LLM model. It returns a massive `context` JSON object.
- **Every subsequent tool** (`generate_readme`, `generate_visuals`, `package_output`) takes this `context` object as its input parameter. 

### Core Modules:
- `ui/app.py`: The Gradio web interface providing a real-time streaming dashboard for users.
- `server.py`: The FastMCP entry point that exposes the underlying tools.
- `github_tools.py`: Handles deep repo fetching, extension counting, smart 5-step fallback deployment URL detection, and PR creation.
- `llm_tools.py`: Wraps LiteLLM to analyze the code and generate copy. Uses a **Dual-LLM Architecture**: a strict JSON model (`JSON_MODEL`) for structured output, and a high-context reasoning model (`LLM_MODEL` with max_tokens=8000) for prose generation.
- `visual_tools.py`: Generates Plotly charts, Pillow social cards, and Playwright screenshots.
- `content_tools.py`: Generates Marp markdown presentations and ROADMAP.md files.
- `package_tools.py`: Bundles text and image paths into a `.zip` archive (safely handling nested JSON stringification).

## 🚦 Current Progress (ShipScript v2)
- `[x]` **Phase 1: Deep Intelligence.** Full codebase parsing with JS/Python dependency parsing and extension-based language inference.
- `[x]` **Phase 2: LLM Generation.** Dual-model architecture implemented for robust JSON extraction vs large-scale text generation.
- `[x]` **Phase 3: Visual Generation.** Upgraded to Plotly for sleek dark-themed charts and Pillow for platform-specific gradient social cards.
- `[x]` **Phase 4: Content & Packaging.** Generates Marp slides and roadmaps, safely bundled into ZIP files without dictionary memoryview crashes.
- `[x]` **Phase 5: User Interface.** Functional Gradio UI built and running at `http://localhost:7860`.
- `[ ]` **Phase 6: Polish & Demo.** The codebase is complete, but it should be tested against more complex apps (e.g. React apps) for the final hackathon demo.

## 🛠️ Setup Instructions for Teammates
1. Ensure Python 3.10+ is installed.
2. Install dependencies: `pip install -r requirements.txt`
3. Run `playwright install chromium` to fetch browser binaries for screenshots.
4. Create a `.env` file in the root of `shipscript` with the following variables:
   ```env
   # Model for prose (README, Roadmap, Slides)
   LLM_MODEL="ollama/qwen3-next:80b-cloud"
   
   # Model for structured output (Analysis, Social Posts)
   JSON_MODEL="ollama/gemma4:31b-cloud"
   
   # API Keys
   GITHUB_PAT="<your-github-personal-access-token-with-repo-scope>"
   VERCEL_TOKEN="<your-vercel-token>"
   ```
   *(Note: For production/demo day, you can switch the LLM models to `gpt-4o` and provide an `OPENAI_API_KEY`)*
5. Run `python ui/app.py` to start the Gradio dashboard locally.
6. Alternatively, run `python test_golden_path.py` to verify the pipeline headless.
