from typing import List, Dict, Any

MAX_README_CHARS = 60_000
TOOL_KEYWORDS = [
    "docker", "github actions", "circleci", "travis", "firebase", "aws", "gcp",
    "fastapi", "flask", "django", "react", "tailwind", "typescript",
    "pandas", "numpy", "scrapy", "mongodb", "angular", "html", "css", "vue"
]

def select_top_repos(repos: List[Dict[str, Any]], strategy: str = "stars", limit: int = 20) -> List[Dict[str, Any]]:
    repos = [r for r in repos if not r.get("fork", False)]
    if strategy == "stars":
        repos.sort(key=lambda r: r.get("stars", 0), reverse=True)
    elif strategy == "recent":
        repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)
    else:
        repos.sort(key=lambda r: (r.get("stars", 0), r.get("forks", 0)), reverse=True)
    return repos[:limit]

def prepare_input_for_llm(owner: str, repo_objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in repo_objs:
        readme = r.get("_readme", "") or ""
        code_text = "\n".join([c["content"] for c in r.get("_code_snippets", [])])
        combined_content = (r.get("description") or "") + "\n\n" + readme[:MAX_README_CHARS] + "\n\n" + code_text
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
            "code_snippets": r.get("_code_snippets", []),
            "content": combined_content
        })
    return out

def cheap_local_summary(prepared: List[Dict[str, Any]]) -> dict:
    languages = {}
    tools = set()
    for p in prepared:
        lang = p.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        text_blob = (p.get("description", "") + " " + p.get("readme", "") +
                     " " + "\n".join([c["content"] for c in p.get("code_snippets", [])])).lower()
        for t in TOOL_KEYWORDS:
            if t in text_blob:
                tools.add(t)

    top_projects = sorted(prepared, key=lambda x: x.get("stars", 0), reverse=True)[:3]

    # Construct a professional summary
    langs_list = sorted(languages.keys(), key=lambda k: -languages[k])
    role_suggestion = "Software Engineer"
    if any(l in langs_list for l in ["python", "pandas", "numpy", "scikit-learn"]):
        role_suggestion = "Data Scientist"
    elif any(l in langs_list for l in ["react", "angular", "vue", "javascript", "typescript"]):
        role_suggestion = "Full Stack Developer"
    elif any(l in langs_list for l in ["java", "c++", "c#"]):
        role_suggestion = "Backend Developer"

    overall_summary = f"The developer has extensive experience in {', '.join(langs_list[:8])}. This suggests the developer is a {role_suggestion}."

    return {
        "overall_summary": overall_summary,
        "key_languages_and_frameworks": langs_list[:8],
        "tools_and_technologies": sorted(list(tools))[:15],
        "top_projects": [
            {"name": p["name"], "url": p["html_url"], "why_it_stands_out": f"{p['stars']} stars, language: {p.get('language')}, appears complete and has clear use case"}
            for p in top_projects[:1]  # Show top project only as most complete
        ],
        "areas_of_expertise": [role_suggestion]
    }
