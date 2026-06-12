"""
RAGPipeline — central orchestrator for the AI Lawyer chat feature.

Flow per query:
  1. IntentDetector  → classify intent + category + language
  2. EmbeddingService → compute 1536-dim query vector (skipped for GENERAL_INFO)
  3. QueryExpander   → expand Bengali legal terms with synonyms
  4. QueryRouter     → retrieve ranked SourceItems via RRF hybrid search
  5. Context builder  → format sources into a prompt-ready string (per-section budget)
  6. Claude streaming → stream tokens back to the caller via async generator
  7. Citations event → yield curated source citations after response

Yields SSE-compatible dicts (CLAUDE.md §8):
  {"type": "intent",    "data": {...}}
  {"type": "sources",   "data": [...]}
  {"type": "token",     "data": "<text chunk>"}
  {"type": "citations", "data": [...]}  ← new: after response
  {"type": "error",     "data": {"message": "..."}}
  {"type": "done",      "data": {"message_id": "...", "response_time_ms": N, ...}}

Design note — why pipeline.stream() does NOT accept a db session
----------------------------------------------------------------
stream() is an async generator that yields tokens during LLM streaming.
Keeping an AsyncSession alive across generator yield points breaks
SQLAlchemy's greenlet bridge ("greenlet_spawn has not been called").
Instead, step 4 (DB retrieval) opens its own SHORT-LIVED session that
is fully closed before any token yield — so no session ever spans a yield.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic
import structlog

from app.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.intent_detector import Intent, IntentDetector, IntentResult
from app.services.query_expander import expand_query, fts_core_terms
from app.services.query_router import QueryResult, QueryRouter, SourceItem

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# System prompt templates — context injected at runtime via .format(context=...)
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE_BN = """\
আপনি বাংলাদেশের একজন অভিজ্ঞ আইনজীবী এবং আইনি পরামর্শদাতা।
আপনার কাছে বাংলাদেশের ১,৬০০+ আইনের তথ্য আছে।

নিচের আইনি ধারাগুলো ব্যবহার করে প্রশ্নের উত্তর দিন:

{context}

উত্তর দেওয়ার নিয়ম:
১. প্রাসঙ্গিক আইন ও ধারা উল্লেখ করুন (যেমন: দণ্ডবিধি ধারা ৩৭৯)
২. সহজ বাংলায় ব্যাখ্যা করুন
৩. ব্যবহারিক পরামর্শ দিন
৪. যদি একাধিক আইন প্রযোজ্য হয়, সবগুলো উল্লেখ করুন
৫. অনিশ্চিত হলে স্পষ্ট বলুন এবং আইনজীবীর পরামর্শ নিতে বলুন
৬. উত্তর সংক্ষিপ্ত কিন্তু সম্পূর্ণ রাখুন

গুরুত্বপূর্ণ: শুধুমাত্র প্রদত্ত আইনি ধারার উপর ভিত্তি করে উত্তর দিন।
⚠️ সর্বদা শেষে এই disclaimer যোগ করুন:
"⚠️ এটি AI-সহায়তা, আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে একজন যোগ্য আইনজীবীর সাথে পরামর্শ করুন।"\
"""

_SYSTEM_PROMPT_TEMPLATE_EN = """\
You are an experienced lawyer and legal advisor specializing in Bangladesh law.
You have access to information from 1,600+ Bangladesh laws.

Use the legal sections below to answer the question:

{context}

Rules for answering:
1. Cite the relevant Act and Section (e.g., Penal Code Section 379)
2. Explain in plain, accessible language
3. Give practical next steps
4. If multiple laws apply, mention all of them
5. If uncertain, say so clearly and recommend consulting a qualified lawyer
6. Keep answers concise but complete

Important: Base your answer ONLY on the provided legal sections.
⚠️ Always end with: "⚠️ This is AI assistance, not legal advice. \
For serious matters, consult a qualified lawyer."\
"""

# ──────────────────────────────────────────────────────────────────────────────
# Document analysis system prompts (static — context goes in user message)
# ──────────────────────────────────────────────────────────────────────────────

_DOCUMENT_SYSTEM_PROMPT = """\
You are AI Lawyer, an expert AI assistant specializing in Bangladesh law.
The user has submitted a legal document (image or PDF) for analysis.

STRICT RULES:
1. Read the attached document carefully and use BOTH its content AND the
   provided legal context from the database to answer.
