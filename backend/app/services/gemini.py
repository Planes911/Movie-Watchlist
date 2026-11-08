"""Thin wrapper around the Google Gemini API.

Kept separate from the recommendation logic so tests can swap in a fake client (no network,
no quota) and the LLM provider could be replaced by editing this file alone.
"""

from typing import Protocol
from app.config import get_settings

class LLM_Error(Exception):
    """The Gemini call failed or returned an unusable response."""
    
class LLM_Not_Configured_Error(LLM_Error):
    """GEMINI_API_KEY is not set."""
    
class LLM_Client(Protocol):
    """Anything that can turn a prompt into a JSON string.

    Gemini_Client implements it in production; tests use a fake.
    """
    def generate_json(self, system_instruction: str, contents: str) -> str: ...
    
class Gemini_Client:
    """Calls Gemini in JSON mode and returns the raw JSON text."""
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        
    def generate_json(self, system_instruction: str, contents: str) -> str:
        if not self._api_key:
            raise LLM_Not_Configured_Error("GEMINI_API_KEY belum diatur di environment.")

        # Imported lazily so the app and the tests still work when the SDK is not installed.
        from google import genai
        from google.genai import types

        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    # JSON mode: the model must answer with valid JSON and no surrounding prose.
                    response_mime_type="application/json",
                    # Low temperature gives more consistent answers that stick to the provided catalogue.
                    temperature=0.3,
                ),
            )
        except Exception as exc:
            # Network errors, quota (429), an invalid key or a wrong model name all map to one domain error.
            raise LLM_Error(f"Pemanggilan Gemini gagal: {type(exc).__name__}: {exc}") from exc

        text = response.text
        # Empty text can happen when the safety filter blocks the answer.
        if not text:
            raise LLM_Error("Gemini mengembalikan respons kosong (mungkin diblokir safety filter).")
        return text

def get_llm_client() -> LLM_Client:
    """FastAPI dependency. Tests override it with a fake LLM client."""
    s = get_settings()
    return Gemini_Client(api_key=s.gemini_api_key, model=s.gemini_model)
