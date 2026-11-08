from app.config import get_settings
from app.services.gemini import get_llm_client

s = get_settings()
print("Model dipakai:", s.gemini_model, "| API key terisi:", bool(s.gemini_api_key))
try:
    out = get_llm_client().generate_json(
        "Balas hanya dengan JSON.",
        'Balas dengan JSON ini: {"movie_id": 1, "reasoning": "tes"}',
    )
    print("BERHASIL ->", out)
except Exception as e:
    print("GAGAL ->", type(e).__name__, e)
    if e.__cause__:
        print("PENYEBAB ->", repr(e.__cause__))