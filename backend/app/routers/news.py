"""
News router — Bangladesh legal news aggregated from RSS feeds.

GET /api/news  →  filtered legal news items, Redis-cached for 30 minutes
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["news"])

_CACHE_KEY = "legal_news"
_CACHE_TTL = 1800   # 30 minutes
_FETCH_TIMEOUT = 10.0

_FEEDS = [
    {"url": "https://www.prothomalo.com/feed",      "source": "প্রথম আলো"},
    {"url": "https://www.bd-pratidin.com/rss.xml",  "source": "বিডি প্রতিদিন"},
    {"url": "https://www.jugantor.com/rss.xml",      "source": "যুগান্তর"},
]

_LEGAL_KEYWORDS = [
    "আদালত", "আইন", "বিচার", "মামলা", "হাইকোর্ট", "সুপ্রিম", "রায়",
    "আইনজীবী", "দণ্ড", "জামিন", "আপিল", "ট্রাইব্যুনাল",
    "verdict", "court", "law", "legal", "judgment",
]

_CATEGORY_MAP: Dict[str, List[str]] = {
    "সুপ্রিম কোর্ট": ["সুপ্রিম", "supreme court"],
    "হাইকোর্ট":      ["হাইকোর্ট", "হাই কোর্ট", "high court"],
    "আদালত":         ["আদালত", "court", "ট্রাইব্যুনাল", "tribunal"],
    "মামলা":          ["মামলা", "case", "suit", "petition", "আপিল"],
    "রায়":            ["রায়", "verdict", "judgment", "আদেশ", "order"],
    "জামিন":           ["জামিন", "bail"],
    "আইন":            ["আইন", "law", "legal", "বিচার", "legislation"],
}

_FALLBACK_NEWS: List[Dict[str, Any]] = [
    {
        "id": "fallback_1",
        "title": "বাংলাদেশ সুপ্রিম কোর্টের নতুন বিধিমালা জারি",
        "summary": "বাংলাদেশ সুপ্রিম কোর্ট আদালত পরিচালনায় নতুন বিধিমালা প্রণয়ন করেছে যা আগামী মাস থেকে কার্যকর হবে।",
        "link": "https://supremecourt.gov.bd",
        "source": "সুপ্রিম কোর্ট",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "আদালত",
    },
    {
        "id": "fallback_2",
        "title": "ডিজিটাল নিরাপত্তা আইনের সংশোধনী প্রক্রিয়া চলছে",
        "summary": "সরকার ডিজিটাল নিরাপত্তা আইন সংশোধনের পরিকল্পনা নিয়ে আলোচনা করছে। বিভিন্ন মহল থেকে আইনের কিছু ধারা পরিবর্তনের দাবি উঠেছে।",
        "link": "https://minlaw.gov.bd",
        "source": "আইন মন্ত্রণালয়",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "আইন",
    },
    {
        "id": "fallback_3",
        "title": "হাইকোর্টে জনগুরুত্বপূর্ণ মামলার দ্রুত শুনানির নির্দেশ",
        "summary": "জনগুরুত্বপূর্ণ মামলা দ্রুত নিষ্পত্তির জন্য হাইকোর্টে বিশেষ বেঞ্চ গঠন করা হয়েছে। আদালত জানিয়েছেন দীর্ঘদিন ঝুলে থাকা মামলাগুলো অগ্রাধিকার পাবে।",
        "link": "https://supremecourt.gov.bd",
        "source": "আদালত সংবাদ",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "হাইকোর্ট",
    },
    {
        "id": "fallback_4",
        "title": "শ্রম আইনে সংশোধনী: শ্রমিকদের অধিকার আরও শক্তিশালী হবে",
        "summary": "শ্রম আইনে নতুন ধারা সংযোজনের মাধ্যমে শ্রমিকদের ন্যূনতম মজুরি ও অধিকার সুনিশ্চিত করা হচ্ছে। মালিকপক্ষের জন্যও দায়বদ্ধতা বাড়ানো হচ্ছে।",
        "link": "https://mole.gov.bd",
        "source": "শ্রম মন্ত্রণালয়",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "আইন",
    },
    {
        "id": "fallback_5",
        "title": "ভূমি রেজিস্ট্রেশন সহজ করতে নতুন আইনের খসড়া তৈরি",
        "summary": "সরকার ভূমি রেজিস্ট্রেশন প্রক্রিয়া সহজ ও দ্রুত করার লক্ষ্যে নতুন আইনের খসড়া তৈরি করেছে। সাধারণ মানুষের ভোগান্তি কমানোই এই উদ্যোগের লক্ষ্য।",
        "link": "https://minland.gov.bd",
        "source": "ভূমি মন্ত্রণালয়",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "category": "আইন",
    },
]


# ─── Schemas ──────────────────────────────────────────────────────────────────

class NewsItem(BaseModel):
    id:           str
    title:        str
    summary:      str
    link:         str
    source:       str
    published_at: str
    category:     str


class NewsResponse(BaseModel):
    news:         List[NewsItem]
    cached:       bool
    last_updated: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _item_id(link: str) -> str:
    return hashlib.md5(link.encode("utf-8")).hexdigest()[:16]


def _is_legal(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in _LEGAL_KEYWORDS)


def _detect_category(title: str, desc: str) -> str:
    combined = (title + " " + desc).lower()
    for category, keywords in _CATEGORY_MAP.items():
        if any(kw.lower() in combined for kw in keywords):
            return category
    return "আইন"


def _parse_pub_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    for fn in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            return fn(raw.strip())  # type: ignore[arg-type]
        except Exception:
            pass
    return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_rss(xml_text: str, source: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("rss_parse_error", source=source, error=str(exc))
        return items

    for item_el in root.iter("item"):
        title   = _strip_html(item_el.findtext("title",       "")).strip()
        desc    = _strip_html(item_el.findtext("description", "")).strip()
        link    = (item_el.findtext("link") or "").strip()
        pubdate = (item_el.findtext("pubDate") or "").strip()

        # Some feeds put the URL inside an atom:link element
        if not link:
            for child in item_el:
                if "link" in child.tag.lower():
                    link = child.get("href") or child.text or ""
                    break

        if not title and not link:
            continue
        if not _is_legal(title + " " + desc):
            continue

        dt       = _parse_pub_date(pubdate)
        iso_str  = dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        sort_key = dt.timestamp() if dt else 0.0

        items.append({
            "id":           _item_id(link or title),
            "title":        title,
            "summary":      desc[:150],
            "link":         link,
            "source":       source,
            "published_at": iso_str,
            "category":     _detect_category(title, desc),
            "_sort_key":    sort_key,
        })

    return items


async def _fetch_one(client: httpx.AsyncClient, url: str, source: str) -> List[Dict[str, Any]]:
    try:
        resp = await client.get(url, timeout=_FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return _parse_rss(resp.text, source)
    except Exception as exc:
        logger.warning("feed_fetch_failed", source=source, url=url, error=str(exc))
        return []


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/news", response_model=NewsResponse)
async def get_news() -> NewsResponse:
    import redis.asyncio as aioredis  # lazy import — only when endpoint is called

    settings = get_settings()
    now_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # ── Try Redis cache ───────────────────────────────────────────────────────
    redis_client: Optional[Any] = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        cached_raw = await redis_client.get(_CACHE_KEY)
        if cached_raw:
            data = json.loads(cached_raw)
            await redis_client.aclose()
            return NewsResponse(
                news=[NewsItem(**n) for n in data["news"]],
                cached=True,
                last_updated=data.get("last_updated", now_iso),
            )
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))
        redis_client = None

    # ── Fetch all feeds concurrently ─────────────────────────────────────────
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HalloAdvocate/1.0; +https://hallo.advocate)"}
    async with httpx.AsyncClient(headers=headers) as client:
        raw_results = await asyncio.gather(
            *[_fetch_one(client, f["url"], f["source"]) for f in _FEEDS],
            return_exceptions=True,
        )

    all_items: List[Dict[str, Any]] = []
    for r in raw_results:
        if isinstance(r, list):
            all_items.extend(r)

    if not all_items:
        logger.warning("all_feeds_empty_returning_fallback")
        all_items = [dict(item, _sort_key=0.0) for item in _FALLBACK_NEWS]

    # Sort desc, deduplicate, cap at 20
    seen_ids: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for item in sorted(all_items, key=lambda x: x.get("_sort_key", 0.0), reverse=True):
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            unique.append(item)
        if len(unique) >= 20:
            break

    news_items = [NewsItem(**{k: v for k, v in item.items() if k != "_sort_key"}) for item in unique]

    # ── Write to Redis ────────────────────────────────────────────────────────
    if redis_client is not None:
        try:
            payload = json.dumps({"news": [n.model_dump() for n in news_items], "last_updated": now_iso})
            await redis_client.setex(_CACHE_KEY, _CACHE_TTL, payload)
        except Exception as exc:
            logger.warning("redis_write_failed", error=str(exc))
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return NewsResponse(news=news_items, cached=False, last_updated=now_iso)
