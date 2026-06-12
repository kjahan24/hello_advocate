"""
QueryRouter — maps IntentResult → DB retrieval strategy → QueryResult.

Strategy table (CLAUDE.md §6):
  FIND_SECTION   → exact match on section_number
  FIND_LAW       → hybrid RRF (vector top-20 + keyword ILIKE top-20 → re-rank top-5)
  EXPLAIN_RIGHTS → hybrid RRF
  FIND_CASE      → vector search on cases table
  CHECK_PROCESS  → hybrid RRF
  COMPARE_LAWS   → two vector searches (filtered + unfiltered), merged
  GET_DOCUMENT   → PostgreSQL full-text search (ts_rank)
  GENERAL_INFO   → no DB query (LLM answers from training knowledge)
  UNKNOWN        → no DB query
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intent_detector import Category, Intent, IntentResult

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SourceItem:
    source_type:    str             # "section" | "case"
    relevance_score: float = 1.0
    # Section fields
    act_title_en:   str            = ""
    act_id:         str            = ""
    category:       str            = ""
    year:           Optional[int]  = None
    section_number: Optional[str]  = None
    section_title:  Optional[str]  = None
    content_en:     Optional[str]  = None
    content_bn:     Optional[str]  = None
    section_db_id:  Optional[str]  = None  # internal dedup key
    # Case fields
    citation:       Optional[str]  = None
    court:          Optional[str]  = None
    parties:        Optional[str]  = None
    summary:        Optional[str]  = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "section_db_id"}


@dataclass
class QueryResult:
    sources:   List[SourceItem]
    strategy:  str
    needs_llm: bool = True   # always True — RAG pipeline always calls Claude


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_TOP_K  = 8
_COMPARE_TOP_K  = 10   # per sub-search; merged result is up to 20
_HYBRID_TOP_K   = 6    # legacy hybrid per sub-search
_RRF_VECTOR_K   = 20   # vector leg for RRF
_RRF_KEYWORD_K  = 20   # keyword leg for RRF
_RRF_FINAL_K    = 5    # top-N returned after re-ranking
_MIN_SCORE      = 0.30
_RRF_K          = 60   # RRF constant

_SECTION_NUM_RE = re.compile(
    r"(?:ধারা|অনুচ্ছেদ|উপধারা|section|sec\.|article|clause)\s*([০-৯\d]+[ক-হa-zA-Z]?)",
    re.IGNORECASE,
)

# ──────────────────────────────────────────────────────────────────────────────
# SQL templates
# The embedding is always bound as a pre-formatted string and cast via ::vector.
# All other values are bound parameters — no raw user input is concatenated.
# ──────────────────────────────────────────────────────────────────────────────

# Columns shared by every section SELECT
_SECTION_COLS = """
    s.id            AS section_db_id,
    a.title_en,
    a.category,
    a.year,
    a.act_id,
    s.section_number,
    s.title         AS section_title,
    s.content_en,
    s.content_bn
"""

_VECTOR_FILTERED_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        1 - (s.embedding <=> :embedding::vector) AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed = FALSE
      AND a.category    = :category
      AND 1 - (s.embedding <=> :embedding::vector) > :min_score
    ORDER BY s.embedding <=> :embedding::vector
    LIMIT :top_k
""")

_VECTOR_UNFILTERED_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        1 - (s.embedding <=> :embedding::vector) AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed = FALSE
      AND 1 - (s.embedding <=> :embedding::vector) > :min_score
    ORDER BY s.embedding <=> :embedding::vector
    LIMIT :top_k
""")

_FIND_SECTION_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        1.0 AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed  = FALSE
      AND s.section_number = :section_number
    ORDER BY a.year DESC
    LIMIT :top_k
""")

_FIND_SECTION_FUZZY_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        1.0 AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed  = FALSE
      AND s.section_number ILIKE :section_pattern
    ORDER BY a.year DESC
    LIMIT :top_k
""")

_FTS_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        ts_rank(
            to_tsvector('english', coalesce(s.content_en, '')),
            plainto_tsquery('english', :fts_query)
        ) AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed = FALSE
      AND to_tsvector('english', coalesce(s.content_en, ''))
          @@ plainto_tsquery('english', :fts_query)
    ORDER BY relevance_score DESC
    LIMIT :top_k
""")