2. Always cite the exact Act name and Section number: [Act Name, Section X]
3. Respond in the SAME language the user used (Bengali or English).
4. Structure every response as:
   a) Document summary — what type of document and what it says
   b) Key legal issues identified in the document
   c) Relevant law: [Act Name, Section X]
   d) Plain language explanation
   e) Practical next steps
   f) Disclaimer (mandatory, always last)
5. NEVER fabricate laws, sections, or case citations.
6. If no relevant law is found in the provided context, say exactly:
   "এই বিষয়ে আমার ডেটাবেজে সুনির্দিষ্ট তথ্য নেই। একজন আইনজীবীর সাথে যোগাযোগ করুন।"
7. ALWAYS end with the disclaimer:
   Bengali: "⚠️ এটি AI-সহায়তা, আইনি পরামর্শ নয়। গুরুত্বপূর্ণ বিষয়ে একজন যোগ্য আইনজীবীর সাথে পরামর্শ করুন।"
   English: "⚠️ This is AI assistance, not legal advice. For serious matters, consult a qualified lawyer."\
"""

_EXTRACTION_SYSTEM = "You are a Bangladesh legal document analyst. Respond in English only."

_EXTRACTION_PROMPT = """\
Analyze this document and describe it in 3-5 sentences covering:
1. Document type (e.g. land deed, court notice, FIR, contract, nikah-nama)
2. The core legal issue or subject matter
3. Key parties, dates, or section/act numbers visible in the document
4. What legal question the holder of this document most likely needs answered

