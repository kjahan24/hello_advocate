#!/usr/bin/env python3
"""
ingest_acts.py — One-time Bangladesh legal acts import.

Recommended two-step workflow
------------------------------
  The HuggingFace `datasets` library fails on this dataset with:
    "Column() changed from object to string in row 0"
  Download the raw data first, then ingest from the local file:

    cd backend
    python scripts/download_dataset.py            # → data/acts.json
    python scripts/ingest_acts.py --from-file data/acts.json

  See download_dataset.py --help for options (--limit, --output, etc.)

Data source
-----------
  sakhadib/Bangladesh-Legal-Acts-Dataset (HuggingFace, CC-BY 4.0)
  1484+ acts scraped from bdlaws.minlaw.gov.bd

What it does
------------
  1. Reads raw act records from a local JSON file (--from-file)
  2. Parses flexible field names into typed ActRecord objects
  3. Upserts acts into PostgreSQL (safe to re-run)
  4. Deletes + re-inserts sections for every ingested act
  5. Generates 1536-dim OpenAI embeddings for all un-embedded sections
     in batches of --batch-size (default 50, as per CLAUDE.md §9)

All flags
---------
  python scripts/ingest_acts.py --from-file acts.json  # ingest local file
  python scripts/ingest_acts.py --limit 20             # first 20 acts (smoke test)
  python scripts/ingest_acts.py --skip-embeddings      # DB insert only
  python scripts/ingest_acts.py --force                # re-ingest existing acts
  python scripts/ingest_acts.py --show-schema          # print field names then exit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

# ── allow `from app.*` imports when run as a script ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.models.act import Act
from app.models.section import Section
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Category inference
# ══════════════════════════════════════════════════════════════════════════════

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "criminal": [
        "penal", "criminal", "crpc", "crime", "punishment", "offence", "offense",
        "arms", "explosive", "narcotic", "drug", "trafficking", "terrorism",
        "police", "prison", "jail", "extradition",
    ],
    "family": [
        "marriage", "matrimonial", "divorce", "dissolution", "family", "child",
        "guardian", "guardianship", "minority", "adoption", "succession",
        "inheritance", "dower", "dowry", "mahr", "polygamy", "personal law",
    ],
    "land_property": [
        "land", "immovable property", "registration", "revenue", "survey",
        "settlement", "acquisition", "cadastral", "khas land", "vested property",
    ],
    "labor_employment": [
        "labour", "labor", "employment", "worker", "workman", "factory",
        "shop establishment", "wage", "trade union", "provident fund",
        "gratuity", "maternity", "industrial relation",
    ],
    "constitutional": [
        "constitution", "election", "parliament", "representation", "referendum",
        "fundamental rights", "ordinance", "emergency", "national assembly",
    ],
    "commercial_business": [
        "company", "partnership", "trade mark", "copyright", "patent",
        "arbitration", "insolvency", "bankruptcy", "commerce", "mercantile",
        "specific relief", "contract act",
    ],
    "banking_finance": [
        "bank", "banking", "financial institution", "insurance",
        "currency", "reserve bank", "negotiable instrument", "cheque",
        "microfinance", "money laundering", "securities",
    ],
    "tenancy_rent": [
        "rent control", "urban tenancy", "premises", "eviction",
        "house rent", "rental",
    ],
    "consumer_rights": [
        "consumer protection", "food", "drug", "standard", "weights and measures",
        "pure food", "adulteration",
    ],
    "digital_cyber": [
        "digital", "cyber", "telecommunication", "information technology",
        "broadcasting", "wireless", "satellite", "electronic transaction",
        "data protection",
    ],
    "immigration": [
        "immigration", "passport", "foreigners", "aliens",
        "refugee", "citizenship", "nationality",
    ],
}


def infer_category(title: str, snippet: str = "") -> str:
    """Return the best-matching legal category for the act, defaulting to 'civil'."""
    haystack  = (title + " " + snippet[:600]).lower()
    best, hits = "civil", 0
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        n = sum(1 for kw in keywords if kw in haystack)
        if n > hits:
            best, hits = cat, n
    return best


# ══════════════════════════════════════════════════════════════════════════════
# Keyword extractor for the `sections.keywords` column
# ══════════════════════════════════════════════════════════════════════════════

_LEGAL_TERMS = [
    "punishment", "penalty", "imprisonment", "fine", "offence", "crime",
    "contract", "agreement", "damages", "breach", "liability",
    "property", "land", "registration", "deed",
    "marriage", "divorce", "inheritance", "custody",
    "employment", "wages", "termination",
    "rights", "fundamental", "constitution",
    "bank", "loan", "interest",
    "consumer", "refund",
    "digital", "cyber",
    "passport", "visa", "citizenship",
]


def _extract_keywords(content: str) -> List[str]:
    if not content:
        return []
    lower = content.lower()
    return [t for t in _LEGAL_TERMS if t in lower][:10]


# ══════════════════════════════════════════════════════════════════════════════
# Data records
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SectionRecord:
    section_number: Optional[str]
    title:          Optional[str]
    content_en:     Optional[str]
    keywords:       List[str] = field(default_factory=list)


@dataclass
class ActRecord:
    act_id:       str
    title_en:     str
    title_bn:     Optional[str]
    year:         Optional[int]
    category:     str
    source_url:   str
    full_text_en: Optional[str]
    is_repealed:  bool
    sections:     List[SectionRecord]


# ══════════════════════════════════════════════════════════════════════════════
# Record parsing — handles multiple field-name conventions
# ══════════════════════════════════════════════════════════════════════════════

def _first(d: Dict[str, Any], *keys: str) -> Any:
    """Return the value of the first existing, non-empty key."""
    for k in keys:
        v = d.get(k)
        if v is not None and v != "":
            return v
    return None


def _parse_year(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    m = re.search(r"(1[5-9]\d\d|20\d\d)", str(raw))
    return int(m.group(1)) if m else None


def _parse_sections(raw: Any) -> List[SectionRecord]:
    if not isinstance(raw, list):
        return []
    sections: List[SectionRecord] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        content = _first(s, "section_content", "text", "content", "body", "section_text", "description", "detail")
        if content:
            content = str(content).strip()
        title = _first(s, "heading", "title", "section_title", "name")
        if title:
            title = str(title).strip()
        sec_no = _first(s, "section_no", "section_number", "number", "no", "clause_no", "article_no", "sec")
        if sec_no:
            sec_no = str(sec_no).strip()
        # Skip entirely empty sections
        if not content and not title:
            continue
        sections.append(SectionRecord(
            section_number = sec_no,
            title          = title,
            content_en     = content,
            keywords       = _extract_keywords(content or ""),
        ))
    return sections


def parse_record(raw: Dict[str, Any], idx: int) -> Optional[ActRecord]:
    """
    Parse one raw dataset record.  Returns None to signal the record should
    be skipped (missing required fields).
    """
    act_id = _first(raw, "act_id", "id", "act_number", "number", "act_no", "serial")
    if act_id is None:
        logger.debug("skip_no_act_id", idx=idx)
        return None
    act_id = str(act_id).strip()

    title_en = _first(raw, "title", "act_title", "title_en", "name", "act_name", "short_title")
    if not title_en:
        logger.debug("skip_no_title", act_id=act_id)
        return None
    title_en = str(title_en).strip()

    title_bn    = _first(raw, "title_bn", "bangla_title", "bn_title", "title_bangla", "bengali_title")
    year        = _parse_year(_first(raw, "year", "act_year", "enacted_year", "enactment_year", "date", "date_enacted"))
    is_repealed = str(_first(raw, "is_repealed", "repealed", "status") or "").lower() in (
        "repealed", "true", "1", "yes",
    )

    raw_sections = _first(raw, "sections", "clauses", "articles", "provisions", "sub_sections")
    sections     = _parse_sections(raw_sections or [])

    # Fallback full text: concatenate section bodies
    full_text_en = _first(raw, "full_text", "full_text_en", "act_text", "body", "content")
    if not full_text_en and sections:
        full_text_en = "\n\n".join(s.content_en for s in sections if s.content_en)
    if full_text_en:
        full_text_en = str(full_text_en).strip() or None

    source_url = _first(raw, "source_url", "url", "link", "source")
    if not source_url:
        source_url = f"https://bdlaws.minlaw.gov.bd/act-{act_id}.html"

    category = infer_category(title_en, full_text_en or "")

    return ActRecord(
        act_id       = act_id,
        title_en     = title_en,
        title_bn     = str(title_bn).strip() if title_bn else None,
        year         = year,
        category     = category,
        source_url   = source_url,
        full_text_en = full_text_en,
        is_repealed  = is_repealed,
        sections     = sections,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Dataset loading
# ══════════════════════════════════════════════════════════════════════════════

def _iter_local_file(path: str, limit: Optional[int]) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with p.open(encoding="utf-8") as fh:
        first_char = fh.read(1)
        fh.seek(0)
        if first_char == "[":
            # Flat JSON array — most common output from download_dataset.py
            for i, rec in enumerate(json.load(fh)):
                if limit and i >= limit:
                    break
                yield rec
        elif first_char == "{":
            # Wrapper object: {"dataset_info": ..., "acts": [...]}
            data = json.load(fh)
            acts = data.get("acts", [data]) if isinstance(data, dict) else [data]
            for i, rec in enumerate(acts):
                if limit and i >= limit:
                    break
                yield rec
        else:                          # JSONL
            for i, line in enumerate(fh):
                if limit and i >= limit:
                    break
                line = line.strip()
                if line:
                    yield json.loads(line)


# Confirmed working URL (HEAD 200, 2026-06-10):
_HF_JSON_URL = (
    "https://huggingface.co/datasets/{dataset_name}/resolve/main/"
    "Contextualized_Bangladesh_Legal_Acts.json"
)


def _iter_json_fallback(
    dataset_name: str, limit: Optional[int]
) -> Iterator[Dict[str, Any]]:
    """
    Fallback: download the raw JSON from HuggingFace CDN via requests.

    File structure (confirmed 2026-06-10):
        {"dataset_info": {...}, "acts": [ 1484 dicts ... ]}

    Each act has keys:
        act_title, act_no, act_year, sections[].section_content,
        source_url, footnotes[].footnote_text, language, token_count, ...
    """
    try:
        import requests as _req  # type: ignore[import]
    except ImportError:
        print(
            "\nERROR: 'requests' not installed. Install it with:\n"
            "  pip install requests\n"
            "Or use the two-step approach:\n"
            "  python scripts/download_dataset.py\n"
            "  python scripts/ingest_acts.py --from-file data/acts.json\n",
            file=sys.stderr,
        )
        sys.exit(1)

    url = _HF_JSON_URL.format(dataset_name=dataset_name)
    print(f"  Fetching JSON: {url}", flush=True)
    try:
        r = _req.get(url, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"\nERROR: JSON download failed: {exc}", flush=True)
        print(
            "Use the two-step approach:\n"
            "  python scripts/download_dataset.py\n"
            "  python scripts/ingest_acts.py --from-file data/acts.json\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Unwrap {"dataset_info": ..., "acts": [...]} or accept plain list
    if isinstance(data, dict) and "acts" in data:
        acts: List[Any] = data["acts"]
    elif isinstance(data, list):
        acts = data
    else:
        print(
            f"\nERROR: Unexpected JSON structure ({type(data).__name__}). "
            "Expected dict with 'acts' key or a list.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    total = min(len(acts), limit) if limit else len(acts)
    print(f"  {total:,} acts loaded ({len(acts):,} total in file).", flush=True)

    for i, act in enumerate(acts):
        if limit and i >= limit:
            break
        yield dict(act)


def _iter_huggingface(
    dataset_name: str, split: str, limit: Optional[int]
) -> Iterator[Dict[str, Any]]:
    print(f"Downloading {dataset_name} ({split}) from HuggingFace…", flush=True)

    # ── Attempt 1: datasets library with trust_remote_code ────────────────────
    try:
        from datasets import load_dataset  # type: ignore[import]
        print("  Trying datasets library (trust_remote_code=True)…", flush=True)
        ds    = load_dataset(dataset_name, split=split, trust_remote_code=True)
        total = min(len(ds), limit) if limit else len(ds)
        print(f"  Loaded {total:,} records via datasets library.", flush=True)
        for i, rec in enumerate(ds):
            if limit and i >= limit:
                break
            yield dict(rec)
        return
    except ImportError:
        print("  'datasets' not installed — trying direct JSON download.", flush=True)
    except Exception as exc:
        print(
            f"  datasets library failed ({type(exc).__name__}): {exc}\n"
            "  Falling back to direct JSON download…",
            flush=True,
        )

    # ── Attempt 2: direct JSON via requests ───────────────────────────────────
    yield from _iter_json_fallback(dataset_name, limit)


# ══════════════════════════════════════════════════════════════════════════════
# Database operations
# ══════════════════════════════════════════════════════════════════════════════

async def upsert_act(record: ActRecord, db: AsyncSession) -> Act:
    """Insert or update one Act row; return the Act ORM object."""
    stmt = (
        pg_insert(Act)
        .values(
            act_id       = record.act_id,
            title_en     = record.title_en,
            title_bn     = record.title_bn,
            year         = record.year,
            category     = record.category,
            is_repealed  = record.is_repealed,
            full_text_en = record.full_text_en,
            source_url   = record.source_url,
        )
        .on_conflict_do_update(
            index_elements = ["act_id"],
            set_ = {
                "title_en":     pg_insert(Act).excluded.title_en,
                "title_bn":     pg_insert(Act).excluded.title_bn,
                "year":         pg_insert(Act).excluded.year,
                "category":     pg_insert(Act).excluded.category,
                "is_repealed":  pg_insert(Act).excluded.is_repealed,
                "full_text_en": pg_insert(Act).excluded.full_text_en,
                "source_url":   pg_insert(Act).excluded.source_url,
            },
        )
    )
    await db.execute(stmt)

    result = await db.execute(select(Act).where(Act.act_id == record.act_id))
    return result.scalar_one()


async def replace_sections(
    act: Act, sections: List[SectionRecord], db: AsyncSession
) -> int:
    """Delete all existing sections for the act and re-insert them."""
    await db.execute(delete(Section).where(Section.act_id == act.id))
    if not sections:
        return 0
    db.add_all([
        Section(
            act_id         = act.id,
            section_number = s.section_number,
            title          = s.title,
            content_en     = s.content_en,
            keywords       = s.keywords or None,
        )
        for s in sections
    ])
    return len(sections)


# ══════════════════════════════════════════════════════════════════════════════
# Embedding generation
# ══════════════════════════════════════════════════════════════════════════════

def _embed_text(
    act_title:      str,
    section_number: Optional[str],
    section_title:  Optional[str],
    content:        Optional[str],
) -> str:
    """
    Build the text to embed for one section.

    Format: "<Act Title>, Section N: <Title>\n\n<content (up to 6 000 chars)>"
    Keeps the header compact so the model captures the legal context immediately.
    """
    header = act_title
    if section_number:
        header += f", Section {section_number}"
    if section_title:
        header += f": {section_title}"
    body = (content or "")[:6_000]        # ~1 500 tokens; well within model limit
    return f"{header}\n\n{body}".strip()


async def generate_embeddings(
    db:            AsyncSession,
    embedding_svc: EmbeddingService,
    batch_size:    int,
) -> None:
    """Embed all sections with a NULL embedding column and persist them."""
    rows_result = await db.execute(
        text("""
            SELECT s.id, s.section_number, s.title, s.content_en,
                   a.title_en AS act_title
            FROM   sections s
            JOIN   acts     a ON s.act_id = a.id
            WHERE  s.embedding IS NULL
              AND  s.content_en IS NOT NULL
            ORDER  BY s.id
        """)
    )
    rows = rows_result.fetchall()

    if not rows:
        print("  No un-embedded sections found — nothing to do.", flush=True)
        return

    total   = len(rows)
    n_batches = (total + batch_size - 1) // batch_size
    done    = 0

    # Rough cost estimate: text-embedding-3-small = $0.02 / 1M tokens
    # Average ~500 tokens per section
    est_tokens = total * 500
    est_cost   = est_tokens / 1_000_000 * 0.02
    print(
        f"  Sections to embed : {total:,}\n"
        f"  Batches           : {n_batches} × {batch_size}\n"
        f"  Estimated cost    : ~${est_cost:.4f} (text-embedding-3-small)",
        flush=True,
    )

    for batch_start in range(0, total, batch_size):
        batch  = rows[batch_start : batch_start + batch_size]
        texts  = [
            _embed_text(r.act_title, r.section_number, r.title, r.content_en)
            for r in batch
        ]
        embeddings = await embedding_svc.embed_batch(texts)

        for row, emb in zip(batch, embeddings):
            emb_literal = "[" + ",".join(f"{v:.8f}" for v in emb) + "]"
            await db.execute(
                text("UPDATE sections SET embedding = CAST(:emb AS vector) WHERE id = :id"),
                {"emb": emb_literal, "id": str(row.id)},
            )

        await db.commit()
        done += len(batch)
        pct   = done / total * 100
        batch_num = batch_start // batch_size + 1
        print(
            f"  [{pct:5.1f}%] batch {batch_num}/{n_batches} — {done:,}/{total:,} done",
            flush=True,
        )

    print(f"  Embedding generation complete: {done:,} sections.", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    ap = argparse.ArgumentParser(
        description="Ingest Bangladesh legal acts into the AI Lawyer database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--dataset",
        default="sakhadib/Bangladesh-Legal-Acts-Dataset",
        metavar="HF_DATASET",
        help="HuggingFace dataset identifier (default: sakhadib/Bangladesh-Legal-Acts-Dataset)",
    )
    ap.add_argument(
        "--split",
        default="train",
        help="Dataset split to load (default: train)",
    )
    ap.add_argument(
        "--from-file",
        metavar="PATH",
        help="Load from a local JSON array or JSONL file instead of HuggingFace",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N acts (useful for smoke-testing)",
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=50,
        metavar="N",
        help="Embedding batch size (default: 50, as per CLAUDE.md §9)",
    )
    ap.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Insert acts and sections only; skip embedding generation",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest acts that are already in the database",
    )
    ap.add_argument(
        "--show-schema",
        action="store_true",
        help="Print the first raw record's field names and exit (for debugging)",
    )
    args = ap.parse_args()

    # ── Choose data source ────────────────────────────────────────────────────
    if args.from_file:
        raw_iter: Iterator[Dict[str, Any]] = _iter_local_file(args.from_file, args.limit)
    else:
        raw_iter = _iter_huggingface(args.dataset, args.split, args.limit)

    # ── Schema preview mode ───────────────────────────────────────────────────
    if args.show_schema:
        first = next(iter(raw_iter), None)
        if first:
            print("\nField names and sample values (first record):")
            for k, v in list(first.items())[:25]:
                sample = str(v)[:120].replace("\n", " ")
                print(f"  {k!r:30s}: {sample!r}")
        else:
            print("Dataset appears to be empty.")
        return

    # ── Parse all records ─────────────────────────────────────────────────────
    print("Parsing records…", flush=True)
    records: List[ActRecord] = []
    skipped = 0
    for i, raw in enumerate(raw_iter):
        parsed = parse_record(raw, i)
        if parsed:
            records.append(parsed)
        else:
            skipped += 1

    print(
        f"Parsed {len(records):,} valid acts"
        f" ({skipped} skipped due to missing required fields).",
        flush=True,
    )
    if not records:
        print("Nothing to ingest — exiting.")
        return

    # Category breakdown
    from collections import Counter
    cats = Counter(r.category for r in records)
    print("Category breakdown:")
    for cat, count in cats.most_common():
        print(f"  {cat:<25} {count:>5}")

    # ── DB ingestion ──────────────────────────────────────────────────────────
    print(f"\nIngesting into PostgreSQL…", flush=True)
    acts_new      = 0
    acts_updated  = 0
    acts_skipped  = 0
    total_sections = 0
    COMMIT_EVERY  = 50

    async with AsyncSessionLocal() as db:
        for i, record in enumerate(records, 1):
            # Check existence
            exists_result = await db.execute(
                select(Act.id).where(Act.act_id == record.act_id)
            )
            already_exists = exists_result.scalar_one_or_none() is not None

            if already_exists and not args.force:
                acts_skipped += 1
            else:
                act            = await upsert_act(record, db)
                n              = await replace_sections(act, record.sections, db)
                total_sections += n
                if already_exists:
                    acts_updated += 1
                else:
                    acts_new += 1

            if i % COMMIT_EVERY == 0:
                await db.commit()
                pct = i / len(records) * 100
                print(f"  [{pct:5.1f}%] {i:,}/{len(records):,} acts processed…", flush=True)

        await db.commit()

    print(
        f"\nIngestion complete:"
        f"\n  Acts inserted  : {acts_new:,}"
        f"\n  Acts updated   : {acts_updated:,}"
        f"\n  Acts skipped   : {acts_skipped:,}  (already exist; use --force to re-ingest)"
        f"\n  Sections total : {total_sections:,}",
        flush=True,
    )

    # ── Embedding generation ──────────────────────────────────────────────────
    if args.skip_embeddings:
        print("\nEmbedding generation skipped (--skip-embeddings).", flush=True)
        return

    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        print(
            "\nWARNING: OPENAI_API_KEY is not set — skipping embedding generation.\n"
            "Set it in .env then re-run without --skip-embeddings.",
            flush=True,
        )
        return

    print("\nGenerating embeddings…", flush=True)
    embedding_svc = EmbeddingService.create()
    async with AsyncSessionLocal() as db:
        await generate_embeddings(db, embedding_svc, args.batch_size)

    print("\nAll done.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
