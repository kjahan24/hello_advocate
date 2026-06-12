"""
Documents router — PDF / DOC / DOCX legal document analysis via Claude.

POST /api/documents/analyze   — AI analysis (returns JSON)
POST /api/documents/report    — generate PDF report from analysis data
"""
from __future__ import annotations

import ast
import base64
import html as html_lib
import io
import json
import re
from datetime import date
from typing import Annotated, List, Literal

import anthropic
import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["documents"])

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

_SYSTEM_PROMPT = (
    "তুমি বাংলাদেশের একজন অভিজ্ঞ আইনজীবী। "
    "Return ONLY valid JSON. No markdown, no backticks, no extra text before or after the JSON."
)

# Single-line schema avoids multi-line truncation issues; no .format() brace escaping needed.
_JSON_SCHEMA = (
    '{"summary": "সারসংক্ষেপ (৩-৫ বাক্য)", '
    '"risks": ["ঝুঁকি ১", "ঝুঁকি ২"], '
    '"dates": ["গুরুত্বপূর্ণ তারিখ/শর্ত ১"], '
    '"advice": "পরামর্শ"}'
)


def _build_prompt(text: str) -> str:
    return (
        "তোমার উত্তর শুধুমাত্র এই JSON format-এ হবে, অন্য কিছু লিখবে না:\n"
        + _JSON_SCHEMA
        + "\n\nআইনি দলিল:\n"
        + text[:4000]
    )


# ─── Robust JSON parser ───────────────────────────────────────────────────────

def _parse_claude_json(raw: str) -> dict:
    """
    4-stage fallback parser for Claude's JSON responses.

    Stage 1 — direct json.loads (fast path, handles well-formed output).
    Stage 2 — strip markdown fences then retry (Claude sometimes wraps output).
    Stage 3 — regex: extract text between first '{' and last '}' (handles
               leading/trailing prose around the JSON object).
    Stage 4 — ast.literal_eval (tolerates single-quoted keys/values).
    All fail  — return a structured error dict so the frontend always gets
               a DocumentAnalysis instead of a 500.
    """
    # Stage 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Stage 2: strip markdown fences and retry
    cleaned = raw
    if "```" in cleaned:
        parts = cleaned.split("```")
        # parts[1] is the content inside fences; strip optional "json" language tag
        inner = parts[1].lstrip("json").strip() if len(parts) > 1 else cleaned
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            cleaned = inner

    # Stage 3: regex — grab from first '{' to last '}'
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Stage 4: ast.literal_eval (handles single-quoted dicts)
    try:
        result = ast.literal_eval(cleaned)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # All failed — return structured error so frontend always renders something
    logger.error("claude_response_parse_failed", raw=raw[:300])
    return {
        "summary": "বিশ্লেষণ সম্পূর্ণ হয়নি — পুনরায় চেষ্টা করুন।",
        "risks": ["JSON পার্সিং ত্রুটি: Claude অপ্রত্যাশিত ফরম্যাটে উত্তর দিয়েছে।"],
        "dates": [],
        "advice": f"কাঁচা প্রতিক্রিয়া (প্রথম ৩০০ অক্ষর): {raw[:300]}",
    }


# ─── Response schema ──────────────────────────────────────────────────────────

class DocumentAnalysis(BaseModel):
    summary: str
    risks: list[str]
    dates: list[str]
    advice: str


# ─── Text extractors ──────────────────────────────────────────────────────────

