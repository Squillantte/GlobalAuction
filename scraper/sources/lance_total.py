"""
Plug‑in: Lance Total – https://www.lancetotal.com.br
Coleta todos os imóveis com leilão aberto ou agendado.
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

BASE_URL = "https://www.lancetotal.com.br"
LIST_URL = f"{BASE_URL}/leiloes/imoveis"

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


async def _parse_card(session: aiohttp.ClientSession, card, photos_dir: Path) -> Auction | None:
    link = card.select_one("a")
    if not link:
        return None

    lot_url = BASE_URL + link["href"]
    id_ = link["href"].split("/")[-1]

    title = card.select_one(".card-title").get_text(strip=True)
    date_text = card.select_one(".leilao-data").get_text(strip=True)  # ex: 25/06/2025
    price = card.select_one(".valor-lance") or card.select_one(".valor-avaliacao")
    price_text = price.get_text(strip=True) if price else "N/A"
    img_tag = card.select_one("img")

    date_iso = datetime.strptime(date_text, "%d/%m/%Y").replace(tzinfo=timezone.utc).isoformat()
    photo_path = ""
    if img_tag and (img_tag.get("src") or img_tag.get("data-src")):
        img_url = img_tag.get("data-src") or img_tag["src"]
        if img_url.startswith("/"):
            img_url = BASE_URL + img_url
        photo_path = await _download_photo(session, img_url, photos_dir)

    return Auction(
        source="Lance Total",
        id=id_,
        title=title,
        auction_date=date_iso,
        location="",
        price=price_text,
        photo_path=photo_path,
        url=lot_url,
    )


async def fetch(photos_dir: Path) -> List[Auction]:
    auctions: List[Auction] = []
    async with aiohttp.ClientSession() as session:
        html = await _get(session, LIST_URL)
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".card-imovel")

        tasks = [_parse_card(session, c, photos_dir) for c in cards]
        for coro in asyncio.as_completed(tasks):
            lot = await coro
            if lot:
                auctions.append(lot)
    return auctions
