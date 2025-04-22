"""
Plug‑in: Tribunal de Justiça – {{UF}}
Preencha as constantes BASE_URL e LIST_URL do respectivo TJ
e ajuste o seletor HTML em _parse_row().

TODO:
• BASE_URL / LIST_URL
• Seletor de linhas (rows)
• Mapeamento das colunas (id_, title, etc.)
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from scraper.fetch_auctions import Auction

UF = "{{UF}}"                    # será trocado automaticamente
BASE_URL = "https://TODO"        # TODO
LIST_URL = f"{BASE_URL}/TODO"    # TODO
HEADERS = {"User-Agent": "LeilaoBot/1.0"}

@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as r:
        r.raise_for_status()
        return await r.text()

async def _parse_row(row) -> Auction | None:
    cols = row.find_all("td")
    if len(cols) < 4:
        return None
    id_       = cols[0].get_text(strip=True)         # TODO adaptar
    title     = cols[1].get_text(strip=True)
    date_txt  = cols[2].get_text(strip=True)
    price_txt = cols[3].get_text(strip=True)

    date_iso = datetime.strptime(date_txt, "%d/%m/%Y").replace(
        tzinfo=timezone.utc).isoformat()

    return Auction(
        source=f"TJ{UF}",
        id=id_,
        title=title,
        auction_date=date_iso,
        location=UF,
        price=price_txt,
        photo_path="",
        url=LIST_URL,
    )

async def fetch(photos_dir: Path) -> List[Auction]:
    async with aiohttp.ClientSession() as s:
        html  = await _get(s, LIST_URL)
        soup  = BeautifulSoup(html, "lxml")
        rows  = soup.select("table tr")   # TODO ajustar seletor
        lots  = [await _parse_row(r) for r in rows]
        return [l for l in lots if l]
