"""
Unit tests for QueryRouter.

The AsyncSession is mocked; no real DB is needed.
Each test exercises one strategy path and asserts:
  - the correct SQL was executed (via mock call inspection)
  - the returned QueryResult has the expected strategy and source count
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intent_detector import Category, Intent, IntentResult
from app.services.query_router import (
    QueryResult,
    QueryRouter,
    SourceItem,
    _dedup_sections,
    _extract_section_number,
    _fmt_embedding,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

DUMMY_EMBEDDING: List[float] = [0.1] * 1536


def _intent(
    intent: Intent,
    category: Category = Category.CRIMINAL,
    language: str = "en",
) -> IntentResult:
    return IntentResult(
        intent=intent,
        category=category,
        confidence=0.9,
        language=language,
        key_concepts=[],
        stage=1,
    )


def _make_section_row(**kwargs: Any) -> SimpleNamespace:
    defaults = dict(
        section_db_id="aaaaaaaa-0000-0000-0000-000000000001",
        title_en="Penal Code 1860",
        category="criminal",
        year=1860,
        act_id="A001",
        section_number="379",
        section_title="Theft",
        content_en="Whoever commits theft...",
        content_bn=None,
        relevance_score=0.85,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_case_row(**kwargs: Any) -> SimpleNamespace:
    defaults = dict(
        case_db_id="bbbbbbbb-0000-0000-0000-000000000001",
        citation="2020 DLR 100",
        court="High Court Division",
        year=2020,
        parties="Rahim v State",
        summary="Judgment on theft case.",
        relevance_score=0.80,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_db(rows: List[Any]) -> AsyncMock:
    """Return an AsyncSession mock whose execute() yields the given rows."""
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    return db


# ──────────────────────────────────────────────────────────────────────────────
# Helper unit tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "query, expected",
    [
        ("ধারা ৩০২ কী?", "৩০২"),
        ("what does section 379 say", "379"),
        ("article 27 of the constitution", "27"),
        ("clause 5 of the agreement", "5"),
        ("no number here", None),
        ("sec. 100A of the act", "100A"),
    ],
)
def test_extract_section_number(query: str, expected: str | None) -> None:
    assert _extract_section_number(query) == expected


def test_fmt_embedding_format() -> None:
    emb = [0.1, -0.5, 1.0]
    result = _fmt_embedding(emb)
    assert result.startswith("[")
    assert result.endswith("]")
    assert result.count(",") == 2


def test_dedup_sections_keeps_highest_score() -> None:
    a = SourceItem(source_type="section", section_db_id="id1", relevance_score=0.7)
    b = SourceItem(source_type="section", section_db_id="id1", relevance_score=0.9)
    c = SourceItem(source_type="section", section_db_id="id2", relevance_score=0.8)
    result = _dedup_sections([a, b, c])
    assert len(result) == 2
    assert result[0].relevance_score == 0.9   # sorted desc
    assert result[1].relevance_score == 0.8


def test_dedup_sections_fallback_key() -> None:
    """Items without section_db_id fall back to act_id:section_number."""
    a = SourceItem(source_type="section", act_id="A1", section_number="5", relevance_score=0.6)
    b = SourceItem(source_type="section", act_id="A1", section_number="5", relevance_score=0.8)
    result = _dedup_sections([a, b])
    assert len(result) == 1
    assert result[0].relevance_score == 0.8


# ──────────────────────────────────────────────────────────────────────────────
# Route dispatch tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def router() -> QueryRouter:
    return QueryRouter()


@pytest.mark.asyncio
async def test_general_info_returns_empty_no_db(router: QueryRouter) -> None:
    db = AsyncMock()
    result = await router.route(_intent(Intent.GENERAL_INFO), "আইনজীবী কোথায়?", None, db)
    assert result.strategy == "GENERAL_INFO"
    assert result.sources == []
    assert result.needs_llm is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_returns_empty_no_db(router: QueryRouter) -> None:
    db = AsyncMock()
    result = await router.route(_intent(Intent.UNKNOWN), "hello", None, db)
    assert result.strategy == "UNKNOWN"
    assert result.sources == []
    db.execute.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# FIND_SECTION
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_section_exact_match(router: QueryRouter) -> None:
    row = _make_section_row(section_number="379")
    db  = _mock_db([row])

    result = await router.route(
        _intent(Intent.FIND_SECTION),
        "section 379 of penal code",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "exact_section"
    assert len(result.sources) == 1
    src = result.sources[0]
    assert src.source_type == "section"
    assert src.section_number == "379"
    assert src.act_title_en == "Penal Code 1860"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_section_no_number_falls_back_to_vector(router: QueryRouter) -> None:
    row = _make_section_row()
    db  = _mock_db([row])

    result = await router.route(
        _intent(Intent.FIND_SECTION),
        "section about theft",        # no numeric section number
        DUMMY_EMBEDDING,
        db,
    )

    # Falls back to vector search
    assert "vector" in result.strategy
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_section_exact_miss_tries_fuzzy(router: QueryRouter) -> None:
    # First call (exact) returns nothing; second (fuzzy) returns a row
    exact_result = MagicMock()
    exact_result.fetchall.return_value = []
    fuzzy_result = MagicMock()
    fuzzy_result.fetchall.return_value = [_make_section_row()]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[exact_result, fuzzy_result])

    result = await router.route(
        _intent(Intent.FIND_SECTION),
        "section 379 penal code",
        None,
        db,
    )

    assert result.strategy == "exact_section"
    assert len(result.sources) == 1
    assert db.execute.await_count == 2  # exact + fuzzy


# ──────────────────────────────────────────────────────────────────────────────
# FIND_LAW / EXPLAIN_RIGHTS — vector filtered
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("intent_val", [Intent.FIND_LAW, Intent.EXPLAIN_RIGHTS])
async def test_vector_filtered_strategies(
    router: QueryRouter, intent_val: Intent
) -> None:
    rows = [_make_section_row(relevance_score=0.85), _make_section_row(section_db_id="id2", relevance_score=0.75)]
    db   = _mock_db(rows)

    result = await router.route(
        _intent(intent_val, category=Category.CRIMINAL),
        "punishment for theft",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "vector_filtered"
    assert len(result.sources) == 2
    assert all(s.source_type == "section" for s in result.sources)
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_no_embedding_returns_empty(router: QueryRouter) -> None:
    db = AsyncMock()
    result = await router.route(
        _intent(Intent.FIND_LAW),
        "what is the punishment for theft?",
        None,
        db,
    )
    assert result.sources == []
    assert "no_embedding" in result.strategy
    db.execute.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# FIND_CASE
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_case_returns_case_sources(router: QueryRouter) -> None:
    db = _mock_db([_make_case_row()])

    result = await router.route(
        _intent(Intent.FIND_CASE),
        "any precedent on theft?",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "case_vector"
    assert len(result.sources) == 1
    src = result.sources[0]
    assert src.source_type == "case"
    assert src.citation == "2020 DLR 100"


@pytest.mark.asyncio
async def test_find_case_no_embedding(router: QueryRouter) -> None:
    db = AsyncMock()
    result = await router.route(_intent(Intent.FIND_CASE), "any case?", None, db)
    assert result.sources == []
    db.execute.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# CHECK_PROCESS — hybrid
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_search_merges_fts_and_vector(router: QueryRouter) -> None:
    fts_row    = _make_section_row(section_db_id="id-fts",    relevance_score=0.70)
    vector_row = _make_section_row(section_db_id="id-vector", relevance_score=0.88)
    overlap    = _make_section_row(section_db_id="id-both",   relevance_score=0.65)
    overlap2   = _make_section_row(section_db_id="id-both",   relevance_score=0.80)

    fts_result = MagicMock(); fts_result.fetchall.return_value = [fts_row, overlap]
    vec_result = MagicMock(); vec_result.fetchall.return_value = [vector_row, overlap2]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[fts_result, vec_result])

    result = await router.route(
        _intent(Intent.CHECK_PROCESS),
        "how to file a case in Bangladesh?",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "hybrid_fts_vector"
    # id-fts, id-vector, id-both (deduped) = 3 unique
    ids = {s.section_db_id for s in result.sources}
    assert "id-both" in ids
    # overlap should keep the higher score (0.80)
    both = next(s for s in result.sources if s.section_db_id == "id-both")
    assert both.relevance_score == 0.80


@pytest.mark.asyncio
async def test_hybrid_fts_failure_falls_back_to_vector_only(router: QueryRouter) -> None:
    """If FTS raises (e.g. pure Bengali query), hybrid still returns vector results."""
    vector_row = _make_section_row()
    vec_result = MagicMock(); vec_result.fetchall.return_value = [vector_row]

    db = AsyncMock()
    # First call (FTS) raises; second (vector) succeeds
    db.execute = AsyncMock(side_effect=[Exception("tsquery parse error"), vec_result])

    result = await router.route(
        _intent(Intent.CHECK_PROCESS),
        "কীভাবে মামলা করব?",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "hybrid_fts_vector"
    assert len(result.sources) == 1


# ──────────────────────────────────────────────────────────────────────────────
# COMPARE_LAWS — multi-vector
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_laws_merges_filtered_and_unfiltered(router: QueryRouter) -> None:
    filtered_row   = _make_section_row(section_db_id="id-filtered",   relevance_score=0.80)
    unfiltered_row = _make_section_row(section_db_id="id-unfiltered", relevance_score=0.75)

    filtered_result   = MagicMock(); filtered_result.fetchall.return_value = [filtered_row]
    unfiltered_result = MagicMock(); unfiltered_result.fetchall.return_value = [unfiltered_row]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[filtered_result, unfiltered_result])

    result = await router.route(
        _intent(Intent.COMPARE_LAWS, category=Category.CRIMINAL),
        "difference between civil and criminal cases",
        DUMMY_EMBEDDING,
        db,
    )

    assert result.strategy == "compare_multi_vector"
    assert len(result.sources) == 2
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_compare_deduplicates_overlap(router: QueryRouter) -> None:
    shared = _make_section_row(section_db_id="shared", relevance_score=0.70)
    higher = _make_section_row(section_db_id="shared", relevance_score=0.90)

    r1 = MagicMock(); r1.fetchall.return_value = [shared]
    r2 = MagicMock(); r2.fetchall.return_value = [higher]

    db = AsyncMock(); db.execute = AsyncMock(side_effect=[r1, r2])

    result = await router.route(
        _intent(Intent.COMPARE_LAWS), "compare laws", DUMMY_EMBEDDING, db
    )
    assert len(result.sources) == 1
    assert result.sources[0].relevance_score == 0.90


# ──────────────────────────────────────────────────────────────────────────────
# GET_DOCUMENT — full-text
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_document_uses_fulltext(router: QueryRouter) -> None:
    row = _make_section_row(relevance_score=0.60)
    db  = _mock_db([row])

    result = await router.route(
        _intent(Intent.GET_DOCUMENT),
        "divorce application form Bangladesh",
        None,           # embedding not needed for FTS
        db,
    )

    assert result.strategy == "fulltext"
    assert len(result.sources) == 1
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_document_fts_error_returns_empty(router: QueryRouter) -> None:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("FTS error"))

    result = await router.route(
        _intent(Intent.GET_DOCUMENT), "certificate form", None, db
    )
    assert result.strategy == "fulltext"
    assert result.sources == []


# ──────────────────────────────────────────────────────────────────────────────
# QueryResult structure
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_always_has_needs_llm_true(router: QueryRouter) -> None:
    for intent_val in Intent:
        db = _mock_db([_make_section_row()])
        result = await router.route(
            _intent(intent_val), "test query", DUMMY_EMBEDDING, db
        )
        assert result.needs_llm is True, f"Failed for {intent_val}"


def test_source_item_to_dict_excludes_internal_key() -> None:
    s = SourceItem(source_type="section", section_db_id="internal", act_title_en="Test")
    d = s.to_dict()
    assert "section_db_id" not in d
    assert "act_title_en" in d
