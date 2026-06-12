"""
Templates router — legal document templates & AI generation.

GET    /api/templates                     → list templates (filter by category)
GET    /api/templates/my-documents        → user's generated documents (auth required)
GET    /api/templates/{id}                → single template with fields
POST   /api/templates/{id}/generate       → generate document via Claude (auth required)
POST   /api/templates/documents/{id}/pdf  → render generated document as PDF
"""
from __future__ import annotations

import html as html_lib
import io
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

import anthropic
import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import CurrentUser, get_current_user, get_db_user
from app.db.database import get_db
from app.models.template import DocumentTemplate, GeneratedDocument
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])

_MODEL = "claude-opus-4-5"

# ─── Schemas ──────────────────────────────────────────────────────────────────

class TemplateField(BaseModel):
    key:         str
    label:       str
    placeholder: Optional[str] = None
    type:        str = "text"
    required:    bool = True


class TemplateListItem(BaseModel):
    id:          str
    title:       str
    title_en:    Optional[str]
    category:    str
    description: Optional[str]
    is_pro:      bool
    field_count: int
    usage_count: int


class TemplateDetail(BaseModel):
    id:          str
    title:       str
    title_en:    Optional[str]
    category:    str
    description: Optional[str]
    fields:      List[Dict[str, Any]]
    is_pro:      bool
    usage_count: int


class GenerateRequest(BaseModel):
    field_values: Dict[str, str]


class GenerateResponse(BaseModel):
    document_id: str
    content:     str
    title:       str


class MyDocumentItem(BaseModel):
    id:              str
    template_title:  Optional[str]
    template_id:     Optional[str]
    field_values:    Dict[str, Any]
    content_preview: str
    created_at:      str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_list_item(t: DocumentTemplate) -> TemplateListItem:
    return TemplateListItem(
        id=str(t.id),
        title=t.title,
        title_en=t.title_en,
        category=t.category,
        description=t.description,
        is_pro=t.is_pro,
        field_count=len(t.fields or []),
        usage_count=t.usage_count,
    )


def _to_detail(t: DocumentTemplate) -> TemplateDetail:
    return TemplateDetail(
        id=str(t.id),
        title=t.title,
        title_en=t.title_en,
        category=t.category,
        description=t.description,
        fields=list(t.fields or []),
        is_pro=t.is_pro,
        usage_count=t.usage_count,
    )


def _format_fields_for_prompt(
    fields: List[Dict[str, Any]],
    values: Dict[str, str],
) -> str:
    lines: List[str] = []
    for f in fields:
        key   = f.get("key", "")
        label = f.get("label", key)
        val   = values.get(key, "").strip()
        if val:
            lines.append(f"{label}: {val}")
    return "\n".join(lines) if lines else "(কোনো তথ্য দেওয়া হয়নি)"


# ─── PDF template ─────────────────────────────────────────────────────────────

_PDF_HTML = """\
<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans Bengali', sans-serif;
    font-size: 13px;
    line-height: 1.8;
    color: #1a1a1a;
    background: #fff;
    padding: 40px 50px;
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #064e3b;
    padding-bottom: 16px;
    margin-bottom: 24px;
  }}
  .header h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #064e3b;
    margin-bottom: 4px;
  }}
  .header .subtitle {{
    font-size: 11px;
    color: #666;
  }}
  .date-line {{
    text-align: right;
    font-size: 12px;
    color: #555;
    margin-bottom: 20px;
  }}
  .content {{
    white-space: pre-wrap;
    font-size: 13px;
    line-height: 2;
    text-align: justify;
  }}
  .footer {{
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid #ccc;
    font-size: 10px;
    color: #999;
    text-align: center;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <div class="subtitle">হ্যালো এ্যাডভকেট — AI-সহায়তায় তৈরি আইনি দলিল</div>
  </div>
  <div class="date-line">তারিখ: {date}</div>
  <div class="content">{content}</div>
  <div class="footer">
    ⚠️ এটি AI-সহায়তায় তৈরি একটি খসড়া দলিল। চূড়ান্ত করার আগে একজন যোগ্য আইনজীবীর পরামর্শ নিন।
  </div>
</body>
</html>
"""


def _build_doc_pdf(title: str, content: str) -> bytes:
    from weasyprint import HTML
    today = date.today()
    bn_months = ["জানুয়ারি","ফেব্রুয়ারি","মার্চ","এপ্রিল","মে","জুন",
                 "জুলাই","আগস্ট","সেপ্টেম্বর","অক্টোবর","নভেম্বর","ডিসেম্বর"]
    date_str = f"{today.day} {bn_months[today.month - 1]} {today.year}"
    html_str = _PDF_HTML.format(
        title=html_lib.escape(title),
        date=date_str,
        content=html_lib.escape(content),
    )
    return HTML(string=html_str).write_pdf()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[TemplateListItem])
