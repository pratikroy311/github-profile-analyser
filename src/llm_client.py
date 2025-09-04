import os
import json
from typing import List, Dict, Any

# Try to import google-generativeai but keep fallback if not installed.
try:
    import google.generativeai as genai  # type: ignore
    _GENAI_AVAILABLE = True
except Exception:
    _GENAI_AVAILABLE = False

PROMPT_TEMPLATE = """
You are an expert tech talent analyst. Return ONLY JSON with the following fields:
{
  "overall_summary": string,
  "key_languages_and_frameworks": [string],
  "tools_and_technologies": [string],
  "top_projects": [
    { "name": string, "url": string, "why_it_stands_out": string }
  ],
  "areas_of_expertise": [string]
}
INPUT_DATA:
{data}
"""

def generate_analysis(prepared_data: List[Dict[str, Any]], model_name: str = None, api_key: str = None) -> Dict[str, Any]:
    """
    Uses Gemini when available and configured. Otherwise returns a cheap local summary
    useful for development and testing.
    """
    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "")

    # If gemini client installed and key provided -> call it
    if _GENAI_AVAILABLE and api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        # Build prompt
        payload = PROMPT_TEMPLATE.format(data=json.dumps(prepared_data, ensure_ascii=False)[:180_000])
        # generation config tuned for structured output
        cfg = {
            "temperature": 0.2,
            "max_output_tokens": 1500,
            "top_p": 0.9,
            "response_mime_type": "application/json"
        }
        resp = model.generate_content(
            [
                {"role": "system", "parts": ["You are an expert tech talent analyst."]},
                {"role": "user", "parts": [payload]}
            ],
            generation_config=cfg
        )
        text = getattr(resp, "text", None) or ""
        # try parse JSON
        try:
            return json.loads(text)
        except Exception:
            # try to extract JSON substring
            import re
            m = re.search(r"\{.*\}$", text, flags=re.S)
            if m:
                return json.loads(m.group(0))
            raise RuntimeError("Could not parse JSON from LLM response")
    # Fallback: simple local heuristic (no API calls; great for dev)
    from .analyzer import cheap_local_summary
    return cheap_local_summary(prepared_data)
