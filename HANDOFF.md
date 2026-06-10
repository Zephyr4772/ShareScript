# ShipScript: Master Handoff Document

> [!IMPORTANT]
> **To any AI Agent (Antigravity/Claude/etc) reading this file:** 
> This is the state of the ShipScript codebase. Your goal is to help the team finish Phase 5, connect the MCP server to Copilot Studio, and polish the final hackathon demo. Read the architecture and progress below before writing any code.

## 🚀 The Concept
**ShipScript** is an MCP server built for the Microsoft Agents League Hackathon ("Marketing & Launch-as-a-Service for Developers"). 
Given a single GitHub repository URL, it acts as a reasoning agent that:
1. Understands the codebase and what problem it solves.
2. Generates an improved README and automatically opens a GitHub PR.
3. Captures screenshots of the deployed project.
4. Generates visual charts (Tech Stack, Language Breakdown).
5. Writes social media posts (LinkedIn, Twitter, Dev.to).
6. Packages everything into a clean `.zip` file for the developer to download.

## 🏆 Hackathon Alignment
- **Track:** Designed primarily for **Reasoning Agents** or **Enterprise Agents**.
- **Microsoft Tool Requirement:** We fulfill this in two ways:
  1. The agent logic relies strictly on **Azure OpenAI** (satisfying the Foundry IQ requirement).
  2. The tools are exposed via an **MCP Server** (`FastMCP`), which is designed to be natively imported into **Microsoft Copilot Studio**.

## 🏗️ Architecture & Tool Signatures
The system is built on Python and `FastMCP`. 
**Crucial State Model:** To prevent constantly hitting the GitHub API, state is passed forward. 
- `analyze_repo` runs *once*, fetching the codebase and generating an `enriched_analysis` via LLM. It returns a massive `context` JSON object.
- **Every subsequent tool** (`generate_readme`, `generate_visuals`, `package_output`) takes this `context` object as its input parameter. 

### Core Modules:
- `server.py`: The FastMCP entry point that exposes the tools.
- `github_tools.py`: Handles repo fetching (with strict size guards to avoid blowing the context window) and opening PRs.
- `llm_tools.py`: Wraps Azure OpenAI to analyze the code and generate copy.
- `visual_tools.py`: Generates Matplotlib charts and Playwright screenshots, returning temporary file paths.
- `package_tools.py`: Bundles text and image paths into a `.zip` archive.

## 🚦 Current Progress
- `[x]` **Phase 1: Repo Intelligence.** Codebase fetching with a smart file-picker queue cap.
- `[x]` **Phase 2: LLM Generation & PRs.** Azure OpenAI integration, README generation, and GitHub PR creation logic (with 403 fallback).
- `[x]` **Phase 3: Visual Generation.** Matplotlib donut charts/badges, and Playwright screenshot fallback logic.
- `[x]` **Phase 4: Packaging.** ZIP creation working perfectly.
- `[ ]` **Phase 5: Copilot Studio Integration & Polish.** The codebase is complete, but it needs to be tested with real Azure keys, hooked into Copilot Studio via the MCP bridge, and fine-tuned for the 3-minute demo video.

## 🛠️ Setup Instructions for Teammates
1. Ensure Python 3.10+ is installed.
2. Run `setup.bat` (Windows) to install `requirements.txt` and the Playwright Chromium binaries.
3. Create a `.env` file in the root of `shipscript` with the following variables:
   ```env
   # The model to use (e.g. "gpt-4o", "gemini/gemini-1.5-flash", "ollama/llama3")
   LLM_MODEL="gemini/gemini-1.5-flash"
   
   # Add the key for whatever provider you chose:
   GEMINI_API_KEY="<your-gemini-key>"
   # OPENAI_API_KEY="sk-<your-openai-api-key>"
   
   GITHUB_PAT="<your-github-personal-access-token-with-repo-scope>"
   ```
4. Run `python test_golden_path.py` to verify the pipeline works end-to-end.
5. Run `python src/server.py` to start the FastMCP server for Copilot Studio.
