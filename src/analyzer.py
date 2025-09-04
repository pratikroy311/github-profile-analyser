from typing import List, Dict, Any

MAX_README_CHARS = 60_000
TOOL_KEYWORDS = [
    "docker", "github actions", "circleci", "travis", "firebase", "aws", "gcp",
    "fastapi", "flask", "django", "react", "tailwind", "typescript",
    "pandas", "numpy", "scrapy"
]

def select_top_repos(repos: List[Dict[str, Any]], strategy: str = "stars", limit: int = 20) -> List[Dict[str, Any]]:
    """Filter forks and select top repos based on strategy"""
    repos = [r for r in repos if not r.get("fork", False)]
    if strategy == "stars":
        repos.sort(key=lambda r: r.get("stars", 0), reverse=True)
    elif strategy == "recent":
        repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)
    else:
        repos.sort(key=lambda r: (r.get("stars", 0), r.get("forks", 0)), reverse=True)
    return repos[:limit]

def prepare_input_for_llm(owner: str, repo_objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize repo data and combine description + README for LLM"""
    out = []
    for r in repo_objs:
        readme = r.get("_readme", "") or ""
        combined_content = (r.get("description") or "") + "\n\n" + readme[:MAX_README_CHARS]
        out.append({
            "name": r.get("name"),
            "html_url": r.get("html_url"),
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "stars": r.get("stars", 0),
            "forks": r.get("forks", 0),
            "topics": r.get("topics", []),
            "license": r.get("license"),
            "pushed_at": r.get("pushed_at"),
            "readme": readme[:MAX_README_CHARS],
            "content": combined_content
        })
    return out

def cheap_local_summary(prepared: List[Dict[str, Any]]) -> dict:
    """Fallback offline summarizer using stars, description, README keywords"""
    languages = {}
    tools = set()
    for p in prepared:
        lang = p.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        text_blob = (p.get("description", "") + " " + p.get("readme", "")).lower()
        for t in TOOL_KEYWORDS:
            if t in text_blob:
                tools.add(t)

    top_projects = sorted(prepared, key=lambda x: x.get("stars", 0), reverse=True)[:3]
    return {
        "overall_summary": f"Developer with {len(prepared)} public projects. Top languages: {', '.join(sorted(languages.keys(), key=lambda k: -languages[k])[:5]) or 'Unknown'}.",
        "key_languages_and_frameworks": list(sorted(languages.keys(), key=lambda k: -languages[k]))[:8],
        "tools_and_technologies": sorted(list(tools))[:15],
        "top_projects": [
            {"name": p["name"], "url": p["html_url"], "why_it_stands_out": f"{p['stars']} stars, language: {p.get('language')}"}
            for p in top_projects
        ],
        "areas_of_expertise": ["/".join([k for k in sorted(languages.keys(), key=lambda k: -languages[k])[:2]])] if languages else []
    }