def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader  # imported here so startup doesn't fail if missing
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document  # python-docx
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_doc(data: bytes) -> str:
    # python-docx cannot read legacy binary .doc — attempt a best-effort decode
    text = data.decode("utf-8", errors="ignore").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="পুরনো .doc ফরম্যাট পড়া যাচ্ছে না। অনুগ্রহ করে .docx বা PDF হিসেবে সেভ করুন।",
        )
    return text


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/documents/analyze", response_model=DocumentAnalysis)
async def analyze_document(
    file: Annotated[UploadFile, File(description="Legal document (PDF, DOC, DOCX — max 10 MB)")],
) -> DocumentAnalysis:

    # ── Validate extension ────────────────────────────────────────────────────
    filename = (file.filename or "").lower()
    ext = ("." + filename.rsplit(".", 1)[-1]) if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"সমর্থিত ফরম্যাট: PDF, DOC, DOCX। আপলোড করা ফাইল: '{file.filename}'",
        )

    # ── Validate size ─────────────────────────────────────────────────────────
    data = await file.read()
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="ফাইলের আকার সর্বোচ্চ ১০ MB হতে পারে।",
        )

    # ── Extract text ──────────────────────────────────────────────────────────
    try:
        if ext == ".pdf":
            text = _extract_pdf(data)
        elif ext == ".docx":
            text = _extract_docx(data)
        else:
            text = _extract_doc(data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("document_extraction_failed", filename=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ডকুমেন্ট থেকে টেক্সট বের করা যায়নি।",
        )

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ডকুমেন্টে কোনো পাঠযোগ্য টেক্সট পাওয়া যায়নি।",
        )

    # ── Analyse with Claude ───────────────────────────────────────────────────
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(text)}],
        )
    except anthropic.APIError as exc:
        logger.error("claude_api_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI বিশ্লেষণ সেবা সাময়িকভাবে অনুপলব্ধ।",
        )

    raw = (message.content[0].text if message.content else "").strip()

    # ── Parse response (4-stage fallback) ────────────────────────────────────
    parsed = _parse_claude_json(raw)
    return DocumentAnalysis(
        summary=str(parsed.get("summary", "")),
        risks=[str(r) for r in parsed.get("risks", [])],
        dates=[str(d) for d in parsed.get("dates", [])],
        advice=str(parsed.get("advice", "")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PDF Report generation
# ─────────────────────────────────────────────────────────────────────────────

# ── Bengali date helpers ──────────────────────────────────────────────────────

_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_BN_MONTHS = [
    "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
]


def _bn_date(d: date) -> str:
    day   = str(d.day).translate(_BN_DIGITS)
    month = _BN_MONTHS[d.month]
    year  = str(d.year).translate(_BN_DIGITS)
    return f"{day} {month}, {year}"


# ── HTML → PDF builder (WeasyPrint + Google Fonts Noto Sans Bengali) ──────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;700&display=swap');
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans Bengali', sans-serif;
    margin: 40px; color: #333; font-size: 14px; line-height: 1.8;
  }}
  h1 {{ color: #064e3b; font-size: 22px; margin-bottom: 4px; }}
  h1 small {{ font-size: 14px; color: #065f46; display: block; margin-top: 4px; }}
  .meta {{ color: #666; font-size: 12px; margin-bottom: 24px; border-bottom: 2px solid #064e3b; padding-bottom: 12px; }}
  .section {{ margin-bottom: 20px; }}
  h2 {{
    font-size: 14px; background: #064e3b; color: white;
    padding: 8px 14px; margin: 0 0 10px; border-radius: 4px;
  }}
  .risk   h2 {{ background: #dc2626; }}
  .date   h2 {{ background: #2563eb; }}
  .advice h2 {{ background: #16a34a; }}
  p {{ margin: 0 0 8px; padding: 0 4px; }}
  ul {{ margin: 0; padding-left: 22px; }}
  li {{ margin-bottom: 6px; }}
  .footer {{
    margin-top: 40px; padding-top: 10px;
    border-top: 1px solid #ccc; font-size: 11px; color: #888;
  }}
</style>
</head>
<body>
  <h1>হ্যালো এ্যাডভকেট<small>আইনি ডকুমেন্ট বিশ্লেষণ রিপোর্ট</small></h1>
  <div class="meta">তারিখ: {date}&nbsp;&nbsp;|&nbsp;&nbsp;ডকুমেন্ট: {filename}</div>

  <div class="section summary">
    <h2>&#x1F4CB; সারসংক্ষেপ</h2>
    <p>{summary}</p>
  </div>

  <div class="section risk">
    <h2>&#x26A0;&#xFE0F; ঝুঁকিপূর্ণ ধারাসমূহ</h2>
    <ul>{risks_html}</ul>
  </div>

  <div class="section date">
    <h2>&#x1F4C5; গুরুত্বপূর্ণ তারিখ ও শর্তাবলী</h2>
    <ul>{dates_html}</ul>
  </div>

  <div class="section advice">
    <h2>&#x1F4A1; পরামর্শ</h2>
    <p>{advice}</p>
  </div>

  <div class="footer">
    এই রিপোর্ট হ্যালো এ্যাডভকেট AI দ্বারা তৈরি।
    আইনি পরামর্শের জন্য বিশেষজ্ঞ আইনজীবীর সাথে যোগাযোগ করুন।
  </div>
</body>
</html>"""


def _build_pdf(
    filename: str,
    summary:  str,
    risks:    List[str],
    dates:    List[str],
    advice:   str,
) -> bytes:
    from weasyprint import HTML  # imported lazily — not needed at startup

    def esc(s: str) -> str:
        return html_lib.escape(s or "তথ্য পাওয়া যায়নি।")

    risks_html = (
        "".join(f"<li>{esc(r)}</li>" for r in risks)
        if risks else "<li>কোনো উল্লেখযোগ্য ঝুঁকি পাওয়া যায়নি।</li>"
    )
    dates_html = (
        "".join(f"<li>{esc(d)}</li>" for d in dates)
        if dates else "<li>কোনো নির্দিষ্ট তারিখ বা শর্ত পাওয়া যায়নি।</li>"
    )

    html_str = _HTML_TEMPLATE.format(
        date      = _bn_date(date.today()),
        filename  = esc(filename),
        summary   = esc(summary),
        risks_html= risks_html,
        dates_html= dates_html,
        advice    = esc(advice),
    )

    return HTML(string=html_str).write_pdf()  # type: ignore[no-any-return]


# ── Request schema ────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    filename: str
    summary:  str
    risks:    List[str]
    dates:    List[str]
    advice:   str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/documents/report", summary="Generate a PDF report from analysis data")
async def generate_report(body: ReportRequest) -> StreamingResponse:
    """
    Accept the JSON analysis result and return a professional Bengali PDF
    document as a file download.
    """
    from urllib.parse import quote

    try:
        pdf_bytes = _build_pdf(
            filename = body.filename or "document",
            summary  = body.summary,
            risks    = body.risks,
            dates    = body.dates,
            advice   = body.advice,
        )
    except Exception as exc:
        logger.error("pdf_generation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF রিপোর্ট তৈরি করা যায়নি।",
        )

    # HTTP headers are latin-1; use RFC 5987 filename* for the Bengali name
    ascii_name    = "hello-advocate-report.pdf"
    unicode_name  = f"হ্যালো-এ্যাডভকেট-রিপোর্ট.pdf"
    encoded_name  = quote(unicode_name, safe="")
    content_disp  = (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{encoded_name}"
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disp,
            "Content-Length":      str(len(pdf_bytes)),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Vision Image Analysis
# ─────────────────────────────────────────────────────────────────────────────

_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_IMAGE_MEDIA_TYPES: dict[str, Literal["image/jpeg", "image/png", "image/gif", "image/webp"]] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}

_VISION_PROMPT_BN = """\
আপনি বাংলাদেশের একজন বিশেষজ্ঞ আইনজীবী। এই ছবিটি বিশ্লেষণ করুন এবং নিচের format-এ বাংলায় উত্তর দিন:

## 📋 ছবির বিষয়বস্তু
[ছবিতে কী আছে তার সংক্ষিপ্ত বর্ণনা]

## ⚖️ আইনি বিশ্লেষণ
[আইনি দৃষ্টিকোণ থেকে গুরুত্বপূর্ণ বিষয়গুলো]

## ⚠️ ঝুঁকি ও সতর্কতা
[কোনো ঝুঁকি বা সমস্যা থাকলে উল্লেখ করুন]

## 📌 গুরুত্বপূর্ণ তথ্য
[তারিখ, নাম, মামলা নম্বর, পরিমাণ ইত্যাদি যদি থাকে]

## 💡 পরামর্শ
[পরবর্তী করণীয় পদক্ষেপ]

যদি ছবিতে কোনো আইনি বিষয় না থাকে, তাহলে ব্যাখ্যা করুন।"""

_VISION_PROMPT_EN = """\
You are an expert lawyer specializing in Bangladesh law. Analyze this image and respond in the following format:

## 📋 Image Content
[Brief description of what's in the image]

## ⚖️ Legal Analysis
[Important points from a legal perspective]

## ⚠️ Risks & Warnings
[Any risks or issues identified]

## 📌 Key Information
[Dates, names, case numbers, amounts if present]

## 💡 Recommendations
[Next steps to take]

If the image contains no legal matter, explain what you see instead."""


def _detect_doc_type(text: str) -> str:
    lower = text.lower()
    if "নোটিশ" in lower or "notice" in lower:
        return "court_notice"
    if "চুক্তি" in lower or "contract" in lower:
        return "contract"
    if "দলিল" in lower or "deed" in lower:
        return "land_deed"
    if "ফর্ম" in lower or " form" in lower:
        return "legal_form"
    if "পরিচয়" in lower or "identity" in lower or "nid" in lower:
        return "id_document"
    return "other"


class ImageAnalysisResponse(BaseModel):
    analysis: str
    detected_type: str
    language: str


@router.post("/documents/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(
    image: Annotated[UploadFile, File(description="Image file (JPG, PNG, WEBP, GIF — max 5 MB)")],
    language: Annotated[str, Form()] = "bn",
) -> ImageAnalysisResponse:

    # ── Validate extension ────────────────────────────────────────────────────
    filename = (image.filename or "").lower()
    ext = ("." + filename.rsplit(".", 1)[-1]) if "." in filename else ""
    if ext not in _ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="শুধু JPG, PNG, WEBP ছবি আপলোড করুন",
        )

    # ── Validate size ─────────────────────────────────────────────────────────
    data = await image.read()
    if len(data) > _IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="ফাইল সাইজ ৫ MB-এর বেশি হতে পারবে না",
        )

    # ── Build vision request ──────────────────────────────────────────────────
    media_type = _IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")
    image_b64  = base64.standard_b64encode(data).decode("utf-8")
    prompt     = _VISION_PROMPT_EN if language == "en" else _VISION_PROMPT_BN

    settings = get_settings()
    client   = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": media_type,
                                "data":       image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.error("claude_vision_api_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI বিশ্লেষণ সেবা সাময়িকভাবে অনুপলব্ধ।",
        )

    analysis      = (message.content[0].text if message.content else "").strip()
    detected_type = _detect_doc_type(analysis)

    return ImageAnalysisResponse(
        analysis=analysis,
        detected_type=detected_type,
        language=language,
    )
