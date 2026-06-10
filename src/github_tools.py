import os
import base64
import uuid
from typing import Dict, Any
from github import Github, Auth, GithubException
from urllib.parse import urlparse

# Size guard constants
MAX_FILES_TO_FETCH = 20
ALLOWED_EXTENSIONS = {'.md', '.txt', '.json', '.toml', '.yml', '.yaml', '.py', '.js', '.ts', '.jsx', '.tsx'}
ROOT_CONFIG_FILES = {'package.json', 'requirements.txt', 'pyproject.toml', 'dockerfile', 'docker-compose.yml', 'vercel.json'}

def get_github_client() -> Github:
    """Initialize GitHub client using PAT if available."""
    token = os.environ.get("GITHUB_PAT")
    if token:
        auth = Auth.Token(token)
        return Github(auth=auth)
    return Github()

def parse_repo_url(repo_url: str) -> str:
    """Extract owner/repo from URL."""
    path = urlparse(repo_url).path.strip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    raise ValueError("Invalid GitHub repository URL")

def fetch_repo_context(repo_url: str) -> Dict[str, Any]:
    """
    Fetch repository metadata, README, and key files with a size guard.
    Returns a clean context JSON.
    """
    g = get_github_client()
    repo_name = parse_repo_url(repo_url)
    repo = g.get_repo(repo_name)
    
    context = {
        "url": repo_url,
        "name": repo.full_name,
        "description": repo.description,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "language": repo.language,
        "homepage": repo.homepage,
        "languages": {},
        "topics": [],
        "readme": "",
        "key_files": {}
    }
    
    try:
        context["languages"] = repo.get_languages()
    except Exception:
        pass
        
    try:
        context["topics"] = repo.get_topics()
    except Exception:
        pass
    
    # Fetch README
    try:
        readme = repo.get_readme()
        context["readme"] = base64.b64decode(readme.content).decode('utf-8', errors='replace')
    except Exception:
        context["readme"] = "No README found."

    # Smart file picker (Size Guard)
    # We will traverse the root and optionally the src/ directory up to MAX_FILES_TO_FETCH
    try:
        contents = repo.get_contents("")
        files_fetched = 0
        
        while contents and files_fetched < MAX_FILES_TO_FETCH:
            file_content = contents.pop(0)
            
            if file_content.type == "dir":
                # Only explore 'src', 'app', 'lib', 'docs' top-level directories to keep it bounded
                if file_content.name.lower() in {'src', 'app', 'lib', 'docs'}:
                    try:
                        dir_contents = repo.get_contents(file_content.path)
                        if len(contents) < 100:
                            contents.extend(dir_contents)
                    except Exception:
                        pass
            else:
                name_lower = file_content.name.lower()
                ext = os.path.splitext(name_lower)[1]
                
                # Fetch if it's a root config or allowed source extension
                is_root_config = name_lower in ROOT_CONFIG_FILES and file_content.path == file_content.name
                is_allowed_src = ext in ALLOWED_EXTENSIONS
                
                if is_root_config or is_allowed_src:
                    try:
                        decoded_content = base64.b64decode(file_content.content).decode('utf-8', errors='replace')
                        # Truncate file content if it's too huge just in case (e.g. 10KB max per file)
                        if len(decoded_content) > 10000:
                            decoded_content = decoded_content[:10000] + "\n...[TRUNCATED]"
                        context["key_files"][file_content.path] = decoded_content
                        files_fetched += 1
                    except Exception:
                        pass
    except Exception as e:
        print(f"Warning fetching files: {e}")

    return context

def create_readme_pr(repo_url: str, readme_content: str, github_pat: str) -> dict:
    """
    Creates a new branch and opens a PR with the updated README.md.
    """
    try:
        auth = Auth.Token(github_pat)
        g = Github(auth=auth)
        repo_name = parse_repo_url(repo_url)
        repo = g.get_repo(repo_name)
        
        # Check permissions by attempting to get the default branch
        default_branch = repo.default_branch
        sb = repo.get_branch(default_branch)
        
        new_branch_name = f"shipscript-readme-update-{uuid.uuid4().hex[:6]}"
        
        try:
            repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=sb.commit.sha)
        except GithubException as e:
            if e.status == 403 or e.status == 404:
                return {"status": "error", "message": "GitHub token lacks write permissions. Need 'repo' scope."}
            raise e
            
        # Create or update README.md
        try:
            contents = repo.get_contents("README.md", ref=new_branch_name)
            repo.update_file(contents.path, "Update README.md via ShipScript", readme_content, contents.sha, branch=new_branch_name)
        except GithubException as e:
            if e.status == 404:
                # File does not exist, create it
                repo.create_file("README.md", "Create README.md via ShipScript", readme_content, branch=new_branch_name)
            else:
                raise e
                
        # Create PR
        pr = repo.create_pull(
            title="✨ ShipScript: Enhanced README.md",
            body="This PR was automatically generated by ShipScript to improve the repository documentation.",
            head=new_branch_name,
            base=default_branch
        )
        
        return {"status": "success", "pr_url": pr.html_url, "branch": new_branch_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}
