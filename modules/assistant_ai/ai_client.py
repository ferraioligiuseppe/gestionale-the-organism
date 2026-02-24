from __future__ import annotations
from typing import Any, Dict, Optional

def _get_openai_client():
    """
    Lazy import per non rompere l'app se la libreria non è installata.
    Richiede: pip install openai
    Richiede API key in env/Streamlit Secrets: OPENAI_API_KEY
    """
    from openai import OpenAI  # type: ignore
    return OpenAI()

def generate_relazione_json(
    model: str,
    system_instructions: str,
    user_prompt: str,
    response_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Usa OpenAI Responses API e (opzionalmente) Structured Outputs via json_schema.
    """
    client = _get_openai_client()

    kwargs: Dict[str, Any] = {
        "model": model,
        "instructions": system_instructions,
        "input": user_prompt,
    }

    if response_schema:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }

    resp = client.responses.create(**kwargs)  # type: ignore
    # output_text contiene il JSON come stringa (se json_schema)
    txt = getattr(resp, "output_text", None) or ""
    if not txt:
        # fallback: prova a ricostruire da output
        try:
            txt = resp.output[0].content[0].text  # type: ignore
        except Exception:
            txt = "{}"

    import json
    return json.loads(txt)
