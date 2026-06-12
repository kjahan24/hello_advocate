"""
Document processing for the AI Lawyer vision feature.

Pure helper functions — no LLM calls here.  All LLM interactions live in
RAGPipeline so the Anthropic client stays in one place.

Supported formats
-----------------
Images: JPEG, PNG, GIF, WEBP  (max 10 MB)
PDFs:   any valid PDF           (max 32 MB — Claude's beta PDF limit)
"""
from __future__ import annotations

import base64
from typing import Any, Dict

from fastapi import HTTPException, status

# ──────────────────────────────────────────────────────────────────────────────
# MIME type registry
# ──────────────────────────────────────────────────────────────────────────────

_IMAGE_TYPES: Dict[str, str] = {
    "image/jpeg": "image/jpeg",
    "image/jpg":  "image/jpeg",
    "image/png":  "image/png",
    "image/gif":  "image/gif",
    "image/webp": "image/webp",
}

PDF_MEDIA_TYPE = "application/pdf"

# Extension → canonical media type (fallback when browser sends octet-stream)
_EXT_MAP: Dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png":  "image/png",
    "gif": "image/gif",  "webp": "image/webp", "pdf":  PDF_MEDIA_TYPE,
}

_MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
_MAX_PDF_BYTES   = 32 * 1024 * 1024   # 32 MB


# ──────────────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────────────

def validate_upload(filename: str, content_type: str, size: int) -> str:
    """
    Validate file type and size.
    Returns the normalised media_type string accepted by Claude's API.
    Raises HTTPException (413 / 415) on validation failure.
    """
    ct = content_type.split(";")[0].strip().lower()

    # Browsers sometimes send application/octet-stream for local files.
    # Try to infer from the file extension in that case.
    if ct in ("application/octet-stream", "binary/octet-stream", ""):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ct  = _EXT_MAP.get(ext, ct)

    if ct in _IMAGE_TYPES:
        if size > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image too large — maximum 10 MB.",
            )
        return _IMAGE_TYPES[ct]

    if ct == PDF_MEDIA_TYPE:
        if size > _MAX_PDF_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="PDF too large — maximum 32 MB.",
            )
        return PDF_MEDIA_TYPE

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=(
            f"Unsupported file type '{ct}'. "
            "Accepted: JPEG, PNG, GIF, WEBP images or PDF documents."
        ),
    )


def build_content_block(file_bytes: bytes, media_type: str) -> Dict[str, Any]:
    """
    Return a Claude API content block ready to embed in a messages list.

    Images → ``{"type": "image",    "source": {...}}``
    PDFs   → ``{"type": "document", "source": {...}}``  (requires beta at call site)
    """
    b64 = base64.standard_b64encode(file_bytes).decode()

    if media_type == PDF_MEDIA_TYPE:
        return {
            "type":   "document",
            "source": {"type": "base64", "media_type": PDF_MEDIA_TYPE, "data": b64},
        }

    return {
        "type":   "image",
        "source": {"type": "base64", "media_type": media_type, "data": b64},
    }
