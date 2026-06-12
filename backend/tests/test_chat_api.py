"""
Unit tests for RAGPipeline and its helpers.

All external I/O (IntentDetector, EmbeddingService, QueryRouter, Anthropic)
is mocked.  No network or DB calls are made.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding_service import EmbeddingService
from app.services.intent_detector import Category, Intent, IntentDetector, IntentResult
from app.services.query_router import QueryResult, QueryRouter, SourceItem
from app.services.rag_pipeline import (
    RAGPipeline,
    _build_context,
    _build_messages,
    _format_case_source,
    _format_section_source,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

DUMMY_EMBEDDING = [0.1] * 1536


def _make_intent(
    intent: Intent = Intent.FIND_LAW,
    category: Category = Category.CRIMINAL,
    language: str = "en",
    confidence: float = 0.9,
    stage: int = 1,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        category=category,
        confidence=confidence,
        language=language,
        key_concepts=["theft"],
        stage=stage,
    )


def _make_section_source(**kw: Any) -> SourceItem:
    defaults = dict(
        source_type="section",
        act_title_en="Penal Code 1860",
        act_id="A001",
        category="criminal",
        year=1860,
        section_number="379",
        section_title="Theft",
        content_en="Whoever commits theft shall be punished...",
        content_bn=None,
        relevance_score=0.85,
        section_db_id="uuid-1",
    )
    defaults.update(kw)
    return SourceItem(**defaults)


def _make_case_source(**kw: Any) -> SourceItem:
    defaults = dict(
        source_type="case",
        citation="2021 DLR 55",
        court="High Court Division",
        year=2021,
        parties="State v Karim",
        summary="The court upheld the conviction for theft.",
        relevance_score=0.78,
    )
    defaults.update(kw)
    return SourceItem(**defaults)


async def _collect_stream(gen: AsyncIterator[Dict]) -> List[Dict]:
    return [event async for event in gen]


def _make_stream_text(tokens: List[str]) -> AsyncIterator[str]:
    """Async generator that yields text tokens one by one."""
    async def _gen() -> AsyncIterator[str]:
        for t in tokens:
            yield t
    return _gen()


def _make_pipeline(
    intent: IntentResult,
    sources: List[SourceItem],
    llm_tokens: List[str],
    embed_raises: bool = False,
    router_raises: bool = False,
) -> RAGPipeline:
    intent_detector = AsyncMock(spec=IntentDetector)
    intent_detector.detect = AsyncMock(return_value=intent)

    embedding_service = AsyncMock(spec=EmbeddingService)
    if embed_raises:
        embedding_service.embed = AsyncMock(side_effect=Exception("OpenAI down"))
    else:
        embedding_service.embed = AsyncMock(return_value=DUMMY_EMBEDDING)

    query_router = AsyncMock(spec=QueryRouter)
    if router_raises:
        query_router.route = AsyncMock(side_effect=Exception("DB error"))
    else:
        query_router.route = AsyncMock(
            return_value=QueryResult(sources=sources, strategy="vector_filtered")
        )

    # Mock the Anthropic streaming context manager
    stream_mock = AsyncMock()
    stream_mock.__aenter__ = AsyncMock(return_value=stream_mock)
    stream_mock.__aexit__  = AsyncMock(return_value=False)
    stream_mock.text_stream = _make_stream_text(llm_tokens)

    llm = MagicMock()
    llm.messages.stream = MagicMock(return_value=stream_mock)

    return RAGPipeline(
        intent_detector   = intent_detector,
        embedding_service = embedding_service,
        query_router      = query_router,
        llm               = llm,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Context / message builder tests
# ──────────────────────────────────────────────────────────────────────────────

def test_format_section_source_contains_key_fields() -> None:
    s   = _make_section_source()
    out = _format_section_source(1, s)
    assert "Penal Code 1860" in out
    assert "379" in out
    assert "Theft" in out
    assert "Whoever commits theft" in out
    assert "0.85" in out


def test_format_section_source_skips_none_fields() -> None:
    s   = _make_section_source(section_title=None, content_bn=None)
    out = _format_section_source(1, s)
    assert "Title:" not in out
    assert "Bengali" not in out


def test_format_case_source_contains_key_fields() -> None:
    s   = _make_case_source()
    out = _format_case_source(1, s)
    assert "2021 DLR 55" in out
    assert "High Court Division" in out
    assert "State v Karim" in out
    assert "upheld the conviction" in out


def test_build_context_empty_sources() -> None:
    result = QueryResult(sources=[], strategy="none")
    assert _build_context(result) == ""


def test_build_context_orders_and_numbers_sources() -> None:
    sources = [_make_section_source(), _make_case_source()]
    result  = QueryResult(sources=sources, strategy="hybrid")
    ctx     = _build_context(result)
    assert "Legal Source 1" in ctx
    assert "Case Law 2" in ctx


def test_build_context_truncates_at_budget() -> None:
    # Create a source with very long content to trigger truncation
    huge = _make_section_source(content_en="X" * 15_000)
    result = QueryResult(sources=[huge, _make_section_source()], strategy="test")
    ctx = _build_context(result)
    # Second source should be omitted
    assert ctx.count("Legal Source") == 1


def test_build_messages_with_context() -> None:
    msgs = _build_messages("what is theft?", "some context", history=None)
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "LEGAL CONTEXT FROM DATABASE:" in msgs[0]["content"]
    assert "what is theft?" in msgs[0]["content"]


def test_build_messages_no_context_inserts_note() -> None:
    msgs = _build_messages("who are you?", "", history=None)
    assert "No matching legal text" in msgs[0]["content"]


def test_build_messages_prepends_history() -> None:
    history = [
        {"role": "user",      "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
    ]
    msgs = _build_messages("new question", "ctx", history=history)
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["content"].endswith("new question")


# ──────────────────────────────────────────────────────────────────────────────
# RAGPipeline.stream() — happy path
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_yields_all_event_types() -> None:
    pipeline = _make_pipeline(
        intent    = _make_intent(),
        sources   = [_make_section_source()],
        llm_tokens= ["চুরির", " শাস্তি", " তিন বছর"],
    )
    db     = AsyncMock()
    events = await _collect_stream(pipeline.stream("চুরির শাস্তি কী?", db))

    types = [e["type"] for e in events]
    assert types[0]  == "intent"
    assert types[1]  == "sources"
    assert "token" in types
    assert types[-1] == "done"


@pytest.mark.asyncio
async def test_stream_intent_event_fields() -> None:
    pipeline = _make_pipeline(_make_intent(stage=2), [], ["ok"])
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))
    intent_e = next(e for e in events if e["type"] == "intent")
    assert intent_e["data"]["intent"]   == "FIND_LAW"
    assert intent_e["data"]["category"] == "criminal"
    assert intent_e["data"]["stage"]    == 2
    assert 0.0 <= intent_e["data"]["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_stream_sources_event_contains_sources() -> None:
    pipeline = _make_pipeline(_make_intent(), [_make_section_source()], ["ok"])
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))
    src_e    = next(e for e in events if e["type"] == "sources")
    assert len(src_e["data"]) == 1
    assert src_e["data"][0]["source_type"] == "section"
    # Internal dedup key must not leak to the outside
    assert "section_db_id" not in src_e["data"][0]


@pytest.mark.asyncio
async def test_stream_tokens_match_llm_output() -> None:
    tokens   = ["The ", "law ", "says..."]
    pipeline = _make_pipeline(_make_intent(), [], tokens)
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))
    token_events = [e["data"] for e in events if e["type"] == "token"]
    assert token_events == tokens


@pytest.mark.asyncio
async def test_stream_done_event_fields() -> None:
    pipeline = _make_pipeline(_make_intent(), [_make_section_source()], ["hello"])
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))
    done_e   = next(e for e in events if e["type"] == "done")
    data     = done_e["data"]
    assert "message_id" in data
    assert isinstance(data["response_time_ms"], int)
    assert data["sources_count"] == 1
    assert data["strategy"] == "vector_filtered"
    assert data["full_response"] == "hello"


# ──────────────────────────────────────────────────────────────────────────────
# GENERAL_INFO / UNKNOWN — embedding skipped
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_general_info_skips_embedding() -> None:
    pipeline = _make_pipeline(
        intent    = _make_intent(intent=Intent.GENERAL_INFO),
        sources   = [],
        llm_tokens= ["Contact a lawyer."],
    )
    events = await _collect_stream(pipeline.stream("আইনজীবী কোথায়?", AsyncMock()))
    assert any(e["type"] == "done" for e in events)
    pipeline._embedding_service.embed.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_unknown_intent_skips_embedding() -> None:
    pipeline = _make_pipeline(
        intent    = _make_intent(intent=Intent.UNKNOWN),
        sources   = [],
        llm_tokens= ["I'm not sure."],
    )
    await _collect_stream(pipeline.stream("???", AsyncMock()))
    pipeline._embedding_service.embed.assert_not_awaited()  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────────────
# Fault tolerance
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_embedding_failure_is_non_fatal() -> None:
    """Pipeline continues even if OpenAI embedding call fails."""
    pipeline = _make_pipeline(
        intent      = _make_intent(),
        sources     = [],
        llm_tokens  = ["ok"],
        embed_raises= True,
    )
    events = await _collect_stream(pipeline.stream("theft punishment?", AsyncMock()))
    types  = [e["type"] for e in events]
    # Should still complete — no error event for embedding failure
    assert "done" in types
    assert "error" not in types


@pytest.mark.asyncio
async def test_router_failure_yields_empty_sources_then_llm() -> None:
    """If the router raises, the pipeline emits empty sources and still calls the LLM."""
    pipeline = _make_pipeline(
        intent        = _make_intent(),
        sources       = [],
        llm_tokens    = ["answer"],
        router_raises = True,
    )
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))
    src_e    = next(e for e in events if e["type"] == "sources")
    assert src_e["data"] == []
    assert any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_llm_api_error_yields_error_event() -> None:
    import anthropic as anthropic_lib

    intent_detector   = AsyncMock(spec=IntentDetector)
    intent_detector.detect = AsyncMock(return_value=_make_intent())
    embedding_service = AsyncMock(spec=EmbeddingService)
    embedding_service.embed = AsyncMock(return_value=DUMMY_EMBEDDING)
    query_router      = AsyncMock(spec=QueryRouter)
    query_router.route = AsyncMock(
        return_value=QueryResult(sources=[], strategy="vector_filtered")
    )

    # LLM stream raises an API status error
    stream_mock = AsyncMock()
    stream_mock.__aenter__ = AsyncMock(
        side_effect=anthropic_lib.APIStatusError(
            "rate limited",
            response=MagicMock(status_code=429),
            body={},
        )
    )
    stream_mock.__aexit__ = AsyncMock(return_value=False)

    llm = MagicMock()
    llm.messages.stream = MagicMock(return_value=stream_mock)

    pipeline = RAGPipeline(intent_detector, embedding_service, query_router, llm)
    events   = await _collect_stream(pipeline.stream("test", AsyncMock()))

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "429" in error_events[0]["data"]["message"]
    # Should NOT have a done event after an error
    assert not any(e["type"] == "done" for e in events)


@pytest.mark.asyncio
async def test_intent_detection_failure_yields_error_and_stops() -> None:
    intent_detector = AsyncMock(spec=IntentDetector)
    intent_detector.detect = AsyncMock(side_effect=Exception("classifier crashed"))

    pipeline = RAGPipeline(
        intent_detector   = intent_detector,
        embedding_service = AsyncMock(spec=EmbeddingService),
        query_router      = AsyncMock(spec=QueryRouter),
        llm               = MagicMock(),
    )
    events = await _collect_stream(pipeline.stream("test", AsyncMock()))
    assert len(events) == 1
    assert events[0]["type"] == "error"


# ──────────────────────────────────────────────────────────────────────────────
# EmbeddingService unit tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_embedding_service_embed_returns_vector() -> None:
    mock_resp = MagicMock()
    mock_resp.data = [MagicMock(embedding=DUMMY_EMBEDDING, index=0)]

    client = AsyncMock()
    client.embeddings.create = AsyncMock(return_value=mock_resp)

    svc = EmbeddingService(client=client)
    result = await svc.embed("چوری کی سزا")
    assert len(result) == 1536
    client.embeddings.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_embedding_service_rejects_empty_text() -> None:
    svc = EmbeddingService(client=AsyncMock())
    with pytest.raises(ValueError, match="empty"):
        await svc.embed("   ")


@pytest.mark.asyncio
async def test_embedding_service_batch_preserves_order() -> None:
    texts = ["first", "second", "third"]
    # Return items out of order from the API (API may reorder)
    mock_resp = MagicMock()
    mock_resp.data = [
        MagicMock(embedding=[3.0] * 1536, index=2),
        MagicMock(embedding=[1.0] * 1536, index=0),
        MagicMock(embedding=[2.0] * 1536, index=1),
    ]
    client = AsyncMock()
    client.embeddings.create = AsyncMock(return_value=mock_resp)

    svc    = EmbeddingService(client=client)
    result = await svc.embed_batch(texts)
    assert len(result) == 3
    assert result[0][0] == pytest.approx(1.0)  # index 0
    assert result[1][0] == pytest.approx(2.0)  # index 1
    assert result[2][0] == pytest.approx(3.0)  # index 2


@pytest.mark.asyncio
async def test_embedding_service_batch_chunks_large_input() -> None:
    """Batches > 100 items must be split into multiple API calls."""
    texts = [f"text {i}" for i in range(250)]

    mock_resp = MagicMock()
    mock_resp.data = [MagicMock(embedding=[0.0] * 1536, index=i) for i in range(100)]

    client = AsyncMock()
    client.embeddings.create = AsyncMock(return_value=mock_resp)

    svc = EmbeddingService(client=client)
    await svc.embed_batch(texts)

    # 250 texts → 3 calls (100 + 100 + 50)
    assert client.embeddings.create.await_count == 3
