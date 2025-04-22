"""
Plug‑in: Diário da Junta Comercial do RJ (JUCERJA)
Busca avisos de leilão publicados no Diário Oficial Empresarial.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from scraper.fetch_auctions import Auction

BASE_URL = "https://www.jucerja.rj.gov.br"
RSS_URL  = f"{BASE_URL}/rss/diarioempresarial.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeilaoBot/1.0; +https://seusite.com)"
}


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        return await resp.text()


async def fetch(photos_dir: Path) -> List[Auction]:
    auctions: List[Auction] = []
    async with aiohttp.ClientSession() as session:
        xml = await _get(session, RSS_URL)
        soup = BeautifulSoup(xml, "xml")

        for item in soup.find_all("item"):
            title = item.title.get_text(strip=True)
            if "leil" not in title.lower():
                continue

            link      = item.link.get_text(strip=True)
            pub_date  = item.pubDate.get_text(strip=True)
            date_iso  = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z") \
                           .astimezone(timezone.utc).isoformat()
            price     = re.search(r"R\$ ?[\d\.]+,\d{2}", title)
            auctions.append(
                Auction(
                    source="JUCERJA",
                    id=link.split("/")[-1],
                    title=title,
                    auction_date=date_iso,
                    location="RJ",
                    price=price.group() if price else "N/A",
                    photo_path="",
                    url=link,
                )
            )
    return auctions
