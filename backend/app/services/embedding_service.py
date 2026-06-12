"""
EmbeddingService — wraps OpenAI text-embedding-3-small (1536 dims).

Dimension 1536 matches the pgvector column size defined in the migration.
Using multilingual-e5-large (HuggingFace) instead would require changing the
column to VECTOR(1024) — keep that in mind for a future cost-free swap.
"""
from __future__ import annotations

from typing import List

import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger(__name__)

_MODEL      = "text-embedding-3-small"
_DIMENSIONS = 1536
_BATCH_MAX  = 100   # OpenAI hard limit per request


def _clean(text: str) -> str:
    return text.replace("\n", " ").strip()


class EmbeddingService:
    """
    Async embedding client.  All methods are coroutines; reuse one instance
    per process (the underlying AsyncOpenAI client manages its own connection
    pool).
    """

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls) -> "EmbeddingService":
        settings = get_settings()
        return cls(client=AsyncOpenAI(api_key=settings.OPENAI_API_KEY))

    # ── Public API ────────────────────────────────────────────────────────────

    async def embed(self, text: str) -> List[float]:
        """Embed a single string.  Returns a 1536-dim float list."""
        text = _clean(text)
        if not text:
            raise ValueError("Cannot embed empty text")

        logger.debug("embedding_single", chars=len(text))
        resp = await self._client.embeddings.create(
            model=_MODEL,
            input=text,
            dimensions=_DIMENSIONS,
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of strings in chunks of up to _BATCH_MAX.
        Returns embeddings in the same order as the input list.
        """
        cleaned = [_clean(t) for t in texts]
        results: List[List[float]] = []

        for start in range(0, len(cleaned), _BATCH_MAX):
            chunk = cleaned[start : start + _BATCH_MAX]
            logger.debug("embedding_batch_chunk", size=len(chunk))
            resp = await self._client.embeddings.create(
                model=_MODEL,
                input=chunk,
                dimensions=_DIMENSIONS,
            )
            # API returns data sorted by index — preserve that order
            ordered = sorted(resp.data, key=lambda d: d.index)
            results.extend(d.embedding for d in ordered)

        return results
