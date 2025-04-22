"""
Plug‑in: Tribunal de Justiça de PI – Portal de Leilões
Pesquisa lotes de imóveis com leilão futuro.
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

BASE_URL = "https://www2.tjpi.jus.br"
LIST_URL = f"{BASE_URL}/leiloes/LeiloesJudiciais.aspx"   # página de listagem

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeilaoBot/1.0; +https://seusite.com)"
}


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        return await resp.text()


async def _download_photo(session: aiohttp.ClientSession, url: str, photos_dir: Path) -> str:
    name = url.split("/")[-1].split("?")[0]
    dest = photos_dir / name
    if dest.exists():
        return str(dest.relative_to(photos_dir.parent))
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        dest.write_bytes(await resp.read())
    return str(dest.relative_to(photos_dir.parent))


async def _parse_row(session: aiohttp.ClientSession, row, photos_dir: Path) -> Auction | None:
    cols = row.find_all("td")
    if len(cols) < 6:
        return None

    id_ = cols[0].get_text(strip=True)
    title = cols[1].get_text(strip=True)
    date_text = cols[2].get_text(strip=True)         # 22/07/2025
    price = cols[3].get_text(strip=True)
    city = cols[4].get_text(strip=True)

    lot_link_tag = cols[1].find("a")
    lot_url = BASE_URL + lot_link_tag["href"] if lot_link_tag else LIST_URL

    img_tag = cols[1].find("img")
    photo_path = ""
    if img_tag and img_tag.get("src"):
        img_url = BASE_URL + img_tag["src"]
        photo_path = await _download_photo(session, img_url, photos_dir)

    date_iso = datetime.strptime(date_text, "%d/%m/%Y").replace(tzinfo=timezone.utc).isoformat()

    return Auction(
        source="TJPI",
        id=id_,
        title=title,
        auction_date=date_iso,
        location=city,
        price=price,
        photo_path=photo_path,
        url=lot_url,
    )


async def fetch(photos_dir: Path) -> List[Auction]:
    auctions: List[Auction] = []
    async with aiohttp.ClientSession() as session:
        html = await _get(session, LIST_URL)
        soup = BeautifulSoup(html, "lxml")
        rows = soup.select("table#ctl00_cphConteudo_gdvLeiloes tr[class^='linha']")

        tasks = [_parse_row(session, r, photos_dir) for r in rows]
        for coro in asyncio.as_completed(tasks):
            lot = await coro
            if lot:
                auctions.append(lot)
    return auctions
