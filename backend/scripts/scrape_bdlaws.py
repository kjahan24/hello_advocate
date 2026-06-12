#!/usr/bin/env python3
"""
scrape_bdlaws.py — Scrape all acts from https://bdlaws.minlaw.gov.bd

Scraping strategy (fastest-first per act):
  1. GET /act-print-{id}.html    — full printable page, all sections inline
  2. GET /act-details-{id}.html  — detail view, sections sometimes inline
  3. GET /act-{id}.html          — overview; follow individual section links

Section parsing tries four strategies in order:
  A. col-sm-3 (header) + col-sm-9 (body) two-column pairs
  B. <table> rows where one cell is the section number
  C. Wide content divs (col-md-12, col-md-10) — preamble / short acts
  D. Every <p> longer than 40 chars (last resort)

Rate limiting: 1-second enforced delay between every HTTP request.
Progress:      saved to data/.scrape_progress.json after every act —
               safe to Ctrl-C and resume with --resume.

Usage
-----
  cd backend
  python scripts/scrape_bdlaws.py                          # full run
  python scripts/scrape_bdlaws.py --limit 20               # smoke test
  python scripts/scrape_bdlaws.py --resume                 # skip done acts
  python scripts/scrape_bdlaws.py --output data/acts_full.json
  python scripts/scrape_bdlaws.py --skip-sections          # titles only (fast)
  python scripts/scrape_bdlaws.py --start-id 500           # start from act 500

After completion:
  python scripts/ingest_acts.py --from-file data/acts_full.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# ── dependency guards ─────────────────────────────────────────────────────────

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed.  pip install httpx", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed.  pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)

# ── constants ─────────────────────────────────────────────────────────────────

BASE_URL       = "http://bdlaws.minlaw.gov.bd"
REQUEST_DELAY  = 1.0   # seconds between requests
MAX_RETRIES    = 3
RETRY_BACKOFF  = 2.0   # base for exponential back-off (2s, 4s)
MAX_ACT_ID     = 1600  # upper bound for range-based fallback

# Bengali → ASCII digit map
_BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# ── category inference ────────────────────────────────────────────────────────

_CATEGORY_KW: dict[str, list[str]] = {
    "criminal":            ["penal", "criminal", "crpc", "crime", "punishment", "offence",
                             "offense", "arms", "explosive", "narcotic", "drug", "trafficking",
                             "terrorism", "police", "prison", "jail"],
    "family":              ["marriage", "matrimonial", "divorce", "dissolution", "family",
                             "child", "guardian", "guardianship", "succession", "inheritance",
                             "dower", "dowry", "mahr", "polygamy", "personal law"],
    "land_property":       ["land", "immovable property", "registration", "revenue", "survey",
                             "settlement", "acquisition", "cadastral", "khas land"],
    "labor_employment":    ["labour", "labor", "employment", "worker", "workman", "factory",
                             "shop establishment", "wage", "trade union", "provident fund",
                             "gratuity", "maternity", "industrial relation"],
    "constitutional":      ["constitution", "election", "parliament", "representation",
                             "referendum", "fundamental rights", "ordinance", "emergency"],
    "commercial_business": ["company", "partnership", "trade mark", "copyright", "patent",
                             "arbitration", "insolvency", "bankruptcy", "commerce",
                             "mercantile", "specific relief", "contract act"],
    "banking_finance":     ["bank", "banking", "financial institution", "insurance",
                             "currency", "reserve bank", "negotiable instrument", "cheque",
                             "microfinance", "money laundering", "securities"],
    "tenancy_rent":        ["rent control", "urban tenancy", "premises", "eviction",
                             "house rent", "rental"],
    "consumer_rights":     ["consumer protection", "food", "drug", "standard",
                             "weights and measures", "pure food", "adulteration"],
    "digital_cyber":       ["digital", "cyber", "telecommunication", "information technology",
                             "broadcasting", "wireless", "satellite", "electronic transaction"],
    "immigration":         ["immigration", "passport", "foreigners", "aliens",
                             "refugee", "citizenship", "nationality"],
}


def _infer_category(title: str, snippet: str = "") -> str:
    haystack = (title + " " + snippet[:600]).lower()
    best, top = "civil", 0
    for cat, kws in _CATEGORY_KW.items():
        n = sum(1 for kw in kws if kw in haystack)
        if n > top:
            best, top = cat, n
    return best


# ══════════════════════════════════════════════════════════════════════════════
# HTTP layer
# ══════════════════════════════════════════════════════════════════════════════

def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection":      "keep-alive",
        },
        timeout=30,
        follow_redirects=True,
    )


_last_req_at: float = 0.0


def _fetch(client: httpx.Client, url: str, *, delay: float | None = None) -> str | None:
    """
    GET *url* respecting the per-request delay and retrying on transient errors.
    Returns the response text, or None for 404 / persistent failure.
    Reads REQUEST_DELAY at call time (not import time) so --delay CLI flag works.
    """
    global _last_req_at
    if delay is None:
        delay = REQUEST_DELAY
    elapsed = time.monotonic() - _last_req_at
    if elapsed < delay:
        time.sleep(delay - elapsed)

    for attempt in range(MAX_RETRIES):
        try:
            _last_req_at = time.monotonic()
            r = client.get(url)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None        # act does not exist — skip silently
            if r.status_code in (429, 503, 502):
                wait = RETRY_BACKOFF ** (attempt + 1)
                print(f"  [{r.status_code}] rate-limited, waiting {wait:.0f}s…", flush=True)
                time.sleep(wait)
                continue
            # Other 4xx/5xx — treat as transient
            print(f"  [{r.status_code}] {url}", flush=True)
        except (httpx.ConnectError, httpx.ReadTimeout,
                httpx.RemoteProtocolError, httpx.ConnectTimeout) as exc:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF ** (attempt + 1)
                print(f"  network error ({exc!s:.60}), retry {attempt + 1} in {wait:.0f}s…",
                      flush=True)
                time.sleep(wait)
            else:
                print(f"  GIVE UP {url}: {exc!s:.80}", flush=True)
                return None

    return None


def _parse(html: str) -> BeautifulSoup:
    # lxml is faster and more lenient; fall back to built-in html.parser
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


# ══════════════════════════════════════════════════════════════════════════════
# Text utilities
# ══════════════════════════════════════════════════════════════════════════════

def _clean(text: str) -> str:
    text = text.replace("‌", "").replace("‍", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_year(text: str) -> int | None:
    t = text.translate(_BN)
    m = re.search(r"(1[5-9]\d\d|20\d\d)", t)
    return int(m.group(1)) if m else None


def _is_bengali(text: str) -> bool:
    return bool(re.search(r"[ঀ-৿]", text))


def _extract_act_id(href: str) -> str | None:
    m = re.search(r"/act(?:-details|-print)?-(\d+)(?:[./]|$)", href)
    return m.group(1) if m else None


def _split_sec_head(raw: str) -> tuple[str | None, str | None]:
    """
    'Section 5. Title'   → ('5',  'Title')
    '5A. Something'      → ('5A', 'Something')
    '302'                → ('302', None)
    'Short title'        → (None, 'Short title')
    """
    raw = raw.strip()
    # 'Section N. Title' / 'Art. N. Title'
    m = re.match(
        r"^(?:section|sec\.?|art\.?|article|clause|§)\s*"
        r"(\d+[A-Za-z]?(?:\s*\(\d+\))?)\s*[.\-:–—]\s*(.*)",
        raw, re.I,
    )
    if m:
        return m.group(1).strip(), _clean(m.group(2)) or None
    # 'N. Title' or 'N- Title'
    m2 = re.match(r"^(\d+[A-Za-z]?)\s*[.\-:–—]\s*(.*)", raw)
    if m2:
        return m2.group(1), _clean(m2.group(2)) or None
    # bare number
    m3 = re.match(r"^(\d+[A-Za-z]?)$", raw)
    if m3:
        return m3.group(1), None
    return None, raw or None


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — act list
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_act_list(client: httpx.Client) -> list[dict[str, Any]]:
    """
    Return [{act_id, title, year}, …] for all known acts.
    Tries three index URLs; falls back to a numeric ID range if all fail.
    """
    index_urls = [
        f"{BASE_URL}/laws-of-bangladesh.html",
        f"{BASE_URL}/laws-of-bangladesh-chronological-index.html",
        f"{BASE_URL}/laws-of-bangladesh-alphabetical-index.html",
    ]

    for url in index_urls:
        print(f"  Fetching act index: {url}", flush=True)
        html = _fetch(client, url, delay=0)
        if not html:
            continue
        acts = _parse_act_list(html)
        if acts:
            print(f"  Found {len(acts):,} acts.", flush=True)
            return acts
        print(f"  No acts parsed from {url} — trying next.", flush=True)

    # Fallback: probe IDs 1 … MAX_ACT_ID
    print(f"  Index pages unreachable — will probe IDs 1–{MAX_ACT_ID}.", flush=True)
    return [{"act_id": str(i), "title": None, "year": None}
            for i in range(1, MAX_ACT_ID + 1)]


def _parse_act_list(html: str) -> list[dict[str, Any]]:
    s = _parse(html)
    acts: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Table inside div.table-responsive (confirmed by Scrapy article)
    for table in s.select("div.table-responsive table, table"):
        for row in table.select("tbody tr, tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Find the cell that contains an act link
            link = None
            for cell in cells:
                a = cell.find("a", href=re.compile(r"/act[-]"))
                if a:
                    link = a
                    break
            if not link:
                continue

            act_id = _extract_act_id(link["href"])
            if not act_id or act_id in seen:
                continue
            seen.add(act_id)

            title = _clean(link.get_text())

            # Year is usually in the last or second-to-last cell
            year: int | None = None
            for cell in reversed(cells):
                y = _parse_year(_clean(cell.get_text()))
                if y:
                    year = y
                    break

            acts.append({"act_id": act_id, "title": title, "year": year})

    return acts


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — individual act
# ══════════════════════════════════════════════════════════════════════════════

def _scrape_act(
    client: httpx.Client,
    act_id: str,
    skip_sections: bool = False,
) -> dict[str, Any] | None:
    """
    Fetch and parse one act. Returns a record dict or None if the act
    could not be found / parsed.
    """
    # Try URLs in priority order: print page → details page → overview page
    candidates = [
        (f"{BASE_URL}/act-print-{act_id}.html",   True),   # (url, is_full_page)
        (f"{BASE_URL}/act-details-{act_id}.html", False),
        (f"{BASE_URL}/act-{act_id}.html",         False),
    ]

    for url, is_full_page in candidates:
        html = _fetch(client, url)
        if not html:
            continue

        s = _parse(html)
        if _is_error_page(s):
            continue

        title_en, title_bn = _parse_titles(s)
        if not title_en and not title_bn:
            continue
        # If only Bengali title found, move it
        if not title_en and title_bn:
            title_en, title_bn = title_bn, None

        year       = _parse_act_year(s) or _parse_year(title_en or "")
        is_repealed = _check_repealed(s)

        if skip_sections:
            sections: list[dict[str, Any]] = []
        else:
            sections = _parse_sections(s, client, act_id, is_full_page)

        snippet   = " ".join(sec.get("text", "") for sec in sections[:3])
        category  = _infer_category(title_en or "", snippet)
        full_text = "\n\n".join(
            "\n".join(filter(None, [
                (f"Section {sec['section_no']}." if sec.get("section_no") else ""),
                (sec.get("heading") or ""),
                (sec.get("text") or ""),
            ]))
            for sec in sections
        ).strip() or None

        return {
            "act_id":     act_id,
            "title":      title_en,
            "title_bn":   title_bn,
            "year":       year,
            "category":   category,
            "is_repealed": is_repealed,
            "source_url": url,
            "full_text":  full_text,
            "sections":   sections,
        }

    return None


# ── act-page helpers ──────────────────────────────────────────────────────────


def _is_error_page(s: BeautifulSoup) -> bool:
    snippet = s.get_text()[:300].lower()
    return any(kw in snippet for kw in ("page not found", "404 not found",
                                         "আপনার কাঙ্ক্ষিত পাতাটি", "access denied"))


def _parse_titles(s: BeautifulSoup) -> tuple[str | None, str | None]:
    title_en: str | None = None
    title_bn: str | None = None

    selectors = [
        "section.bg-act-section h3",
        "section.bg-act-section h4",
        ".act-title h3",
        ".act-title",
        ".panel-heading h3",
        ".panel-title",
        "h1", "h2", "h3",
    ]
    for sel in selectors:
        for el in s.select(sel):
            t = _clean(el.get_text())
            if not t or len(t) < 4:
                continue
            # Skip navigation labels
            if t.lower() in ("laws of bangladesh", "bangladesh code", "home", "search"):
                continue
            if _is_bengali(t):
                if not title_bn:
                    title_bn = t
            else:
                if not title_en:
                    title_en = t
            if title_en and title_bn:
                return title_en, title_bn

    # Second pass: look for Bengali title in any heading we may have skipped
    if title_en and not title_bn:
        for el in s.select("h4, h5, .subtitle, .act-subtitle"):
            t = _clean(el.get_text())
            if t and _is_bengali(t):
                title_bn = t
                break

    return title_en, title_bn


def _parse_act_year(s: BeautifulSoup) -> int | None:
    for sel in [
        ".form-group.pull-right.text-info.publish-date",
        ".publish-date",
        ".act-year",
        ".enact-date",
        "span.date",
        "p.date",
    ]:
        el = s.select_one(sel)
        if el:
            y = _parse_year(_clean(el.get_text()))
            if y:
                return y
    return None


def _check_repealed(s: BeautifulSoup) -> bool:
    sample = s.get_text()[:3000]
    return bool(re.search(r"\bRepealed\b", sample, re.I))


# ══════════════════════════════════════════════════════════════════════════════
# Section parsing — four inline strategies + one link-follow fallback
# ══════════════════════════════════════════════════════════════════════════════

def _parse_sections(
    s: BeautifulSoup,
    client: httpx.Client,
    act_id: str,
    is_full_page: bool,
) -> list[dict[str, Any]]:

    # A: two-column layout (col-sm-3 header + col-sm-9 body)
    secs = _strategy_columns(s)
    if secs:
        return secs

    # B: table rows
    secs = _strategy_table(s)
    if secs:
        return secs

    # C: wide content divs (short acts / preamble-only)
    secs = _strategy_content_div(s)
    if secs:
        return secs

    # D: follow links to individual section sub-pages (only if not print page)
    if not is_full_page:
        links = _find_section_links(s, act_id)
        if links:
            secs = _fetch_section_pages(client, links)
            if secs:
                return secs

    # E: last resort — grab paragraphs
    return _strategy_paragraphs(s)


def _strategy_columns(s: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Handles the standard two-column layout used on both print and detail pages:
      <div class="row">
        <div class="col-sm-3 txt-head">Section N. Title</div>
        <div class="col-sm-9 txt-details"><p>Body text…</p></div>
      </div>
    """
    sections: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Try both Bootstrap row divs and plain table rows
    containers = s.select("div.row") or s.select("tr")
    for container in containers:
        head_el = (
            container.select_one("div.col-sm-3.txt-head")
            or container.select_one("div.col-sm-3")
            or container.select_one("td.txt-head")
        )
        body_el = (
            container.select_one("div.col-sm-9.txt-details")
            or container.select_one("div.col-sm-9")
            or container.select_one("td.txt-details")
        )
        if not head_el or not body_el:
            continue

        head = _clean(head_el.get_text())

        paras = [_clean(p.get_text()) for p in body_el.find_all("p")
                 if _clean(p.get_text())]
        body  = " ".join(paras) if paras else _clean(body_el.get_text())

        # Require non-trivial content
        if not body or len(body) < 15 or body in seen:
            continue
        # Skip navigation rows (short, no real text)
        if len(body) < 30 and not re.search(r"[a-zA-Zঀ-৿]{10}", body):
            continue
        seen.add(body)

        sec_no, heading = _split_sec_head(head)
        sections.append({
            "section_no": sec_no,
            "heading":    heading,
            "text":       body,
        })

    return sections


