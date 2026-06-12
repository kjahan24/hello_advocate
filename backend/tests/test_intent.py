"""
Unit tests for the two-stage intent detector.

Stage 1 tests run without any network call.
Stage 2 tests mock the Anthropic client.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intent_detector import (
    Category,
    Intent,
    IntentDetector,
    _detect_language,
    _match_category,
    _match_intent,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def detector() -> IntentDetector:
    with patch("app.services.intent_detector.get_settings") as mock_cfg:
        mock_cfg.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")
        with patch("anthropic.AsyncAnthropic"):
            return IntentDetector()


def _make_llm_response(intent: str, category: str, confidence: float = 0.85) -> MagicMock:
    payload = json.dumps(
        {
            "intent": intent,
            "category": category,
            "confidence": confidence,
            "language": "en",
            "key_concepts": ["test"],
        }
    )
    msg = MagicMock()
    msg.content = [MagicMock(text=payload)]
    return msg


# ──────────────────────────────────────────────────────────────────────────────
# Language detection
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text, expected",
    [
        ("চুরির শাস্তি কী?", "bn"),
        ("punishment for theft", "en"),
        ("ধারা 302 কী?", "mixed"),
        ("", "en"),
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    assert _detect_language(text) == expected


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — intent keyword matching
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "query, expected_intent",
    [
        # FIND_SECTION
        ("ধারা ৩০২ কী?", Intent.FIND_SECTION),
        ("What does section 302 say?", Intent.FIND_SECTION),
        ("article 27 of the constitution", Intent.FIND_SECTION),
        # FIND_LAW
        ("চুরির শাস্তি কী?", Intent.FIND_LAW),
        ("punishment for theft in Bangladesh", Intent.FIND_LAW),
        ("what law covers domestic violence?", Intent.FIND_LAW),
        # FIND_CASE
        ("জমি নিয়ে কোনো নজির আছে?", Intent.FIND_CASE),
        ("any case law on property disputes?", Intent.FIND_CASE),
        ("relevant judgment on divorce Bangladesh", Intent.FIND_CASE),
        # EXPLAIN_RIGHTS
        ("আমার কী কী অধিকার আছে?", Intent.EXPLAIN_RIGHTS),
        ("what are my rights as an employee?", Intent.EXPLAIN_RIGHTS),
        ("fundamental rights under constitution", Intent.EXPLAIN_RIGHTS),
        # CHECK_PROCESS
        ("মামলা করতে হলে কী করতে হবে?", Intent.CHECK_PROCESS),
        ("how to file a case in Bangladesh?", Intent.CHECK_PROCESS),
        ("procedure for registering a company", Intent.CHECK_PROCESS),
        # COMPARE_LAWS
        ("দেওয়ানি ও ফৌজদারি পার্থক্য কী?", Intent.COMPARE_LAWS),
        ("difference between civil and criminal cases", Intent.COMPARE_LAWS),
        # GET_DOCUMENT
        ("তালাকের জন্য কোন ফর্ম লাগে?", Intent.GET_DOCUMENT),
        ("what documents are needed for marriage registration?", Intent.GET_DOCUMENT),
        # GENERAL_INFO
        ("আইনজীবী কোথায় পাব?", Intent.GENERAL_INFO),
        ("where can I find legal aid in Dhaka?", Intent.GENERAL_INFO),
    ],
)
def test_stage1_intent(query: str, expected_intent: Intent) -> None:
    intent, confidence = _match_intent(query)
    assert intent == expected_intent, f"Query: {query!r}"
    assert confidence > 0


@pytest.mark.parametrize(
    "query, expected_category",
    [
        ("চুরির শাস্তি কী?", Category.CRIMINAL),
        ("divorce procedure Bangladesh", Category.FAMILY),
        ("জমি রেজিস্ট্রেশন কীভাবে করব?", Category.LAND_PROPERTY),
        ("শ্রমিকের বেতন না দিলে কী হবে?", Category.LABOR_EMPLOYMENT),
        ("cyber crime law Bangladesh", Category.DIGITAL_CYBER),
        ("bank loan default Bangladesh", Category.BANKING_FINANCE),
        ("tenant eviction notice", Category.TENANCY_RENT),
        ("visa application Bangladesh", Category.IMMIGRATION),
        ("consumer complaint product defect", Category.CONSUMER_RIGHTS),
        ("writ petition high court", Category.CONSTITUTIONAL),
    ],
)
def test_stage1_category(query: str, expected_category: Category) -> None:
    category = _match_category(query)
    assert category == expected_category, f"Query: {query!r}"


def test_unknown_query_returns_low_confidence() -> None:
    intent, confidence = _match_intent("hello how are you")
    assert intent == Intent.UNKNOWN
    assert confidence == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# IntentDetector.detect() — Stage 1 path (high confidence, no LLM call)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_stage1_no_llm_call(detector: IntentDetector) -> None:
    result = await detector.detect("ধারা ৩০২ কী?")
    assert result.intent == Intent.FIND_SECTION
    assert result.stage == 1
    assert result.confidence >= detector.CONFIDENCE_THRESHOLD
    detector._client.messages.create.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_detect_empty_query(detector: IntentDetector) -> None:
    result = await detector.detect("   ")
    assert result.intent == Intent.UNKNOWN
    assert result.stage == 1


# ──────────────────────────────────────────────────────────────────────────────
# IntentDetector.detect() — Stage 2 path (low confidence → LLM)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_escalates_to_llm(detector: IntentDetector) -> None:
    llm_resp = _make_llm_response("FIND_LAW", "criminal", confidence=0.85)
    detector._client.messages.create = AsyncMock(return_value=llm_resp)  # type: ignore[attr-defined]

    # Ambiguous query that won't hit any keyword rule
    result = await detector.detect("আইন সম্পর্কে জানতে চাই")
    assert result.stage == 2
    detector._client.messages.create.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_detect_llm_api_error_returns_unknown(detector: IntentDetector) -> None:
    import anthropic as anthropic_lib

    detector._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
        side_effect=anthropic_lib.APIStatusError(
            "rate limit",
            response=MagicMock(status_code=429),
            body={},
        )
    )
    result = await detector.detect("আইন সম্পর্কে জানতে চাই")
    assert result.intent == Intent.UNKNOWN
    assert result.stage == 2


@pytest.mark.asyncio
async def test_detect_llm_bad_json_returns_unknown(detector: IntentDetector) -> None:
    bad = MagicMock()
    bad.content = [MagicMock(text="not json at all")]
    detector._client.messages.create = AsyncMock(return_value=bad)  # type: ignore[attr-defined]

    result = await detector.detect("আইন সম্পর্কে জানতে চাই")
    assert result.intent == Intent.UNKNOWN


# ──────────────────────────────────────────────────────────────────────────────
# IntentResult fields
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_has_all_fields(detector: IntentDetector) -> None:
    result = await detector.detect("section 302 penal code Bangladesh")
    assert isinstance(result.intent, Intent)
    assert isinstance(result.category, Category)
    assert 0.0 <= result.confidence <= 1.0
    assert result.language in ("bn", "en", "mixed")
    assert isinstance(result.key_concepts, list)
    assert result.stage in (1, 2)
