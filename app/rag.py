import os
import json
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from .llm_client import LLMClient

DATA_DIR = os.getenv("DATA_DIR", "data")

def _load_meta(path: str) -> List[Dict]:
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            recs.append(json.loads(line))
    return recs

class RAG:
    def __init__(self, data_dir: str = DATA_DIR, top_k: int = 6):
        self.data_dir = data_dir
        self.top_k = top_k
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.meta = _load_meta(os.path.join(data_dir, "meta.jsonl"))
        self.index = faiss.read_index(os.path.join(data_dir, "index.faiss"))
        self.llm = LLMClient()

    def retrieve(self, query: str) -> List[Tuple[float, Dict]]:
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores, idxs = self.index.search(q_emb, self.top_k)
        results = []
        for s, i in zip(scores[0], idxs[0]):
            if i == -1:
                continue
            results.append((float(s), self.meta[int(i)]))
        return results

    async def answer(self, question: str) -> Dict:
        hits = self.retrieve(question)
        if not hits:
            return {"answer": "Não encontrei essa informação no site da SIGNA. Sugiro contatar a SIGNA pelos contatos oficiais.", "sources": []}

        context_blocks = []
        dedup = set()
        sources = []
        for score, rec in hits:
            key = (rec["url"], rec["text"][:80])
            if key in dedup:
                continue
            dedup.add(key)
            context_blocks.append(f"- Fonte: {rec['url']}\n{rec['text']}")
            if rec["url"] not in sources:
                sources.append(rec["url"])

        system = (
            "Responde como um assistente da SIGNA. "
            "Usa APENAS a informação do CONTEXTO. Se a resposta não existir no contexto, diz claramente que não encontrou no site "
            "e sugere entrar em contato. Não incluas secções de fontes na resposta — as fontes já serão mostradas separadamente"
        )
        user = f"PERGUNTA: {question}\n\nCONTEXTO:\n" + "\n\n".join(context_blocks[:6])

        text = await self.llm.acomplete(system, user)
        if "Não foi configurado um modelo" in text:
            snippet = hits[0][1]["text"][:600]
            text = f"Resumo da fonte mais relevante:\n\n{snippet}\n\n(Fontes no fim)"
        return {"answer": text.strip(), "sources": sources}