async def list_templates(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[TemplateListItem]:
    q = select(DocumentTemplate).order_by(DocumentTemplate.is_pro, DocumentTemplate.usage_count.desc())
    if category:
        q = q.where(DocumentTemplate.category == category)
    templates = (await db.execute(q)).scalars().all()
    return [_to_list_item(t) for t in templates]


@router.get("/my-documents", response_model=List[MyDocumentItem])
async def my_documents(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MyDocumentItem]:
    result = await db.execute(select(User).where(User.email == current_user.email))
    user = result.scalar_one_or_none()
    if user is None:
        return []

    q = (
        select(GeneratedDocument)
        .options(selectinload(GeneratedDocument.template))
        .where(GeneratedDocument.user_id == user.id)
        .order_by(GeneratedDocument.created_at.desc())
        .limit(50)
    )
    docs = (await db.execute(q)).scalars().all()
    return [
        MyDocumentItem(
            id=str(d.id),
            template_title=d.template.title if d.template else None,
            template_id=str(d.template_id) if d.template_id else None,
            field_values=dict(d.field_values or {}),
            content_preview=d.generated_content[:200] + ("…" if len(d.generated_content) > 200 else ""),
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
) -> TemplateDetail:
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    result = await db.execute(select(DocumentTemplate).where(DocumentTemplate.id == tid))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_detail(template)


@router.post("/{template_id}/generate", response_model=GenerateResponse)
async def generate_document(
    template_id: str,
    body: GenerateRequest,
    user: User = Depends(get_db_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    result = await db.execute(select(DocumentTemplate).where(DocumentTemplate.id == tid))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_pro and user.plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="এই টেমপ্লেটটি প্রো সদস্যদের জন্য। প্রো প্ল্যানে আপগ্রেড করুন।",
        )

    if user.query_count_today >= user.query_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"আজকের প্রশ্নের সীমা ({user.query_limit}টি) শেষ হয়ে গেছে।",
        )

    fields_text = _format_fields_for_prompt(list(template.fields or []), body.field_values)

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = (
        f'নিচের তথ্য দিয়ে একটি "{template.title}" তৈরি করো। '
        f"দলিলটি বাংলাদেশের আইন অনুযায়ী হবে এবং সম্পূর্ণ বাংলায় লেখা হবে। "
        f"দলিলটি পেশাদার, বিস্তারিত এবং আইনগতভাবে সঠিক হতে হবে।\n\n"
        f"তথ্য:\n{fields_text}\n\n"
        f"একটি সম্পূর্ণ আইনি দলিল তৈরি করো। শুধু দলিলের মূল বিষয়বস্তু লিখবে — "
        f"কোনো ব্যাখ্যা বা মন্তব্য যোগ করবে না।"
    )

    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=3000,
            system=(
                "তুমি বাংলাদেশের একজন অভিজ্ঞ আইনজীবী। "
                "তুমি আইনি দলিল তৈরি করতে পারো। "
                "সবসময় বাংলায় উত্তর দাও। "
                "দলিলে যুক্তিসংগত ধারা ও শর্তাবলী অন্তর্ভুক্ত করো।"
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text
    except Exception as exc:
        logger.error("claude_generation_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="দলিল তৈরিতে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।")

    doc = GeneratedDocument(
        user_id=user.id,
        template_id=template.id,
        field_values=dict(body.field_values),
        generated_content=content,
    )
    db.add(doc)

    template.usage_count += 1
    user.query_count_today += 1

    await db.flush()
    logger.info("document_generated", template=template.title, user_id=str(user.id))

    return GenerateResponse(
        document_id=str(doc.id),
        content=content,
        title=template.title,
    )


@router.post("/documents/{document_id}/pdf")
async def document_pdf(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    user_result = await db.execute(select(User).where(User.email == current_user.email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        select(GeneratedDocument)
        .options(selectinload(GeneratedDocument.template))
        .where(GeneratedDocument.id == did, GeneratedDocument.user_id == user.id)
    )
    result = await db.execute(q)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    title = doc.template.title if doc.template else "আইনি দলিল"

    try:
        pdf_bytes = _build_doc_pdf(title, doc.generated_content)
    except Exception as exc:
        logger.error("pdf_generation_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="PDF তৈরিতে সমস্যা হয়েছে।")

    from urllib.parse import quote
    ascii_name   = "legal-document.pdf"
    unicode_name = f"{title}.pdf"
    encoded_name = quote(unicode_name, safe="")
    content_disp = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disp,
            "Content-Length": str(len(pdf_bytes)),
        },
    )
