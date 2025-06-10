# services/wordsapi_service.py
import httpx
import os
from typing import List, Dict

WORDSAPI_HOST = os.getenv("WORDSAPI_HOST", "wordsapiv1.p.rapidapi.com")
WORDSAPI_KEY = os.getenv("WORDSAPI_KEY")

async def fetch_definitions_from_wordsapi(term: str) -> List[Dict]:
    url = f"https://{WORDSAPI_HOST}/words/{term}"
    headers = {
        "X-RapidAPI-Host": WORDSAPI_HOST,
        "X-RapidAPI-Key": WORDSAPI_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            # Aquí está el fix
            definitions = data.get("definitions") or data.get("results", [])

            return [
                {
                    "meaning": d.get("definition", "").strip(),
                    "example": d.get("examples", [""])[0] if d.get("examples") else "",
                    "part_of_speech": d.get("partOfSpeech", "unknown"),
                    "usage_context": "general",
                    "is_idiomatic": False,
                    "synonyms": d.get("synonyms", []),
                    "source": "WordsAPI"
                }
                for d in definitions
                if d.get("definition")
            ]

    except Exception as e:
        print(f"❌ WordsAPI error for term '{term}': {e}")
        return []
