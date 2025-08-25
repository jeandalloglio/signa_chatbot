import os
import re
import json
import argparse
from urllib.parse import urljoin, urldefrag, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as html2md
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss

DOMAIN = "www.signa.pt"
BASE = f"https://{DOMAIN}/"

def clean_url(u: str) -> str:
    u, _ = urldefrag(u)
    return u

def is_allowed(u: str) -> bool:
    p = urlparse(u)
    if p.netloc != DOMAIN:
        return False
    bad = ["orcamento.asp", "login", "register", "top.asp"]
    if any(b in p.path.lower() for b in bad):
        return False
    return True

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for cls in ["footer", "navbar", "menu", "breadcrumb", "header"]:
        for el in soup.select(f".{cls}"):
            el.decompose()
    text_md = html2md(str(soup), strip=["img"])
    text_md = re.sub(r"\n{3,}", "\n\n", text_md)
    return text_md.strip()

def chunk_text(t: str, chunk_size: int, overlap: int):
    t = t.strip()
    if not t:
        return []
    chunks = []
    start = 0
    while start < len(t):
        end = min(len(t), start + chunk_size)
        c = t[start:end]
        if end < len(t):
            next_nl = t.find("\n\n", end)
            if next_nl != -1 and next_nl - end < 200:
                c = t[start:next_nl]
                end = next_nl
        c = c.strip()
        if len(c) > 200:
            chunks.append(c)
        start = max(end - overlap, end)
    return chunks

async def fetch(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, timeout=20)
    r.raise_for_status()
    return r.text

async def crawl(seed_urls, max_pages=150):
    seen = set()
    queue = list(seed_urls)
    pages = []
    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent":"SignaChatbot/1.0"}) as client:
        pbar = tqdm(total=max_pages, desc="Crawling")
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            url = clean_url(url)
            if url in seen or not is_allowed(url):
                continue
            seen.add(url)
            try:
                html = await fetch(client, url)
            except Exception:
                continue
            pages.append({"url": url, "html": html})
            pbar.update(1)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                if is_allowed(href) and href not in seen:
                    queue.append(href)
        pbar.close()
    return pages

def build_index(docs, out_dir="data", chunk_size=1200, overlap=200):
    os.makedirs(out_dir, exist_ok=True)
    records = []
    for d in docs:
        text = extract_text(d["html"])
        if not text:
            continue
        for c in chunk_text(text, chunk_size, overlap):
            records.append({"url": d["url"], "text": c})

    if not records:
        raise RuntimeError("Nenhum conteúdo legível encontrado para indexar.")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    corpus = [r["text"] for r in records]
    embs = model.encode(corpus, batch_size=64, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)

    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embs)
    faiss.write_index(index, os.path.join(out_dir, "index.faiss"))

    with open(os.path.join(out_dir, "meta.jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Index criado com {len(records)} chunks.")

def load_seed(path):
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="demo_data/seed_urls.txt")
    ap.add_argument("--max_pages", type=int, default=int(os.getenv("MAX_PAGES", "150")))
    ap.add_argument("--chunk_size", type=int, default=int(os.getenv("CHUNK_SIZE", "1200")))
    ap.add_argument("--chunk_overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", "200")))
    ap.add_argument("--out_dir", default=os.getenv("DATA_DIR", "data"))
    args = ap.parse_args()

    import asyncio
    seed_urls = load_seed(args.seed)
    pages = asyncio.run(crawl(seed_urls, max_pages=args.max_pages))
    build_index(pages, out_dir=args.out_dir, chunk_size=args.chunk_size, overlap=args.chunk_overlap)

if __name__ == "__main__":
    main()
