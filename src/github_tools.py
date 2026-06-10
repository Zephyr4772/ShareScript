import os
import base64
import uuid
import json
import re
import requests
from typing import Dict, Any, Optional, List, Tuple
from github import Github, Auth, GithubException
from urllib.parse import urlparse

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILES_TO_FETCH = 35
ALLOWED_EXTENSIONS = {
    '.md', '.txt', '.json', '.toml', '.yml', '.yaml',
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.rs', '.go', '.java', '.cs', '.rb', '.php',
    '.vue', '.svelte', '.astro',
}
PRIORITY_CONFIG_FILES = {
    'package.json', 'requirements.txt', 'pyproject.toml',
    'cargo.toml', 'go.mod', 'gemfile',
    'dockerfile', 'docker-compose.yml',
    'vercel.json', 'netlify.toml', '.vercelignore',
    'vite.config.ts', 'vite.config.js',
    'next.config.js', 'next.config.ts', 'next.config.mjs',
    'tailwind.config.js', 'tailwind.config.ts',
    '.env.example', 'readme.md',
}
DIRS_TO_EXPLORE = {'src', 'app', 'lib', 'pages', 'components', 'api', 'server', 'backend', 'frontend', 'core'}

# Framework fingerprints — maps package name → framework label
JS_FRAMEWORK_DEPS = {
    'react': 'React',
    'react-dom': 'React',
    'next': 'Next.js',
    'vue': 'Vue.js',
    'nuxt': 'Nuxt.js',
    '@angular/core': 'Angular',
    'svelte': 'Svelte',
    '@sveltejs/kit': 'SvelteKit',
    'astro': 'Astro',
    'vite': 'Vite',
    'express': 'Express.js',
    'fastify': 'Fastify',
    'tailwindcss': 'Tailwind CSS',
    '@chakra-ui/react': 'Chakra UI',
    '@mui/material': 'Material UI',
    'prisma': 'Prisma',
    '@prisma/client': 'Prisma',
    'mongoose': 'MongoDB/Mongoose',
    '@supabase/supabase-js': 'Supabase',
    'firebase': 'Firebase',
    'graphql': 'GraphQL',
    'trpc': 'tRPC',
    '@trpc/server': 'tRPC',
    'zustand': 'Zustand',
    'redux': 'Redux',
    '@reduxjs/toolkit': 'Redux Toolkit',
    'react-query': 'React Query',
    '@tanstack/react-query': 'TanStack Query',
    'axios': 'Axios',
    'typescript': 'TypeScript',
    'electron': 'Electron',
    'socket.io': 'Socket.io',
}

PY_FRAMEWORK_KEYWORDS = {
    'fastapi': 'FastAPI',
    'django': 'Django',
    'flask': 'Flask',
    'streamlit': 'Streamlit',
    'gradio': 'Gradio',
    'torch': 'PyTorch',
    'pytorch': 'PyTorch',
    'tensorflow': 'TensorFlow',
    'keras': 'Keras',
    'scikit-learn': 'scikit-learn',
    'sklearn': 'scikit-learn',
    'pandas': 'Pandas',
    'numpy': 'NumPy',
    'sqlalchemy': 'SQLAlchemy',
    'celery': 'Celery',
    'pydantic': 'Pydantic',
    'langchain': 'LangChain',
    'openai': 'OpenAI SDK',
    'anthropic': 'Anthropic SDK',
}

EXT_TO_LANGUAGE = {
    '.tsx': 'TypeScript', '.ts': 'TypeScript',
    '.jsx': 'JavaScript', '.js': 'JavaScript',
    '.py': 'Python', '.rs': 'Rust', '.go': 'Go',
    '.java': 'Java', '.cs': 'C#', '.rb': 'Ruby',
    '.php': 'PHP', '.vue': 'Vue', '.svelte': 'Svelte',
}

# ── GitHub Client ─────────────────────────────────────────────────────────────

def get_github_client() -> Github:
    token = os.environ.get("GITHUB_PAT")
    if token:
        return Github(auth=Auth.Token(token))
    return Github()

def parse_repo_url(repo_url: str) -> str:
    path = urlparse(repo_url).path.strip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

# ── Framework Detection ───────────────────────────────────────────────────────

def detect_js_frameworks(pkg_json_str: str) -> Tuple[List[str], List[str]]:
    """Returns (detected_framework_labels, all_dep_names)."""
    try:
        pkg = json.loads(pkg_json_str)
    except Exception:
        return [], []

    all_deps: Dict[str, str] = {}
    all_deps.update(pkg.get('dependencies', {}))
    all_deps.update(pkg.get('devDependencies', {}))
    all_deps.update(pkg.get('peerDependencies', {}))

    seen = set()
    frameworks = []
    for dep_name in all_deps:
        label = JS_FRAMEWORK_DEPS.get(dep_name)
        if label and label not in seen:
            frameworks.append(label)
            seen.add(label)

    return frameworks, list(all_deps.keys())


