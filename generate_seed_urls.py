#!/usr/bin/env python3
import re
import sys
import argparse
from urllib.parse import urljoin, urldefrag, urlparse
import collections

import httpx
from bs4 import BeautifulSoup
from urllib import robotparser
from tqdm import tqdm   # 👈 barra de progresso

DOMAIN = "www.signa.pt"
BASE = f"https://{DOMAIN}/"

PRIORITY_PATHS = [
    "/brindes/empresa.asp",
    "/brindes/contactos.asp",
    "/brindes/ap_Faqs.asp",
    "/brindes/ap_CondicoesVenda.asp",
    "/brindes/ap_Privacidade.asp",
    "/brindes/ap_Garantia.asp",
    "/brindes/ap_Personalizacao.asp",
    "/brindes/top.asp",
    "/brindes/pedidoCatalogo.asp",
]

RE_CATEGORY = re.compile(r"/brindes/categoria\.asp\?idCategoria=\d+\b", re.I)
RE_SECTOR   = re.compile(r"/brindes/sector\.asp\?idSector=\d+\b", re.I)

BLOCK_PATTERNS = [
    r"orcamento\.asp", r"login", r"register",
    r"carrinho", r"finalizar", r"checkout",
    r"top\.asp",   
]

def is_blocked(path: str) -> bool:
    return any(re.search(bp, path.lower()) for bp in BLOCK_PATTERNS)

def norm_url(u: str) -> str:
    u, _ = urldefrag(u)
    return u

def same_domain(u: str) -> bool:
    p = urlparse(u)
    return (p.scheme in ("http", "https")) and (p.netloc == DOMAIN)

def fetch_robots_allow(client: httpx.Client) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    try:
        r = client.get(urljoin(BASE, "/robots.txt"), timeout=10)
        if r.status_code == 200:
            rp.parse(r.text.splitlines())
        else:
            rp.parse(["User-agent: *", "Allow: /"])
    except Exception:
        rp.parse(["User-agent: *", "Allow: /"])
    return rp

def good_candidate(path: str) -> bool:
    if path in ("/", ""):
        return True
    if path in PRIORITY_PATHS:
        return True
    if RE_CATEGORY.search(path) or RE_SECTOR.search(path):
        return True
    if re.search(r"(empresa|contactos|faq|condicoes|privacidade|garantia|personalizacao|pedidoCatalogo)", path, re.I):
        return True
    return False

def discover(start_urls, max_pages=300, max_categories=50, max_sectors=50, include_home=True):
    seen = set()
    candidates = collections.OrderedDict()
    cat_count, sec_count = 0, 0

    headers = {"User-Agent": "SeedSignaBot/1.0"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=15) as client:
        rp = fetch_robots_allow(client)

        queue = collections.deque()
        if include_home:
            queue.append(BASE)
        for s in start_urls:
            queue.append(s if s.startswith("http") else urljoin(BASE, s))

        pbar = tqdm(total=max_pages, desc="Descobrindo páginas")  # 👈 barra
        while queue and len(seen) < max_pages:
            url = norm_url(queue.popleft())
            if url in seen or not same_domain(url):
                continue
            if not rp.can_fetch("*", url):
                continue
            parsed = urlparse(url)
            if is_blocked(parsed.path):
                continue

            seen.add(url)
            pbar.update(1)  # 👈 avança a barra

            try:
                r = client.get(url)
                if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                    continue
                html = r.text
            except Exception:
                continue

            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = norm_url(urljoin(url, a["href"]))
                if not same_domain(href):
                    continue
                p = urlparse(href)
                if is_blocked(p.path):
                    continue
                if href not in seen:
                    queue.append(href)

                if good_candidate(p.path):
                    if RE_CATEGORY.search(p.path):
                        if cat_count >= max_categories:
                            continue
                        cat_count += 1
                    if RE_SECTOR.search(p.path):
                        if sec_count >= max_sectors:
                            continue
                        sec_count += 1
                    candidates.setdefault(href, None)

            if parsed.path in PRIORITY_PATHS or parsed.path == "/":
                candidates.setdefault(url, None)
        pbar.close()

    return list(candidates.keys())

def main():
    ap = argparse.ArgumentParser(description="Gerar seed_urls.txt automaticamente para signa.pt")
    ap.add_argument("--max_pages", type=int, default=300)
    ap.add_argument("--max_categories", type=int, default=80)
    ap.add_argument("--max_sectors", type=int, default=40)
    ap.add_argument("--no_home", action="store_true")
    ap.add_argument("--output", default="seed_urls.txt")
    args = ap.parse_args()

    seeds = discover(
        start_urls=[],
        max_pages=args.max_pages,
        max_categories=args.max_categories,
        max_sectors=args.max_sectors,
        include_home=not args.no_home,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        for u in seeds:
            f.write(u + "\n")

    print(f"✅ Gerado {args.output} com {len(seeds)} URLs.")

if __name__ == "__main__":
    main()
