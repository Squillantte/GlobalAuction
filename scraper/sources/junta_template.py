"""
Plug‑in: Junta Comercial – {{UF}}
Consome o RSS ou página de avisos da Junta.
Preencha RSS_URL e a lógica de filtragem.
"""

from __future__ import annotations
import asyncio, re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from scraper.fetch_auctions import Auction

UF = "{{UF}}"
RSS_URL = "https://TODO/rss"      # TODO
HEADERS = {"User-Agent": "LeilaoBot/1.0"}

@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as r:
        r.raise_for_status()
        return await r.text()

async def fetch(photos_dir: Path) -> List[Auction]:
    auctions = []
    async with aiohttp.ClientSession() as s:
        xml  = await _get(s, RSS_URL)
        soup = BeautifulSoup(xml, "xml")
        for item in soup.find_all("item"):
            title = item.title.get_text(strip=True)
            if "leil" not in title.lower():
                continue
            link  = item.link.get_text(strip=True)
            pub   = item.pubDate.get_text(strip=True)
            date  = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z")\
                    .astimezone(timezone.utc).isoformat()
            price = re.search(r"R\$ ?[\d\.]+,\d{2}", title)
            auctions.append(Auction(
                source=f"Junta {UF}",
                id=link.split("/")[-1],
                title=title,
                auction_date=date,
                location=UF,
                price=price.group() if price else "N/A",
                photo_path="",
                url=link,
            ))
    return auctions