_FTS_FILTERED_SQL = text(f"""
    SELECT
        {_SECTION_COLS},
        ts_rank(
            to_tsvector('english', coalesce(s.content_en, '')),
            plainto_tsquery('english', :fts_query)
        ) AS relevance_score
    FROM sections s
    JOIN acts a ON s.act_id = a.id
    WHERE a.is_repealed = FALSE
      AND a.category    = :category
      AND to_tsvector('english', coalesce(s.content_en, ''))
          @@ plainto_tsquery('english', :fts_query)
    ORDER BY relevance_score DESC
    LIMIT :top_k
""")

_CASE_VECTOR_SQL = text("""
    SELECT
        c.id            AS case_db_id,
        c.citation,
        c.court,
        c.year,
        c.parties,
        c.summary,
        1 - (c.embedding <=> :embedding::vector) AS relevance_score
    FROM cases c
    WHERE 1 - (c.embedding <=> :embedding::vector) > :min_score
    ORDER BY c.embedding <=> :embedding::vector
    LIMIT :top_k
""")

# ──────────────────────────────────────────────────────────────────────────────
# Dynamic SQL builder for keyword ILIKE search
# Parameter names :kw0, :kw1, ... are controlled by our code, not user input.
# Actual values are bound parameters — no SQL injection risk.
# ──────────────────────────────────────────────────────────────────────────────

