import os
import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from .github_client import parse_username, fetch_repos
from .analyzer import select_top_repos, prepare_input_for_llm
from .llm_client import generate_analysis

load_dotenv()

def run_app():
    st.set_page_config(page_title="AI GitHub Profile Analyzer", layout="wide")
    st.title("🔎 AI GitHub Profile Analyzer")
    st.caption("Paste a GitHub profile URL or username, then click Analyze.")

    with st.sidebar:
        st.header("Config")
        username_input = st.text_input("GitHub username or profile URL", placeholder="https://github.com/torvalds")
        strategy = st.selectbox("Select repos by", ["stars", "recent", "stars_and_forks"])
        limit = st.slider("Max repos to analyze", 5, 40, 20)
        st.markdown("**API keys** (optional; recommended)")
        gh_token_override = st.text_input("GitHub Token (optional)", type="password", value=os.getenv("GITHUB_TOKEN", ""))
        gemini_key_override = st.text_input("Gemini API Key (optional)", type="password", value=os.getenv("GEMINI_API_KEY", ""))
        run_button = st.button("Analyze Profile")

    if not run_button:
        st.info("Enter a username and click Analyze Profile")
        return

    if not username_input.strip():
        st.error("Please provide a GitHub username or profile URL.")
        return

    username = parse_username(username_input)
    st.markdown(f"### Analyzing: **{username}**")

    # Fetch repos
    repos = st.cache_data(fetch_repos, show_spinner=False)(username, gh_token_override)
    if not repos:
        st.warning("No public repos found for user.")
        return

    chosen = select_top_repos(repos, strategy=strategy, limit=limit)

    # Show quick summary table
    df = pd.DataFrame([{
        "name": r.get("name"),
        "language": r.get("language"),
        "stars": r.get("stars"),
        "forks": r.get("forks"),
        "updated": r.get("pushed_at"),
        "url": r.get("html_url")
    } for r in chosen])
    st.subheader("Selected repositories")
    st.dataframe(df, use_container_width=True)

    # Prepare data for LLM
    st.subheader("Preparing data for analysis (including descriptions, README & code snippets)…")
    prepared_for_llm = prepare_input_for_llm(username, chosen)

    st.subheader("Analyzing profile with AI…")
    with st.spinner("Generating analysis..."):
        analysis = generate_analysis(
            prepared_for_llm,
            model_name=os.getenv("GEMINI_MODEL"),
            api_key=gemini_key_override or os.getenv("GEMINI_API_KEY")
        )

    st.success("✅ Analysis ready")

    # Highlight developer role
    role = analysis.get("areas_of_expertise", ["Software Engineer"])[0]
    st.markdown(f"## 👤 Suggested Role: **{role}**")

    # Overall summary
    st.markdown("### 📋 Overall Summary")
    st.write(analysis.get("overall_summary", "(no summary returned)"))

    # Languages & Tools
    cols = st.columns(2)
    with cols[0]:
        st.markdown("### 💻 Languages & Frameworks")
        for item in analysis.get("key_languages_and_frameworks", []):
            st.write(f"- {item}")
    with cols[1]:
        st.markdown("### 🛠️ Tools & Technologies")
        for item in analysis.get("tools_and_technologies", []):
            st.write(f"- {item}")

    # Top project highlighted
    top_projects = analysis.get("top_projects", [])
    if top_projects:
        st.markdown("### ⭐ Top Project")
        p = top_projects[0]
        name = p.get("name")
        url = p.get("url")
        why = p.get("why_it_stands_out", "")
        st.markdown(f"**[{name}]({url})**  \n{why}")

    # Raw JSON output (optional)
    with st.expander("Raw model output (JSON)"):
        st.code(json.dumps(analysis, indent=2, ensure_ascii=False))
