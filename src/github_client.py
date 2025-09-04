import base64
from typing import List, Dict, Any, Tuple
import requests

GITHUB_API = "https://api.github.com"

def parse_username(input_str: str) -> str:
    s = input_str.strip().rstrip("/")
    if "github.com/" in s:
        parts = s.split("github.com/")[-1].split("/")
        return parts[0]
    return s.split("/")[-1]

def _get(url: str, token: str = "", accept: str = "application/vnd.github+json", timeout: int = 30) -> Tuple[int, Any, dict]:
    headers = {
        "Accept": accept,
        "User-Agent": "github-profile-analyzer",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    try:
        payload = resp.json()
    except Exception:
        payload = resp.text
    return resp.status_code, payload, resp.headers

def fetch_readme(owner: str, repo: str, token: str = "") -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    status, data, _ = _get(url, token)
    if status != 200:
        return ""
    if isinstance(data, dict) and data.get("encoding") == "base64":
        try:
            return base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(data, str):
        return data
    return ""

def fetch_code_files(owner: str, repo: str, token: str = "", exts=None, max_files=3, max_lines=200) -> List[Dict[str, str]]:
    exts = exts or [".py", ".js", ".ts", ".html", ".ipynb", ".java"]
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents"
    status, contents, _ = _get(url, token)
    if status != 200 or not isinstance(contents, list):
        return []
    
    snippets = []
    count = 0
    for f in contents:
        if f["type"] == "file" and any(f["name"].endswith(e) for e in exts):
            s_status, s_content, _ = _get(f["download_url"], token)
            if s_status == 200 and isinstance(s_content, str):
                lines = "\n".join(s_content.splitlines()[:max_lines])
                snippets.append({"name": f["name"], "content": lines})
                count += 1
                if count >= max_files:
                    break
    return snippets

def fetch_repos(username: str, token: str = "") -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        url = f"{GITHUB_API}/users/{username}/repos?per_page={per_page}&page={page}&type=owner&sort=updated"
        status, data, _ = _get(url, token)
        if status == 404:
            raise ValueError("GitHub user not found")
        if status >= 400:
            raise RuntimeError(f"GitHub API error {status}: {data}")
        if not isinstance(data, list) or len(data) == 0:
            break

        for repo in data:
            readme = fetch_readme(username, repo.get("name"), token)
            code_snippets = fetch_code_files(username, repo.get("name"), token)
            repos.append({
                "name": repo.get("name"),
                "html_url": repo.get("html_url"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "description": repo.get("description") or "",
                "topics": repo.get("topics", []),
                "license": (repo.get("license") or {}).get("spdx_id"),
                "pushed_at": repo.get("pushed_at"),
                "_readme": readme,
                "_code_snippets": code_snippets,
                "fork": repo.get("fork", False)
            })

        if len(data) < per_page:
            break
        page += 1

    return repos