def _strategy_table(s: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Acts presented as a two-column HTML table:
      | Section No | Content |
    """
    sections: list[dict[str, Any]] = []
    for table in s.select("table"):
        rows = table.select("tr")
        if not rows:
            continue
        # Skip tables that look like navigation/layout (very few rows, very short)
        if len(rows) < 2:
            continue
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            head  = _clean(cells[0].get_text())
            # Use all remaining cells as body
            body  = " ".join(_clean(c.get_text()) for c in cells[1:])
            if not body or len(body) < 30:
                continue
            sec_no, heading = _split_sec_head(head)
            if sec_no or (heading and len(heading) > 5):
                sections.append({"section_no": sec_no, "heading": heading, "text": body})

    return sections


def _strategy_content_div(s: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Short acts and preamble-only pages dump all text into a single wide div.
    Selectors from the Scrapy article: col-md-12.pad-right, col-md-10.
    """
    for sel in [
        "div.col-md-12.pad-right",
        "div.col-md-10",
        "div.act-content",
        "div#act-content",
        "div.section-content",
        "div.content-body",
        "div.act-body",
    ]:
        el = s.select_one(sel)
        if not el:
            continue

        paras = [_clean(p.get_text()) for p in el.find_all("p")
                 if len(_clean(p.get_text())) > 30]

        if not paras:
            full = _clean(el.get_text())
            if len(full) > 50:
                return [{"section_no": None, "heading": "Preamble", "text": full}]
            continue

        sections: list[dict[str, Any]] = []
        for i, para in enumerate(paras, 1):
            sec_no, heading = _split_sec_head(para[:120])
            sections.append({
                "section_no": sec_no or str(i),
                "heading":    heading,
                "text":       para,
            })
        return sections

    return []


def _strategy_paragraphs(s: BeautifulSoup) -> list[dict[str, Any]]:
    """Last-resort: every paragraph ≥ 40 chars in the main body area."""
    container = (
        s.select_one("main")
        or s.select_one("article")
        or s.select_one("div#content")
        or s.select_one("div.container")
        or s.body
    )
    if not container:
        return []

    sections: list[dict[str, Any]] = []
    for i, p in enumerate(container.find_all("p"), 1):
        text = _clean(p.get_text())
        if len(text) < 40:
            continue
        sec_no, heading = _split_sec_head(text[:120])
        sections.append({
            "section_no": sec_no or str(i),
            "heading":    heading,
            "text":       text,
        })
        if len(sections) >= 300:   # safety cap
            break

    return sections


# ── section link fallback ─────────────────────────────────────────────────────


def _find_section_links(s: BeautifulSoup, act_id: str) -> list[str]:
    """
    Collect URLs to individual section sub-pages from the act's overview page.
    Two known patterns:
      /act-{act_id}/section-{section_id}.html
      /act-print-{act_id}/section-print-{section_id}.html
    """
    seen: set[str] = set()
    links: list[str] = []

    # Primary: anchors inside section.search-here (from Scrapy article)
    for a in s.select("section.search-here a[href], section a[href]"):
        href = a["href"]
        if re.search(r"section", href, re.I):
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url not in seen:
                seen.add(url)
                links.append(url)

    # Fallback: any anchor matching /section-\d+ pattern
    if not links:
        for a in s.find_all("a", href=re.compile(r"/section-\d+")):
            href = a["href"]
            url  = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url not in seen:
                seen.add(url)
                links.append(url)

    # Also prefer print URLs when available (cleaner HTML)
    if links:
        links = [
            re.sub(r"/section-(\d+)\.html$", r"/section-print-\1.html",
                   u.replace("/act-", "/act-print-", 1))
            if "/section-print-" not in u else u
            for u in links
        ]

    return links


def _fetch_section_pages(
    client: httpx.Client,
    urls: list[str],
) -> list[dict[str, Any]]:
    """Fetch each section sub-page and extract its content."""
    sections: list[dict[str, Any]] = []

    for url in urls:
        html = _fetch(client, url)
        if not html:
            continue

        s = _parse(html)

        # Section heading (col-sm-3) and body (col-sm-9) — from Scrapy article
        head_el = (
            s.select_one("div.col-sm-3.txt-head")
            or s.select_one(".section-no")
            or s.select_one(".section-head")
            or s.select_one("h3")
            or s.select_one("h4")
        )
        body_el = (
            s.select_one("div.col-sm-9.txt-details")
            or s.select_one(".section-body")
            or s.select_one(".section-content")
        )

        if not body_el:
            continue

        head  = _clean(head_el.get_text()) if head_el else ""
        paras = [_clean(p.get_text()) for p in body_el.find_all("p")
                 if _clean(p.get_text())]
        body  = " ".join(paras) if paras else _clean(body_el.get_text())

        if not body:
            continue

        sec_no, heading = _split_sec_head(head)
        chapter_el = s.select_one("p.act-chapter-name, .chapter-name, .chapter-head")
        chapter    = _clean(chapter_el.get_text()) if chapter_el else None

        sec: dict[str, Any] = {"section_no": sec_no, "heading": heading, "text": body}
        if chapter:
            sec["chapter"] = chapter
        sections.append(sec)

    return sections


# ══════════════════════════════════════════════════════════════════════════════
# Checkpoint system
# ══════════════════════════════════════════════════════════════════════════════

def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    """Return previously scraped acts keyed by act_id, or empty dict."""
    if path.exists():
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_checkpoint(path: Path, done: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)
    tmp.replace(path)   # atomic rename


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Scrape all acts from bdlaws.minlaw.gov.bd → JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--output", default="data/acts_full.json", metavar="PATH",
        help="Output JSON file (default: data/acts_full.json)",
    )
    ap.add_argument(
        "--checkpoint", default="data/.scrape_progress.json", metavar="PATH",
        help="Checkpoint file for resume support (default: data/.scrape_progress.json)",
    )
    ap.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Stop after N acts (smoke test)",
    )
    ap.add_argument(
        "--start-id", type=int, default=None, metavar="ID",
        help="Skip all acts whose numeric ID is below this value",
    )
    ap.add_argument(
        "--resume", action="store_true",
        help="Skip act IDs already present in the checkpoint file",
    )
    ap.add_argument(
        "--skip-sections", action="store_true",
        help="Collect only titles and years; do not scrape section content (fast)",
    )
    ap.add_argument(
        "--delay", type=float, default=REQUEST_DELAY, metavar="SECS",
        help=f"Seconds between HTTP requests (default: {REQUEST_DELAY})",
    )
    return ap


