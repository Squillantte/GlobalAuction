"""
Plug‑in: Zukerman Leilões – https://www.zukerman.com.br/
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

BASE_URL = "https://www.zukerman.com.br"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeilaoBot/1.0; +https://seusite.com)"
}


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
async def _get(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        return await resp.text()


async def _parse_card(session: aiohttp.ClientSession, card, photos_dir: Path) -> Auction | None:
    link_tag = card.select_one("a.card_produto")
    if link_tag is None:
        return None

    lot_url = BASE_URL + link_tag["href"]
    id_ = link_tag["href"].split("-")[-1]

    title = card.select_one(".titulo-cards").get_text(strip=True)
    date_text = card.select_one(".data-leilao").get_text(strip=True)
    price = card.select_one(".preco-cards").get_text(strip=True)
    img_tag = card.select_one("img")  # lazy‑load

    # 10/05/2025
    date_str = datetime.strptime(date_text, "%d/%m/%Y").replace(tzinfo=timezone.utc).isoformat()
    photo_path = ""

    if img_tag and img_tag.get("data-src"):
        img_url = img_tag["data-src"]
        photo_path = await _download_photo(session, img_url, photos_dir)

    return Auction(
        source="Zukerman",
        id=id_,
        title=title,
        auction_date=date_str,
        location="",
        price=price,
        photo_path=photo_path,
        url=lot_url,
    )


async def _download_photo(session: aiohttp.ClientSession, url: str, photos_dir: Path) -> str:
    name = url.split("/")[-1].split("?")[0]
    dest = photos_dir / name
    if dest.exists():
        return str(dest.relative_to(photos_dir.parent))
    async with session.get(url, headers=HEADERS, timeout=60) as resp:
        resp.raise_for_status()
        dest.write_bytes(await resp.read())
    return str(dest.relative_to(photos_dir.parent))


async def fetch(photos_dir: Path) -> List[Auction]:
    list_url = f"{BASE_URL}/index/leiloes-judiciais"
    auctions: List[Auction] = []
    async with aiohttp.ClientSession() as session:
        html = await _get(session, list_url)
        soup = BeautifulSoup(html, "lxml")

        cards = soup.select(".card")
        tasks = [_parse_card(session, card, photos_dir) for card in cards]
        for coro in asyncio.as_completed(tasks):
            lot = await coro
            if lot:
                auctions.append(lot)
    return auctions