def _build_keyword_sql(n_terms: int, filtered: bool) -> Any:
    """Build ILIKE keyword search SQL with n bound parameters :kw0..:kw{n-1}.

    Results are ranked by length-normalised ts_rank (flag=1) so that short,
    focused sections (e.g. "Section 379. Whoever commits theft shall be
    punished…") score higher than long omnibus sections that merely mention
    the keyword in passing.
    """
    conds = " OR ".join(
        f"s.content_en ILIKE :kw{i} OR s.content_bn ILIKE :kw{i}"
        for i in range(n_terms)
    )
    cat_clause = "AND a.category = :category" if filtered else ""
    return text(f"""
        SELECT
            {_SECTION_COLS},
            ts_rank(
                to_tsvector('english', coalesce(s.content_en, '')),
                plainto_tsquery('english', :fts_terms),
                1
            ) AS relevance_score
        FROM sections s
        JOIN acts a ON s.act_id = a.id
        WHERE a.is_repealed = FALSE
          {cat_clause}
          AND ({conds})
        ORDER BY relevance_score DESC, a.year DESC NULLS LAST
        LIMIT :top_k
    """)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_embedding(embedding: List[float]) -> str:
    """Serialize a float list to pgvector literal '[x,y,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


def _extract_section_number(query: str) -> Optional[str]:
    m = _SECTION_NUM_RE.search(query)
    return m.group(1) if m else None


def _row_to_section(row: Any) -> SourceItem:
    return SourceItem(
        source_type    = "section",
        act_title_en   = row.title_en or "",
        act_id         = row.act_id or "",
        category       = row.category or "",
        year           = row.year,
        section_number = row.section_number,
        section_title  = row.section_title,
        content_en     = row.content_en,
        content_bn     = row.content_bn,
        relevance_score= float(row.relevance_score),
        section_db_id  = str(row.section_db_id),
    )


def _row_to_case(row: Any) -> SourceItem:
    return SourceItem(
        source_type    = "case",
        relevance_score= float(row.relevance_score),
        citation       = row.citation,
        court          = row.court,
        year           = row.year,
        parties        = row.parties,
        summary        = row.summary,
    )


def _dedup_sections(items: List[SourceItem]) -> List[SourceItem]:
    """Deduplicate by section_db_id, keeping the highest relevance score."""
    seen: Dict[str, SourceItem] = {}
    for item in items:
        key = item.section_db_id or f"{item.act_id}:{item.section_number}"
        if key not in seen or item.relevance_score > seen[key].relevance_score:
            seen[key] = item
    return sorted(seen.values(), key=lambda x: x.relevance_score, reverse=True)


def _item_key(item: SourceItem) -> str:
    return item.section_db_id or f"{item.act_id}:{item.section_number}"


def _rrf_combine(
    vector_items: List[SourceItem],
    keyword_items: List[SourceItem],
    rrf_k: int = _RRF_K,
) -> List[Tuple[str, float, SourceItem]]:
    """Combine two ranked lists using Reciprocal Rank Fusion."""
    # Merge unique items (highest score wins on collision)
    all_items: Dict[str, SourceItem] = {}
    for item in vector_items + keyword_items:
        key = _item_key(item)
        if key not in all_items or item.relevance_score > all_items[key].relevance_score:
            all_items[key] = item

    v_ranks = {_item_key(item): i + 1 for i, item in enumerate(vector_items)}
    k_ranks = {_item_key(item): i + 1 for i, item in enumerate(keyword_items)}

    scored: List[Tuple[str, float, SourceItem]] = []
    for key, item in all_items.items():
        v_r = v_ranks.get(key, len(vector_items) + rrf_k)
        k_r = k_ranks.get(key, len(keyword_items) + rrf_k)
        rrf_score = 1.0 / (v_r + rrf_k) + 1.0 / (k_r + rrf_k)
        scored.append((key, rrf_score, item))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _rerank(
    rrf_scored: List[Tuple[str, float, SourceItem]],
    query: str,
    top_n: int = _RRF_FINAL_K,
) -> List[SourceItem]:
    """Apply re-ranking bonuses to the top-10 RRF results and return top_n."""
    query_lower = query.lower()
    query_words = {w for w in query_lower.split() if len(w) > 2}

    final: List[Tuple[float, SourceItem]] = []
    for _key, rrf_score, item in rrf_scored:
        bonus = 0.0
        content = (item.content_en or "").lower() + " " + (item.content_bn or "").lower()

        # Exact phrase match in content
        if len(query_lower) > 4 and query_lower in content:
            bonus += 0.3
        # Law name match: any significant query word found in act title
        act_title_lower = (item.act_title_en or "").lower()
        if any(w in act_title_lower for w in query_words if len(w) > 3):
            bonus += 0.2
        # Recent law bonus
        if item.year and item.year >= 2000:
            bonus += 0.1

        final_score = rrf_score + bonus
        item.relevance_score = round(final_score, 4)
        final.append((final_score, item))

    final.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in final[:top_n]]


# ──────────────────────────────────────────────────────────────────────────────
# QueryRouter
# ──────────────────────────────────────────────────────────────────────────────

class QueryRouter:
    """
    Routes an IntentResult to the correct DB strategy and returns a QueryResult
    containing ranked SourceItems ready to be injected into the RAG prompt.

    All DB calls are async; callers must pass a live AsyncSession.
    The `embedding` parameter is the pre-computed query embedding (1536-dim).
    The `expanded_terms` parameter is the query-expanded synonym list from QueryExpander.
    """

    async def route(
        self,
        intent:         IntentResult,
        query:          str,
        embedding:      Optional[List[float]],
        db:             AsyncSession,
        expanded_terms: Optional[List[str]] = None,
        fts_terms:      Optional[str]       = None,
    ) -> QueryResult:
        log = logger.bind(intent=intent.intent, category=intent.category, query=query[:60])
        log.info("query_routing")

        terms    = expanded_terms or [query]
        fts      = fts_terms or "law"

        match intent.intent:
            case Intent.FIND_SECTION:
                return await self._find_section(query, embedding, intent.category, db, terms, fts)
            case Intent.FIND_LAW:
                return await self._rrf_search(query, terms, intent.category, embedding, db,
                                               "rrf_find_law", fts)
            case Intent.EXPLAIN_RIGHTS:
                return await self._rrf_search(query, terms, intent.category, embedding, db,
                                               "rrf_explain_rights", fts)
            case Intent.FIND_CASE:
                return await self._find_case(embedding, db)
            case Intent.CHECK_PROCESS:
                return await self._rrf_search(query, terms, intent.category, embedding, db,
                                               "rrf_check_process", fts)
            case Intent.COMPARE_LAWS:
                return await self._compare_search(intent.category, embedding, db)
            case Intent.GET_DOCUMENT:
                return await self._fulltext_search(query, db)
            case Intent.GENERAL_INFO | Intent.UNKNOWN:
                return QueryResult(sources=[], strategy=intent.intent.value, needs_llm=True)
            case _:
                return QueryResult(sources=[], strategy="unknown", needs_llm=True)

    # ── FIND_SECTION ──────────────────────────────────────────────────────────

    async def _find_section(
        self,
        query:          str,
        embedding:      Optional[List[float]],
        category:       Category,
        db:             AsyncSession,
        expanded_terms: List[str],
        fts_terms:      str = "law",
    ) -> QueryResult:
        section_num = _extract_section_number(query)

        if section_num:
            result = await db.execute(
                _FIND_SECTION_SQL,
                {"section_number": section_num, "top_k": _DEFAULT_TOP_K},
            )
            rows = result.fetchall()

            if not rows:
                result = await db.execute(
                    _FIND_SECTION_FUZZY_SQL,
                    {"section_pattern": f"%{section_num}%", "top_k": _DEFAULT_TOP_K},
                )
                rows = result.fetchall()

            if rows:
                return QueryResult(
                    sources=[_row_to_section(r) for r in rows],
                    strategy="exact_section",
                )

        # No section number found — fall back to RRF hybrid
        return await self._rrf_search(query, expanded_terms, category, embedding, db,
                                       "exact_section_fallback_rrf", fts_terms)

    # ── FIND_CASE ─────────────────────────────────────────────────────────────

    async def _find_case(
        self,
        embedding: Optional[List[float]],
        db:        AsyncSession,
    ) -> QueryResult:
        if not embedding:
            return QueryResult(sources=[], strategy="case_vector_no_embedding")

        emb_str = _fmt_embedding(embedding)
        result  = await db.execute(
            _CASE_VECTOR_SQL,
            {"embedding": emb_str, "min_score": _MIN_SCORE, "top_k": _DEFAULT_TOP_K},
        )
        sources = [_row_to_case(r) for r in result.fetchall()]
        return QueryResult(sources=sources, strategy="case_vector")

    # ── COMPARE_LAWS — two vector searches, merged ────────────────────────────

    async def _compare_search(
        self,
        category:  Category,
        embedding: Optional[List[float]],
        db:        AsyncSession,
    ) -> QueryResult:
        if not embedding:
            return QueryResult(sources=[], strategy="compare_no_embedding")

        emb_str  = _fmt_embedding(embedding)

        filtered   = await self._vector_search(category, embedding, db, _COMPARE_TOP_K)
        unfiltered_result = await db.execute(
            _VECTOR_UNFILTERED_SQL,
            {"embedding": emb_str, "min_score": _MIN_SCORE, "top_k": _COMPARE_TOP_K},
        )
        unfiltered = [_row_to_section(r) for r in unfiltered_result.fetchall()]

        merged = _dedup_sections(filtered + unfiltered)
        return QueryResult(sources=merged[:_COMPARE_TOP_K], strategy="compare_multi_vector")

    # ── GET_DOCUMENT — full-text search ───────────────────────────────────────

    async def _fulltext_search(
        self,
        query: str,
        db:    AsyncSession,
    ) -> QueryResult:
        try:
            result = await db.execute(
                _FTS_SQL,
                {"fts_query": query, "top_k": _DEFAULT_TOP_K},
            )
            rows    = result.fetchall()
            sources = [_row_to_section(r) for r in rows]
        except Exception as exc:
            logger.warning("fts_failed", error=str(exc))
            sources = []

        return QueryResult(sources=sources, strategy="fulltext")

    # ── RRF hybrid search (vector + keyword ILIKE + re-rank) ──────────────────

    async def _rrf_search(
        self,
        query:          str,
        expanded_terms: List[str],
        category:       Category,
        embedding:      Optional[List[float]],
        db:             AsyncSession,
        strategy_name:  str = "rrf_hybrid",
        fts_terms:      str = "law",
    ) -> QueryResult:
        """
        Hybrid search:
          1. Vector search (top 20) filtered by category
          2. Keyword ILIKE search (top 20) on expanded_terms
          3. Reciprocal Rank Fusion combining both lists
          4. Re-ranking bonuses (phrase match, law name, recency)
          5. Return top 5

        Falls back to unfiltered vector search if both legs return nothing.
        """
        vector_items:  List[SourceItem] = []
        keyword_items: List[SourceItem] = []

        # ── Vector leg ──
        if embedding:
            emb_str = _fmt_embedding(embedding)
            try:
                res = await db.execute(
                    _VECTOR_FILTERED_SQL,
                    {
                        "embedding": emb_str,
                        "category":  category.value,
                        "min_score": _MIN_SCORE,
                        "top_k":     _RRF_VECTOR_K,
                    },
                )
                vector_items = [_row_to_section(r) for r in res.fetchall()]
            except Exception as exc:
                logger.warning("rrf_vector_failed", error=str(exc))
                # A failed PG query aborts the transaction; rollback so the
                # keyword leg can run in a fresh implicit transaction.
                try:
                    await db.rollback()
                except Exception:
                    pass

        # ── Keyword ILIKE leg ──
        kw_patterns = [f"%{t}%" for t in expanded_terms if t.strip()][:6]
        if kw_patterns:
            try:
                kw_sql = _build_keyword_sql(len(kw_patterns), filtered=True)
                params: Dict[str, Any] = {"top_k": _RRF_KEYWORD_K, "category": category.value, "fts_terms": fts_terms}
                for i, kw in enumerate(kw_patterns):
                    params[f"kw{i}"] = kw
                res = await db.execute(kw_sql, params)
                keyword_items = [_row_to_section(r) for r in res.fetchall()]
            except Exception as exc:
                logger.warning("rrf_keyword_failed", error=str(exc))
                try:
                    await db.rollback()
                except Exception:
                    pass

        # ── Unfiltered keyword fallback: if category filter killed results ──
        if not keyword_items and kw_patterns:
            try:
                kw_sql = _build_keyword_sql(len(kw_patterns), filtered=False)
                params2: Dict[str, Any] = {"top_k": _RRF_KEYWORD_K, "fts_terms": fts_terms}
                for i, kw in enumerate(kw_patterns):
                    params2[f"kw{i}"] = kw
                res = await db.execute(kw_sql, params2)
                keyword_items = [_row_to_section(r) for r in res.fetchall()]
                logger.debug("rrf_keyword_unfiltered_fallback", count=len(keyword_items))
            except Exception as exc:
                logger.warning("rrf_keyword_unfiltered_failed", error=str(exc))
                try:
                    await db.rollback()
                except Exception:
                    pass

        # ── Fallback: unfiltered vector if both legs still empty ──
        if not vector_items and not keyword_items:
            if embedding:
                emb_str = _fmt_embedding(embedding)
                try:
                    res = await db.execute(
                        _VECTOR_UNFILTERED_SQL,
                        {"embedding": emb_str, "min_score": _MIN_SCORE - 0.1, "top_k": 8},
                    )
                    return QueryResult(
                        sources=[_row_to_section(r) for r in res.fetchall()],
                        strategy=f"{strategy_name}_fallback_unfiltered",
                    )
                except Exception:
                    pass
            return QueryResult(sources=[], strategy=f"{strategy_name}_no_results")

        # ── RRF combination ──
        rrf_scored = _rrf_combine(vector_items, keyword_items)

        # ── Re-ranking ──
        top_sources = _rerank(rrf_scored, query, top_n=_RRF_FINAL_K)

        logger.debug(
            "rrf_complete",
            strategy=strategy_name,
            vector_count=len(vector_items),
            keyword_count=len(keyword_items),
            final_count=len(top_sources),
        )
        return QueryResult(sources=top_sources, strategy=strategy_name)

    # ── Shared vector search helper ───────────────────────────────────────────

    async def _vector_search(
        self,
        category:  Category,
        embedding: List[float],
        db:        AsyncSession,
        top_k:     int = _DEFAULT_TOP_K,
    ) -> List[SourceItem]:
        emb_str = _fmt_embedding(embedding)
        result  = await db.execute(
            _VECTOR_FILTERED_SQL,
            {
                "embedding": emb_str,
                "category":  category.value,
                "min_score": _MIN_SCORE,
                "top_k":     top_k,
            },
        )
        return [_row_to_section(r) for r in result.fetchall()]

    async def _vector_search_result(
        self,
        category:  Category,
        embedding: Optional[List[float]],
        db:        AsyncSession,
        strategy:  str,
    ) -> QueryResult:
        if not embedding:
            return QueryResult(sources=[], strategy=f"{strategy}_no_embedding")
        sources = await self._vector_search(category, embedding, db, _DEFAULT_TOP_K)
        return QueryResult(sources=sources, strategy=strategy)
