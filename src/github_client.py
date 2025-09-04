import time
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
    """Return README text (decoded), empty string if none or error."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    status, data, headers = _get(url, token, accept="application/vnd.github+json")
    if status == 404 or status >= 400:
        return ""
    if isinstance(data, dict) and data.get("encoding") == "base64":
        try:
            return base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(data, str):
        return data
    return ""

def fetch_repos(username: str, token: str = "") -> List[Dict[str, Any]]:
    """
    Return list of normalized repo dicts including:
    name, stars, forks, language, description, topics, license, pushed_at, readme
    """
    repos: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        url = f"{GITHUB_API}/users/{username}/repos?per_page={per_page}&page={page}&type=owner&sort=updated"
        status, data, headers = _get(url, token)
        if status == 404:
            raise ValueError("GitHub user not found")
        if status >= 400:
            raise RuntimeError(f"GitHub API error {status}: {data}")
        if not isinstance(data, list) or len(data) == 0:
            break

        for repo in data:
            readme = fetch_readme(username, repo.get("name"), token)
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
                "fork": repo.get("fork", False)
            })

        if len(data) < per_page:
            break
        page += 1

    return repos
