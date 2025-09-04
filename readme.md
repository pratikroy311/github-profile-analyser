# AI GitHub Profile Analyzer

A Streamlit app that analyzes a GitHub profile (public repos + READMEs) and produces a concise summary of languages, tools, top projects and areas of expertise. Uses Google Gemini when configured; otherwise a local heuristic fallback is used.

## Quick start

1. Create & activate virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