def detect_py_frameworks(req_str: str) -> List[str]:
    """Detect Python frameworks from requirements.txt / pyproject.toml text."""
    req_lower = req_str.lower()
    seen = set()
    frameworks = []
    for keyword, label in PY_FRAMEWORK_KEYWORDS.items():
        if keyword in req_lower and label not in seen:
            frameworks.append(label)
            seen.add(label)
    return frameworks


def count_extensions(file_paths: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext:
            counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def infer_language_from_extensions(ext_counts: Dict[str, int]) -> Optional[str]:
    for ext, _ in ext_counts.items():
        if ext in EXT_TO_LANGUAGE:
            return EXT_TO_LANGUAGE[ext]
    return None

# ── Deployment URL Detection ──────────────────────────────────────────────────

def _ping(url: str, timeout: int = 6) -> bool:
    """Returns True if the URL responds with HTTP < 400."""
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True,
                          headers={'User-Agent': 'ShipScript/2.0'})
        return r.status_code < 400
    except Exception:
        return False


def find_deployment_url(repo, context: dict, owner: str, repo_name: str) -> Tuple[Optional[str], str]:
    """
    Full fallback chain — returns (url_or_None, source_description).

    Chain:
    1. repo.homepage field (verified)
    2. Vercel API via VERCEL_TOKEN
    3. vercel.json present → ping common vercel.app patterns
    4. GitHub Releases body → scan for live URLs
    5. HTTP ping: vercel.app / netlify.app / github.io variants
    6. Give up → return (None, 'not_found')
    """
    # 1. Repo homepage
    if repo.homepage and repo.homepage.startswith('http'):
        if _ping(repo.homepage):
            return repo.homepage, 'repo_homepage'

    # 2. Vercel API
    vercel_token = os.environ.get('VERCEL_TOKEN', '').strip()
    if vercel_token and vercel_token != 'PASTE_YOUR_VERCEL_TOKEN_HERE':
        try:
            r = requests.get(
                'https://api.vercel.com/v6/deployments',
                headers={'Authorization': f'Bearer {vercel_token}'},
                params={'limit': 10, 'state': 'READY'},
                timeout=10,
            )
            if r.status_code == 200:
                for dep in r.json().get('deployments', []):
                    raw_url = dep.get('url', '')
                    if not raw_url:
                        continue
                    full = f"https://{raw_url}" if not raw_url.startswith('http') else raw_url
                    # Match by repo name in the URL
                    if repo_name.lower().replace('-', '') in full.lower().replace('-', ''):
                        if _ping(full):
                            return full, 'vercel_api'
        except Exception as e:
            print(f"Vercel API lookup failed: {e}")

    # 3. vercel.json in repo
    if 'vercel.json' in context.get('key_files', {}):
        candidates = [
            f"https://{repo_name}.vercel.app",
            f"https://{repo_name}-{owner.lower()}.vercel.app",
            f"https://{owner.lower()}-{repo_name}.vercel.app",
        ]
        for url in candidates:
            if _ping(url):
                return url, 'vercel_json_detected'

    # 4. GitHub Releases — scan body text for https:// URLs
    try:
        releases = list(repo.get_releases())[:5]
        for release in releases:
            body = release.body or ''
            urls = re.findall(r'https?://[^\s\)\]\'"<>]+', body)
            for url in urls:
                url = url.rstrip('.,')
                if any(p in url for p in ['vercel.app', 'netlify.app', '.io', '.com', '.dev']):
                    if _ping(url):
                        return url, f'github_release_{release.tag_name}'
    except Exception:
        pass

    # 5. HTTP ping common patterns
    patterns = [
        f"https://{repo_name}.vercel.app",
        f"https://{repo_name}-app.vercel.app",
        f"https://{owner.lower()}-{repo_name}.vercel.app",
        f"https://{repo_name}.netlify.app",
        f"https://{owner.lower()}.github.io/{repo_name}",
        f"https://{repo_name}.pages.dev",
    ]
    for url in patterns:
        if _ping(url):
            return url, 'http_ping'

    return None, 'not_found'

# ── Main Fetch ────────────────────────────────────────────────────────────────

