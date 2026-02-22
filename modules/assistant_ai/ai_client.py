from __future__ import annotations
from typing import Any, Dict, Optional

def _get_openai_client():
    """
    Richiede: pip install openai
    Legge OPENAI_API_KEY da env o Streamlit Secrets.
    """
    from openai import OpenAI  # type: ignore
    return OpenAI()

def generate_relazione_json(
    model: str,
    system_instructions: str,
    user_prompt: str,
    response_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    client = _get_openai_client()

    kwargs: Dict[str, Any] = {
        "model": model,
        "instructions": system_instructions,
        "input": user_prompt,
    }
    if response_schema:
        kwargs["response_format"] = {"type": "json_schema", "json_schema": response_schema}

    resp = client.responses.create(**kwargs)  # type: ignore
    txt = getattr(resp, "output_text", None) or ""
    if not txt:
        try:
            txt = resp.output[0].content[0].text  # type: ignore
        except Exception:
            txt = "{}"
    import json
    return json.loads(txt)
