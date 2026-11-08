from typing import Protocol
from app.config import get_settings

class LLM_Error(Exception):
    """Gemini gagal dipanggil, mengembalikan respons yang tidak dipakai."""
    
class LLM_Not_Configured_Error(LLM_Error):
    """GEMINI_API_KEY belum diisi."""
    
class LLM_Client(Protocol):
    def generate_json(self, system_instruction: str, contents: str) -> str: ...
    
class Gemini_Client:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        
    def generate_json(self, system_instruction: str, contents: str) -> str:
        if not self._api_key:
            raise LLM_Not_Configured_Error("GEMINI_API_KEY belum diatur di environment.")

        # Import di dalam method: aplikasi & test tetap jalan walau SDK belum terpasang.
        from google import genai
        from google.genai import types

        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
        except Exception as exc:
            raise LLM_Error(f"Pemanggilan Gemini gagal: {type(exc).__name__}: {exc}") from exc

        text = response.text
        if not text:
            raise LLM_Error("Gemini mengembalikan respons kosong (mungkin diblokir safety filter).")
        return text

def get_llm_client() -> LLM_Client:
    """Dependency FastAPI. Di test, dependency ini di-override dengan FakeLLM."""
    s = get_settings()
    return Gemini_Client(api_key=s.gemini_api_key, model=s.gemini_model)