def fetch_repo_context(repo_url: str, user_deployment_url: str = None) -> Dict[str, Any]:
    """
    Fetch deep repo context: metadata, README, key files, framework detection,
    language inference, and verified deployment URL.
    """
    g = get_github_client()
    repo_full_name = parse_repo_url(repo_url)
    repo = g.get_repo(repo_full_name)
    owner, repo_name = repo_full_name.split('/', 1)

    context: Dict[str, Any] = {
        "url": repo_url,
        "name": repo.full_name,
        "description": repo.description or "",
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "language": repo.language,
        "homepage": repo.homepage or "",
        "languages": {},
        "topics": [],
        "readme": "",
        "key_files": {},
        # v2 enrichment
        "detected_frameworks": [],
        "all_dependencies": [],
        "file_extension_counts": {},
        "deployment_url": None,
        "deployment_url_source": "not_found",
    }

    # Languages from GitHub API
    try:
        context["languages"] = repo.get_languages()
    except Exception:
        pass

    # Topics
    try:
        context["topics"] = repo.get_topics()
    except Exception:
        pass

    # README
    try:
        readme_file = repo.get_readme()
        context["readme"] = base64.b64decode(readme_file.content).decode('utf-8', errors='replace')
    except Exception:
        context["readme"] = ""

    # ── Deep file traversal ──────────────────────────────────────────────────
    all_paths: List[str] = []
    try:
        queue = list(repo.get_contents(""))
        files_fetched = 0

        while queue and files_fetched < MAX_FILES_TO_FETCH:
            item = queue.pop(0)

            if item.type == "dir":
                if item.name.lower() in DIRS_TO_EXPLORE:
                    try:
                        children = repo.get_contents(item.path)
                        if len(queue) < 200:
                            queue.extend(children)
                    except Exception:
                        pass
                continue

            all_paths.append(item.path)
            name_lower = item.name.lower()
            ext = os.path.splitext(name_lower)[1]
            is_priority = name_lower in PRIORITY_CONFIG_FILES
            is_source = ext in ALLOWED_EXTENSIONS

            if (is_priority or is_source) and item.size < 120_000:
                try:
                    raw = base64.b64decode(item.content).decode('utf-8', errors='replace')
                    if len(raw) > 15_000:
                        raw = raw[:15_000] + "\n...[TRUNCATED]"
                    context["key_files"][item.path] = raw
                    files_fetched += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"Warning during file traversal: {e}")

    # ── Extension counting + language inference ──────────────────────────────
    context["file_extension_counts"] = count_extensions(all_paths)

    if not context["language"]:
        context["language"] = infer_language_from_extensions(context["file_extension_counts"])

    # If GitHub returned no language breakdown, synthesize from extensions
    if not context["languages"] and context["language"]:
        # Use extension counts to approximate percentages
        ext_langs = {EXT_TO_LANGUAGE.get(ext, ext): cnt
                     for ext, cnt in context["file_extension_counts"].items()
                     if ext in EXT_TO_LANGUAGE}
        context["languages"] = ext_langs if ext_langs else {context["language"]: 100}

    # ── Framework detection ──────────────────────────────────────────────────
    # JS/TS projects
    pkg_json = context["key_files"].get("package.json") or \
               next((v for k, v in context["key_files"].items() if k.endswith("package.json")), None)
    if pkg_json:
        js_frameworks, deps = detect_js_frameworks(pkg_json)
        context["detected_frameworks"].extend(js_frameworks)
        context["all_dependencies"] = deps

    # Python projects
    req_txt = context["key_files"].get("requirements.txt") or \
              next((v for k, v in context["key_files"].items() if k.endswith("requirements.txt")), None)
    if req_txt:
        context["detected_frameworks"].extend(detect_py_frameworks(req_txt))

    pyproject = context["key_files"].get("pyproject.toml") or \
                next((v for k, v in context["key_files"].items() if k.endswith("pyproject.toml")), None)
    if pyproject:
        context["detected_frameworks"].extend(detect_py_frameworks(pyproject))

    # Deduplicate
    context["detected_frameworks"] = list(dict.fromkeys(context["detected_frameworks"]))

    # ── Deployment URL ───────────────────────────────────────────────────────
    if user_deployment_url and user_deployment_url.strip():
        context["deployment_url"] = user_deployment_url.strip()
        context["deployment_url_source"] = "user_provided"
    else:
        url, source = find_deployment_url(repo, context, owner, repo_name)
        context["deployment_url"] = url
        context["deployment_url_source"] = source

    return context


# ── PR Creation ───────────────────────────────────────────────────────────────

def create_readme_pr(repo_url: str, readme_content: str, github_pat: str) -> dict:
    """Creates a branch and opens a PR with the updated README.md."""
    try:
        g = Github(auth=Auth.Token(github_pat))
        repo_full = parse_repo_url(repo_url)
        repo = g.get_repo(repo_full)

        default_branch = repo.default_branch
        base_sha = repo.get_branch(default_branch).commit.sha
        branch_name = f"shipscript-readme-{uuid.uuid4().hex[:6]}"

        try:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        except GithubException as e:
            if e.status in (403, 404):
                return {"status": "error", "message": "Token lacks write (repo) scope."}
            raise

        try:
            existing = repo.get_contents("README.md", ref=branch_name)
            repo.update_file(existing.path, "docs: update README via ShipScript",
                             readme_content, existing.sha, branch=branch_name)
        except GithubException as e:
            if e.status == 404:
                repo.create_file("README.md", "docs: create README via ShipScript",
                                 readme_content, branch=branch_name)
            else:
                raise

        pr = repo.create_pull(
            title="✨ ShipScript: Enhanced README.md",
            body=(
                "## ShipScript Auto-generated README\n\n"
                "This PR was created automatically by [ShipScript](https://github.com/Zephyr4772/ShareScript) "
                "to improve repository documentation.\n\n"
                "Review the changes and merge when ready."
            ),
            head=branch_name,
            base=default_branch,
        )

        return {"status": "success", "pr_url": pr.html_url, "branch": branch_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
