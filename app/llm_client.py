import os
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

class LLMClient:
    def __init__(self):
        self.provider = "openai" if OPENAI_API_KEY else ("ollama" if OLLAMA_BASE_URL else "none")

    async def acomplete(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai":
            return await self._openai_chat(system_prompt, user_prompt)
        elif self.provider == "ollama":
            return await self._ollama_chat(system_prompt, user_prompt)
        return "Não foi configurado um modelo de linguagem. Configure OPENAI_API_KEY ou OLLAMA_BASE_URL."

    async def _openai_chat(self, system_prompt: str, user_prompt: str) -> str:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _ollama_chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "").strip()