Be specific about any legal concepts, Bangladesh act names, or section numbers you can see.\
"""

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_LLM_MODEL        = "claude-sonnet-4-5"
_MAX_TOKENS       = 2048
_SECTION_MAX_CHARS   = 12_000   # ~3 000 tokens per section — truncate with paragraph extraction
_TOTAL_MAX_CHARS     = 48_000   # ~12 000 tokens total context budget

# Intents that skip the embedding call (no vector search needed)
_NO_EMBED_INTENTS = frozenset({Intent.GENERAL_INFO, Intent.UNKNOWN})

# Fallback context string when no DB results found
_NO_CONTEXT_BN = "প্রাসঙ্গিক কোনো আইনি ধারা ডেটাবেজে পাওয়া যায়নি।"
_NO_CONTEXT_EN = "No relevant legal sections were found in the database."

# ──────────────────────────────────────────────────────────────────────────────
# Context / message builders
# ──────────────────────────────────────────────────────────────────────────────

def _extract_relevant_paragraph(content: str, query_lower: str, max_chars: int) -> str:
    """Return the paragraph of `content` with the most query keyword matches."""
    if len(content) <= max_chars:
        return content
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return content[:max_chars]
    query_words = {w for w in query_lower.split() if len(w) > 2}

    def _score(p: str) -> int:
        pl = p.lower()
        return sum(1 for w in query_words if w in pl)

    best = max(paragraphs, key=_score)
    return best[:max_chars] if len(best) > max_chars else best


def _format_section_source(i: int, s: SourceItem, query: str = "") -> str:
    sec_label = s.section_number or "N/A"
    if s.section_title:
        sec_label += f" - {s.section_title}"

    content = s.content_en or s.content_bn or ""
    if len(content) > _SECTION_MAX_CHARS:
        content = _extract_relevant_paragraph(content, query.lower(), _SECTION_MAX_CHARS)

    lines = [
        f"আইনের নাম: {s.act_title_en} ({s.year or 'year unknown'})",
        f"ধারা: {sec_label}",
        "",
        content,
        f"[প্রাসঙ্গিকতা: {s.relevance_score:.2f}]",
    ]
    return "\n".join(lines)


def _format_case_source(i: int, s: SourceItem) -> str:
    lines = [
        f"--- Case Law {i} ---",
        f"Citation : {s.citation or 'N/A'}",
        f"Court    : {s.court or 'N/A'}",
        f"Year     : {s.year or 'N/A'}",
        f"Parties  : {s.parties or 'N/A'}",
    ]
    if s.summary:
        lines.append(f"Summary  :\n{s.summary}")
    lines.append(f"Relevance: {s.relevance_score:.2f}")
    return "\n".join(lines)


def _build_context(query_result: QueryResult, query: str = "") -> str:
    """
    Format retrieved sources into a context string for injection into the system prompt.

    Per-section limit: _SECTION_MAX_CHARS (paragraph extraction for oversized sections).
    Total budget:      _TOTAL_MAX_CHARS (drop least-relevant sources if exceeded).
    """
    if not query_result.sources:
        return ""

    parts: List[str] = []
    total_chars = 0

    for i, source in enumerate(query_result.sources, 1):
        block = (
            _format_case_source(i, source)
            if source.source_type == "case"
            else _format_section_source(i, source, query)
        )

        if total_chars + len(block) > _TOTAL_MAX_CHARS:
            break

        parts.append(block)
        total_chars += len(block)

    return "\n\n".join(parts)


def _build_messages_with_document(
    document_block:  Dict[str, Any],
    extracted_query: str,
    user_hint:       str,
    context:         str,
    history:         Optional[List[Dict[str, str]]],
) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = list(history or [])

    lines: List[str] = []
    if user_hint.strip():
        lines.append(f"User question: {user_hint.strip()}\n")

    if context:
        lines.append(f"LEGAL CONTEXT FROM DATABASE:\n{context}")
    else:
        lines.append(
            "NOTE: No closely matching legal text was found in the database. "
            "Answer based on what you can determine from the document itself."
        )

    lines.append(f"\n[Document description (auto-extracted): {extracted_query}]")

    messages.append({
        "role":    "user",
        "content": [
            document_block,
            {"type": "text", "text": "\n".join(lines)},
        ],
    })
    return messages


def _build_messages(
    query:   str,
    history: Optional[List[Dict[str, str]]],
) -> List[Dict[str, str]]:
    """
    Construct the Claude messages list.
    Context is now injected into the system prompt template, not the user message.
    """
    messages: List[Dict[str, str]] = list(history or [])
    messages.append({"role": "user", "content": query})
    return messages


# ──────────────────────────────────────────────────────────────────────────────
# SSE event helpers
# ──────────────────────────────────────────────────────────────────────────────

def _intent_event(intent: IntentResult) -> Dict[str, Any]:
    return {
        "type": "intent",
        "data": {
            "intent":     intent.intent.value,
            "category":   intent.category.value,
            "confidence": round(intent.confidence, 3),
            "language":   intent.language,
            "stage":      intent.stage,
        },
    }


def _sources_event(sources: List[SourceItem]) -> Dict[str, Any]:
    return {
        "type": "sources",
        "data": [s.to_dict() for s in sources],
    }


def _token_event(text: str) -> Dict[str, Any]:
    return {"type": "token", "data": text}


def _error_event(message: str) -> Dict[str, Any]:
    return {"type": "error", "data": {"message": message}}


def _citations_event(sources: List[SourceItem]) -> Dict[str, Any]:
    """Curated source citations sent after the LLM response completes."""
    citations = []
    for s in sources[:5]:
        if s.source_type == "section":
            citations.append({
                "law_name":  s.act_title_en or "",
                "section":   s.section_number or "",
                "title":     s.section_title or "",
                "relevance": round(s.relevance_score, 2),
            })
    return {"type": "citations", "data": citations}


def _done_event(
    message_id: str,
    elapsed_ms: int,
    intent: IntentResult,
    query_result: QueryResult,
    full_response: str,
) -> Dict[str, Any]:
    return {
        "type": "done",
        "data": {
            "message_id":       message_id,
            "response_time_ms": elapsed_ms,
            "intent":           intent.intent.value,
            "category":         intent.category.value,
            "sources_count":    len(query_result.sources),
            "strategy":         query_result.strategy,
            "full_response":    full_response,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# RAGPipeline
# ──────────────────────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Async streaming RAG pipeline.

    Dependencies are injected so they can be mocked in tests.
    Use RAGPipeline.create() in production code.
    """

    def __init__(
        self,
        intent_detector:   IntentDetector,
        embedding_service: EmbeddingService,
        query_router:      QueryRouter,
        llm:               anthropic.AsyncAnthropic,
    ) -> None:
        self._intent_detector   = intent_detector
        self._embedding_service = embedding_service
        self._query_router      = query_router
        self._llm               = llm

    @classmethod
    def create(cls) -> "RAGPipeline":
        settings = get_settings()
        return cls(
            intent_detector   = IntentDetector(),
            embedding_service = EmbeddingService.create(),
            query_router      = QueryRouter(),
            llm               = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY),
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def stream(
        self,
        query:                str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        language:             str = 'bn',
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Async generator that yields SSE-compatible dicts.

        Yields in order:
          intent → sources → token... → citations → done
          OR
          intent → error   (on failure)

        DB retrieval (step 4) uses a short-lived internal session that is
        opened and fully closed BEFORE any token yield — so no AsyncSession
        ever spans a generator yield boundary.
        """
        from app.db.database import AsyncSessionLocal

        started_at = time.monotonic()
        message_id = str(uuid.uuid4())
        log        = logger.bind(message_id=message_id, query=query[:60])

        # ── Step 1: Intent detection ──────────────────────────────────────────
        try:
            intent_result = await self._intent_detector.detect(query)
        except Exception as exc:
            log.error("intent_detection_failed", error=str(exc))
            yield _error_event(f"Intent detection failed: {exc}")
            return

        log.info("intent_detected", intent=intent_result.intent, stage=intent_result.stage)
        yield _intent_event(intent_result)

        # ── Step 2: Embedding ─────────────────────────────────────────────────
        embedding: Optional[List[float]] = None
        if intent_result.intent not in _NO_EMBED_INTENTS:
            try:
                embedding = await self._embedding_service.embed(query)
                log.debug("embedding_computed")
            except Exception as exc:
                log.warning("embedding_failed_continuing", error=str(exc))

        # ── Step 3: Query expansion ───────────────────────────────────────────
        expanded_terms = expand_query(query)
        fts_terms = fts_core_terms(query)
        log.debug("query_expanded", original=query[:40], n_terms=len(expanded_terms), fts=fts_terms)

        # ── Step 4: DB retrieval — dedicated short-lived session ──────────────
        try:
            async with AsyncSessionLocal() as db:
                query_result = await self._query_router.route(
                    intent_result, query, embedding, db,
                    expanded_terms=expanded_terms,
                    fts_terms=fts_terms,
                )
            log.info(
                "sources_retrieved",
                count=len(query_result.sources),
                strategy=query_result.strategy,
            )
        except Exception as exc:
            log.error("query_router_failed", error=str(exc))
            query_result = QueryResult(sources=[], strategy="error", needs_llm=True)

        yield _sources_event(query_result.sources)

        # ── Step 5: Build dynamic system prompt with context ──────────────────
        context = _build_context(query_result, query)

        template = (
            _SYSTEM_PROMPT_TEMPLATE_EN if language == "en"
            else _SYSTEM_PROMPT_TEMPLATE_BN
        )
        no_ctx = _NO_CONTEXT_EN if language == "en" else _NO_CONTEXT_BN
        system_prompt = template.format(context=context or no_ctx)

        messages = _build_messages(query, conversation_history)

        # ── Step 6: Stream LLM response ───────────────────────────────────────
        full_response_parts: List[str] = []
        try:
            async with self._llm.messages.stream(
                model      = _LLM_MODEL,
                max_tokens = _MAX_TOKENS,
                system     = system_prompt,
                messages   = messages,
            ) as stream:
                async for text in stream.text_stream:
                    full_response_parts.append(text)
                    yield _token_event(text)

        except anthropic.APIStatusError as exc:
            log.error("llm_api_status_error", status=exc.status_code, error=str(exc))
            yield _error_event(f"LLM API error ({exc.status_code}): {exc.message}")
            return
        except anthropic.APIConnectionError as exc:
            log.error("llm_connection_error", error=str(exc))
            yield _error_event("LLM connection failed. Please try again.")
            return
        except anthropic.APIError as exc:
            log.error("llm_api_error", error=str(exc))
            yield _error_event("LLM request failed. Please try again.")
            return

        # ── Step 7: Citations + Done ──────────────────────────────────────────
        elapsed_ms    = int((time.monotonic() - started_at) * 1000)
        full_response = "".join(full_response_parts)

        if query_result.sources:
            yield _citations_event(query_result.sources)

        log.info(
            "stream_complete",
            elapsed_ms=elapsed_ms,
            response_chars=len(full_response),
            strategy=query_result.strategy,
        )

        yield _done_event(message_id, elapsed_ms, intent_result, query_result, full_response)

    # ── Document vision helpers ───────────────────────────────────────────────

    async def extract_document_query(
        self,
        file_bytes: bytes,
        media_type: str,
        user_hint:  str,
    ) -> str:
        from app.services.document_service import PDF_MEDIA_TYPE, build_content_block

        content_block = build_content_block(file_bytes, media_type)
        prompt_text   = _EXTRACTION_PROMPT
        if user_hint.strip():
            prompt_text += f"\n\nThe user also wrote: {user_hint.strip()}"

        create_kwargs: Dict[str, Any] = {
            "model":      _LLM_MODEL,
            "max_tokens": 512,
            "system":     _EXTRACTION_SYSTEM,
            "messages": [{
                "role":    "user",
                "content": [
                    content_block,
                    {"type": "text", "text": prompt_text},
                ],
            }],
        }

        if media_type == PDF_MEDIA_TYPE:
            response = await self._llm.beta.messages.create(
                **create_kwargs,
                betas=["pdfs-2024-09-25"],
            )
        else:
            response = await self._llm.messages.create(**create_kwargs)

        extracted = response.content[0].text.strip()
        logger.info("document_query_extracted", chars=len(extracted))
        return extracted

    async def stream_with_document(
        self,
        extracted_query:      str,
        document_block:       Dict[str, Any],
        user_hint:            str,
        is_pdf:               bool,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        from app.db.database import AsyncSessionLocal

        started_at = time.monotonic()
        message_id = str(uuid.uuid4())
        log        = logger.bind(message_id=message_id, query=extracted_query[:60])

        # ── Step 1: Intent detection ──────────────────────────────────────────
        try:
            intent_result = await self._intent_detector.detect(extracted_query)
        except Exception as exc:
            log.error("intent_detection_failed", error=str(exc))
            yield _error_event(f"Intent detection failed: {exc}")
            return

        log.info("intent_detected", intent=intent_result.intent, stage=intent_result.stage)
        yield _intent_event(intent_result)

        # ── Step 2: Embedding ─────────────────────────────────────────────────
        embedding: Optional[List[float]] = None
        if intent_result.intent not in _NO_EMBED_INTENTS:
            try:
                embedding = await self._embedding_service.embed(extracted_query)
            except Exception as exc:
                log.warning("embedding_failed_continuing", error=str(exc))

        # ── Step 3: Query expansion ───────────────────────────────────────────
        expanded_terms = expand_query(extracted_query)
        fts_terms      = fts_core_terms(extracted_query)

        # ── Step 4: DB retrieval — dedicated short-lived session ──────────────
        try:
            async with AsyncSessionLocal() as db:
                query_result = await self._query_router.route(
                    intent_result, extracted_query, embedding, db,
                    expanded_terms=expanded_terms,
                    fts_terms=fts_terms,
                )
            log.info("sources_retrieved", count=len(query_result.sources))
        except Exception as exc:
            log.error("query_router_failed", error=str(exc))
            query_result = QueryResult(sources=[], strategy="error", needs_llm=True)

        yield _sources_event(query_result.sources)

        # ── Step 5: Build prompt with document block ──────────────────────────
        context  = _build_context(query_result, extracted_query)
        messages = _build_messages_with_document(
            document_block, extracted_query, user_hint, context, conversation_history
        )

        # ── Step 6: Stream LLM response (PDF needs beta header) ───────────────
        full_response_parts: List[str] = []
        try:
            if is_pdf:
                stream_ctx = self._llm.beta.messages.stream(
                    model      = _LLM_MODEL,
                    max_tokens = _MAX_TOKENS,
                    system     = _DOCUMENT_SYSTEM_PROMPT,
                    messages   = messages,
                    betas      = ["pdfs-2024-09-25"],
                )
            else:
                stream_ctx = self._llm.messages.stream(
                    model      = _LLM_MODEL,
                    max_tokens = _MAX_TOKENS,
                    system     = _DOCUMENT_SYSTEM_PROMPT,
                    messages   = messages,
                )

            async with stream_ctx as stream:
                async for text in stream.text_stream:
                    full_response_parts.append(text)
                    yield _token_event(text)

        except anthropic.APIStatusError as exc:
            log.error("llm_api_status_error", status=exc.status_code, error=str(exc))
            yield _error_event(f"LLM API error ({exc.status_code}): {exc.message}")
            return
        except anthropic.APIConnectionError as exc:
            log.error("llm_connection_error", error=str(exc))
            yield _error_event("LLM connection failed. Please try again.")
            return
        except anthropic.APIError as exc:
            log.error("llm_api_error", error=str(exc))
            yield _error_event("LLM request failed. Please try again.")
            return

        # ── Step 7: Citations + Done ──────────────────────────────────────────
        elapsed_ms    = int((time.monotonic() - started_at) * 1000)
        full_response = "".join(full_response_parts)

        if query_result.sources:
            yield _citations_event(query_result.sources)

        log.info("document_stream_complete", elapsed_ms=elapsed_ms)
        yield _done_event(message_id, elapsed_ms, intent_result, query_result, full_response)