def main() -> None:
    global REQUEST_DELAY
    args = _build_parser().parse_args()

    # Propagate CLI delay into the module constant
    REQUEST_DELAY = args.delay

    output_path     = Path(args.output)
    checkpoint_path = Path(args.checkpoint)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = _make_client()

    # ── Phase 1: act list ────────────────────────────────────────────────────
    print("\n[Phase 1] Fetching act list…", flush=True)
    act_stubs = _scrape_act_list(client)
    print(f"  Act stubs: {len(act_stubs):,}", flush=True)

    # Apply --start-id filter
    if args.start_id:
        act_stubs = [a for a in act_stubs
                     if int(a["act_id"]) >= args.start_id]
        print(f"  After --start-id {args.start_id}: {len(act_stubs):,}", flush=True)

    # Apply --limit
    if args.limit:
        act_stubs = act_stubs[: args.limit]

    # ── Resume: load checkpoint ───────────────────────────────────────────────
    done: dict[str, dict[str, Any]] = {}
    if args.resume:
        done = _load_checkpoint(checkpoint_path)
        print(f"  Resuming: {len(done):,} acts already in checkpoint.", flush=True)

    # ── Phase 2: scrape each act ─────────────────────────────────────────────
    print("\n[Phase 2] Scraping acts…", flush=True)
    total      = len(act_stubs)
    scraped    = 0
    skipped    = 0
    failed     = 0
    start_time = time.monotonic()

    for i, stub in enumerate(act_stubs, 1):
        act_id = stub["act_id"]

        if args.resume and act_id in done:
            skipped += 1
            continue

        pct = i / total * 100
        elapsed = time.monotonic() - start_time
        rate    = scraped / elapsed if elapsed > 0 else 0
        eta_s   = (total - i) / rate if rate > 0 else 0
        eta_str = f"{eta_s / 60:.0f}m" if eta_s > 90 else f"{eta_s:.0f}s"

        print(
            f"  [{pct:5.1f}%] {i:>5}/{total}  act-{act_id:<6} "
            f"rate={rate:.1f}/s  ETA≈{eta_str}",
            end="  ", flush=True,
        )

        record = _scrape_act(client, act_id, skip_sections=args.skip_sections)

        if record:
            # Merge list-page title/year if act page couldn't determine them
            if not record["title"] and stub.get("title"):
                record["title"] = stub["title"]
            if not record["year"] and stub.get("year"):
                record["year"] = stub["year"]

            done[act_id] = record
            scraped += 1
            n_sec = len(record.get("sections") or [])
            print(f"✓  {record['title'][:55]!r}  ({n_sec} sections)", flush=True)
        else:
            failed += 1
            print("✗  not found / parse failed", flush=True)

        # Checkpoint every 25 acts
        if i % 25 == 0:
            _save_checkpoint(checkpoint_path, done)

    # Final checkpoint save
    _save_checkpoint(checkpoint_path, done)

    # ── Write output ─────────────────────────────────────────────────────────
    acts_list = sorted(done.values(), key=lambda a: int(a["act_id"]))
    print(f"\n[Phase 3] Writing {len(acts_list):,} acts to {output_path}…", flush=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(acts_list, f, ensure_ascii=False, indent=2)

    size_mb = output_path.stat().st_size / 1_048_576
    elapsed = time.monotonic() - start_time

    print(f"\n{'=' * 60}", flush=True)
    print(f"  Acts scraped   : {scraped:,}", flush=True)
    print(f"  Acts skipped   : {skipped:,}  (already in checkpoint)", flush=True)
    print(f"  Acts failed    : {failed:,}", flush=True)
    print(f"  Output size    : {size_mb:.1f} MB", flush=True)
    print(f"  Wall time      : {elapsed / 60:.1f} min", flush=True)
    print(f"  Output file    : {output_path.resolve()}", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"\nNext step:", flush=True)
    print(f"  python scripts/ingest_acts.py --from-file {output_path}", flush=True)


if __name__ == "__main__":
    main()
