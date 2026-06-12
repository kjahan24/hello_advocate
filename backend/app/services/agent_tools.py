"""Agent tools — server-side functions Claude can invoke via tool_use."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.act import Act
from app.models.section import Section

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Tool 1 — search_laws
# ──────────────────────────────────────────────────────────────────────────────

async def search_laws(
    query: str,
    limit: int = 5,
    db: AsyncSession | None = None,
) -> list[dict[str, Any]]:
    """Search Bangladesh laws and sections by keyword using full-text / ILIKE."""
    if db is None:
        return []
    try:
        pattern = f"%{query.lower()}%"
        stmt = (
            select(
                Act.title_en,
                Act.category,
                Act.year,
                Act.act_id,
                Section.section_number,
                Section.title.label("section_title"),
                Section.content_en,
            )
            .join(Section, Section.act_id == Act.id)
            .where(
                Act.is_repealed.is_(False),
                (
                    func.lower(Section.content_en).contains(query.lower())
                    | func.lower(Section.title).contains(query.lower())
                    | func.lower(Act.title_en).contains(query.lower())
                ),
            )
            .limit(limit)
        )
        rows = (await db.execute(stmt)).fetchall()
        return [
            {
                "law_name":       r.title_en,
                "category":       r.category or "",
                "year":           r.year,
                "act_id":         r.act_id,
                "section_number": r.section_number or "",
                "section_title":  r.section_title or "",
                "content":        (r.content_en or "")[:600],
                "relevance_score": 1.0,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("search_laws_error", error=str(exc))
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Tool 2 — get_law_details
# ──────────────────────────────────────────────────────────────────────────────

async def get_law_details(
    law_name: str,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Get full details of a specific Bangladesh law by name."""
    if db is None:
        return {"error": "Database unavailable"}
    try:
        stmt = (
            select(
                Act.id,
                Act.act_id,
                Act.title_en,
                Act.title_bn,
                Act.year,
                Act.category,
                Act.subcategory,
                Act.is_repealed,
            )
            .where(func.lower(Act.title_en).contains(law_name.lower()))
            .limit(1)
        )
        row = (await db.execute(stmt)).fetchone()
        if not row:
            return {"error": f"No law found matching '{law_name}'"}

        count_stmt = select(func.count()).select_from(Section).where(Section.act_id == row.id)
        total_sections = (await db.execute(count_stmt)).scalar() or 0

        return {
            "id":             str(row.id),
            "act_id":         row.act_id,
            "name":           row.title_en,
            "name_bn":        row.title_bn or "",
            "year":           row.year,
            "category":       row.category or "",
            "subcategory":    row.subcategory or "",
            "is_repealed":    row.is_repealed,
            "total_sections": total_sections,
        }
    except Exception as exc:
        logger.error("get_law_details_error", error=str(exc))
        return {"error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Tool 3 — search_legal_templates
# ──────────────────────────────────────────────────────────────────────────────

_TEMPLATES: list[dict[str, str]] = [
    # land
    {"name": "জমি বিক্রয় চুক্তি",        "category": "land",     "description": "জমি ক্রয়-বিক্রয়ের আইনগত চুক্তিপত্র",          "template_id": "land_sale"},
    {"name": "বায়না দলিল",                "category": "land",     "description": "সম্পত্তি ক্রয়ের অগ্রিম চুক্তি",               "template_id": "land_advance"},
    {"name": "ভাড়া চুক্তি",               "category": "land",     "description": "আবাসিক বা বাণিজ্যিক সম্পত্তির ভাড়া চুক্তি",  "template_id": "tenancy"},
    # family
    {"name": "তালাকনামা",                  "category": "family",   "description": "মুসলিম আইনে তালাকের আনুষ্ঠানিক দলিল",         "template_id": "divorce"},
    {"name": "কাবিননামা",                  "category": "family",   "description": "মুসলিম বিবাহের আইনি নিবন্ধন দলিল",            "template_id": "marriage"},
    {"name": "ওয়ারিশনামা",                 "category": "family",   "description": "সম্পত্তির উত্তরাধিকারের সনদ",                  "template_id": "inheritance"},
    # business
    {"name": "ব্যবসায়িক অংশীদারি চুক্তি",  "category": "business", "description": "দুই বা ততোধিক পক্ষের ব্যবসায়িক অংশীদারিত্ব", "template_id": "partnership"},
    {"name": "সেবা চুক্তি",               "category": "business", "description": "পেশাদার সেবা প্রদানের চুক্তি",                "template_id": "service"},
    {"name": "আমমোক্তারনামা",              "category": "business", "description": "আইনগত ক্ষমতা অর্পণের দলিল",                    "template_id": "poa"},
    # labor
    {"name": "নিয়োগপত্র",                  "category": "labor",    "description": "কর্মসংস্থান নিয়োগের আনুষ্ঠানিক চিঠি",          "template_id": "appointment"},
    {"name": "শ্রমিক অভিযোগ আবেদন",        "category": "labor",    "description": "শ্রম আদালতে অভিযোগ দায়েরের ফর্ম",             "template_id": "labor_complaint"},
    {"name": "ছাঁটাই ক্ষতিপূরণ দাবি",      "category": "labor",    "description": "বেআইনি ছাঁটাইয়ের বিরুদ্ধে ক্ষতিপূরণের আবেদন", "template_id": "redundancy"},
    # consumer
    {"name": "ভোক্তা অভিযোগ পত্র",         "category": "consumer", "description": "ত্রুটিপূর্ণ পণ্য বা সেবার বিরুদ্ধে অভিযোগ",   "template_id": "consumer_complaint"},
    {"name": "প্রতিকার দাবিপত্র",           "category": "consumer", "description": "ক্ষতিপূরণ বা পণ্য প্রতিস্থাপনের দাবি",         "template_id": "remedy"},
]


def search_legal_templates(query: str, category: str = "all") -> list[dict[str, str]]:
    """Find legal document templates relevant to a query."""
    q = query.lower()
    results = []
    for tmpl in _TEMPLATES:
        if category != "all" and tmpl["category"] != category:
            continue
        if (
            q in tmpl["name"].lower()
            or q in tmpl["description"].lower()
            or q in tmpl["category"]
        ):
            results.append(tmpl)
    if not results and category == "all":
        results = _TEMPLATES[:5]
    return results[:8]


# ──────────────────────────────────────────────────────────────────────────────
# Tool 4 — calculate_legal_deadline
# ──────────────────────────────────────────────────────────────────────────────

_DEADLINE_RULES: dict[str, dict[str, Any]] = {
    "appeal": {
        "days":        30,
        "legal_basis": "Code of Civil Procedure 1908, Order 41 Rule 1",
        "description": "আপিল দায়েরের সময়সীমা",
    },
    "limitation_contract": {
        "days":        1095,  # 3 years
        "legal_basis": "Limitation Act 1908, Article 115",
        "description": "চুক্তি লঙ্ঘনের মামলার সময়সীমা (৩ বছর)",
    },
    "limitation_tort": {
        "days":        365,  # 1 year
        "legal_basis": "Limitation Act 1908, Article 36",
        "description": "অপকৃত্য মামলার সময়সীমা (১ বছর)",
    },
    "cheque_dishonor": {
        "days":        30,
        "legal_basis": "Negotiable Instruments Act 1881, Section 138",
        "description": "চেক ডিজঅনার নোটিশের সময়সীমা",
    },
    "labor_complaint": {
        "days":        30,
        "legal_basis": "Bangladesh Labour Act 2006, Section 33",
        "description": "শ্রম আদালতে অভিযোগের সময়সীমা",
    },
    "consumer_complaint": {
        "days":        90,
        "legal_basis": "Consumer Rights Protection Act 2009, Section 21",
        "description": "ভোক্তা অধিকার অভিযোগের সময়সীমা",
    },
    "land_dispute": {
        "days":        365,
        "legal_basis": "Limitation Act 1908, Article 144",
        "description": "জমি সংক্রান্ত মামলার সময়সীমা",
    },
}


def calculate_legal_deadline(
    event_type: str,
    start_date: str,
    jurisdiction: str = "bangladesh",
) -> dict[str, Any]:
    """Calculate legal deadlines based on Bangladesh law."""
    rule = _DEADLINE_RULES.get(event_type.lower())
    if not rule:
        keys = ", ".join(_DEADLINE_RULES.keys())
        return {
            "error":       f"Unknown event type '{event_type}'",
            "valid_types": keys,
        }
    try:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            start = datetime.strptime(start_date, "%d/%m/%Y").date()
        deadline = start + timedelta(days=rule["days"])
        today     = date.today()
        days_remaining = (deadline - today).days
        is_past = days_remaining < 0
        return {
            "event_type":     event_type,
            "start_date":     start.isoformat(),
            "deadline_date":  deadline.isoformat(),
            "days_remaining": days_remaining,
            "is_past_deadline": is_past,
            "legal_basis":    rule["legal_basis"],
            "description":    rule["description"],
            "warning":        "⚠️ সময়সীমা পার হয়ে গেছে!" if is_past else "",
            "jurisdiction":   jurisdiction,
        }
    except ValueError as exc:
        return {"error": f"Invalid date format: {exc}. Use YYYY-MM-DD"}


# ──────────────────────────────────────────────────────────────────────────────
# Tool 5 — get_court_info
# ──────────────────────────────────────────────────────────────────────────────

_COURT_DATA: dict[str, dict[str, Any]] = {
    "supreme": {
        "court_name":  "সুপ্রিম কোর্ট অব বাংলাদেশ",
        "court_name_en": "Supreme Court of Bangladesh",
        "divisions":   ["আপিল বিভাগ (Appellate Division)", "হাইকোর্ট বিভাগ (High Court Division)"],
        "jurisdiction": "দেশের সর্বোচ্চ আদালত — সাংবিধানিক বিষয়, আপিল",
        "location":    "রমনা, ঢাকা ১০০০",
        "filing_fees": "বিষয়ভেদে ভিন্ন (৫০০ – ৫০,০০০ টাকা)",
        "contact":     "02-9561099",
    },
    "high_court": {
        "court_name":  "হাইকোর্ট বিভাগ",
        "court_name_en": "High Court Division",
        "jurisdiction": "রিট, আপিল, মূল এখতিয়ার",
        "location":    "রমনা, ঢাকা ১০০০",
        "filing_fees": "১,০০০ – ১০,০০০ টাকা",
        "contact":     "02-9563422",
    },
    "district": {
        "court_name":  "জেলা জজ আদালত",
        "court_name_en": "District Judge Court",
        "jurisdiction": "দেওয়ানি মামলা — ১ লক্ষ টাকার উপরে",
        "location":    "জেলা সদর",
        "filing_fees": "মামলার মূল্যমানের ১%",
        "contact":     "জেলা জজ আদালত ভবন",
    },
    "sessions": {
        "court_name":  "দায়রা জজ আদালত",
        "court_name_en": "Sessions Judge Court",
        "jurisdiction": "গুরুতর ফৌজদারি মামলা — হত্যা, ধর্ষণ, ডাকাতি",
        "location":    "জেলা সদর",
        "filing_fees": "ফৌজদারি মামলায় ফি নেই",
        "contact":     "জেলা দায়রা জজ আদালত",
    },
    "magistrate": {
        "court_name":  "ম্যাজিস্ট্রেট আদালত",
        "court_name_en": "Magistrate Court",
        "jurisdiction": "সাধারণ ফৌজদারি মামলা, জামিন, চার্জশিট",
        "location":    "জেলা ও থানা সদর",
        "filing_fees": "ফৌজদারি মামলায় ফি নেই",
        "contact":     "সংশ্লিষ্ট জেলা",
    },
    "labour": {
        "court_name":  "শ্রম আদালত",
        "court_name_en": "Labour Court",
        "jurisdiction": "শ্রম বিরোধ, ছাঁটাই, মজুরি সংক্রান্ত মামলা",
        "location":    "ঢাকা, চট্টগ্রাম, রাজশাহী, খুলনা, সিলেট",
        "filing_fees": "১০০ – ৫০০ টাকা",
        "contact":     "শ্রম ভবন, ঢাকা",
    },
    "family": {
        "court_name":  "পারিবারিক আদালত",
        "court_name_en": "Family Court",
        "jurisdiction": "বিবাহ, তালাক, ভরণপোষণ, সন্তানের অভিভাবকত্ব",
        "location":    "জেলা সদর",
        "filing_fees": "২০০ – ১,০০০ টাকা",
        "contact":     "জেলা জজ আদালত ভবন",
    },
    "administrative": {
        "court_name":  "প্রশাসনিক ট্রাইব্যুনাল",
        "court_name_en": "Administrative Tribunal",
        "jurisdiction": "সরকারি চাকরি সংক্রান্ত বিরোধ",
        "location":    "ঢাকা",
        "filing_fees": "৫০০ টাকা",
        "contact":     "প্রশাসনিক ট্রাইব্যুনাল ভবন, ঢাকা",
    },
}


def get_court_info(court_type: str, district: str = "dhaka") -> dict[str, Any]:
    """Get information about Bangladesh courts and their jurisdiction."""
    key = court_type.lower().replace(" ", "_").replace("-", "_")
    # fuzzy match
    for k in _COURT_DATA:
        if k in key or key in k:
            info = dict(_COURT_DATA[k])
            info["district"] = district
            return info
    return {
        "available_courts": list(_COURT_DATA.keys()),
        "error": f"Court type '{court_type}' not found. Available: {', '.join(_COURT_DATA.keys())}",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tool 6 — check_legal_eligibility
# ──────────────────────────────────────────────────────────────────────────────

def check_legal_eligibility(
    action_type: str,
    case_details: dict[str, Any],
) -> dict[str, Any]:
    """Check eligibility for bail, appeal, legal aid, or other legal actions."""
    action = action_type.lower()

    if action == "bail":
        offense = str(case_details.get("offense", "")).lower()
        non_bailable = ["murder", "rape", "robbery", "terrorism", "হত্যা", "ধর্ষণ", "ডাকাতি"]
        is_non_bailable = any(w in offense for w in non_bailable)
        if is_non_bailable:
            return {
                "eligible":    False,
                "action_type": "bail",
                "reason":      "অ-জামিনযোগ্য অপরাধ — হাইকোর্ট বা দায়রা জজ আদালতে আবেদন করতে হবে",
                "conditions":  ["উচ্চ আদালতে আবেদন", "পর্যাপ্ত কারণ দর্শানো"],
                "next_steps":  [
                    "হাইকোর্ট বিভাগে জামিন আবেদন করুন",
                    "অভিজ্ঞ ফৌজদারি আইনজীবী নিয়োগ করুন",
                    "মামলার কাগজপত্র সংগ্রহ করুন",
                ],
            }
        return {
            "eligible":    True,
            "action_type": "bail",
            "reason":      "জামিনযোগ্য অপরাধ — ম্যাজিস্ট্রেট আদালতে জামিন পাওয়া সম্ভব",
            "conditions":  ["জামানত প্রদান", "নির্দিষ্ট এলাকায় অবস্থান"],
            "next_steps":  [
                "নিকটস্থ ম্যাজিস্ট্রেট আদালতে আবেদন করুন",
                "জামিনদার এবং জামানত প্রস্তুত রাখুন",
                "আইনজীবীর সহায়তা নিন",
            ],
        }

    if action == "appeal":
        days_since = int(case_details.get("days_since_judgment", 0))
        within_limit = days_since <= 30
        return {
            "eligible":    within_limit,
            "action_type": "appeal",
            "reason":      (
                "রায়ের ৩০ দিনের মধ্যে আপিল করা যাবে"
                if within_limit
                else f"সময়সীমা পার হয়ে গেছে (রায়ের {days_since} দিন পর)"
            ),
            "conditions":  ["নির্দিষ্ট সময়ের মধ্যে দাখিল", "আপিলযোগ্য কারণ"],
            "next_steps":  [
                "উচ্চতর আদালতে আপিল দায়ের করুন" if within_limit else "বিলম্ব মওকুফের আবেদন করুন",
                "রায়ের সার্টিফাইড কপি সংগ্রহ করুন",
                "আপিল আইনজীবী নিয়োগ করুন",
            ],
        }

    if action == "legal_aid":
        monthly_income = int(case_details.get("monthly_income", 999999))
        eligible = monthly_income <= 10000
        return {
            "eligible":    eligible,
            "action_type": "legal_aid",
            "reason":      (
                "আয়সীমার মধ্যে — বিনামূল্যে আইনি সহায়তা পাওয়ার যোগ্য"
                if eligible
                else f"আয় সীমার বাইরে (মাসিক আয় ১০,০০০ টাকার বেশি)"
            ),
            "conditions":  ["আয়ের প্রমাণ সনদ", "স্থানীয় ইউপি/পৌরসভার প্রত্যয়নপত্র"],
            "next_steps":  [
                "জেলা আইনি সহায়তা কমিটিতে আবেদন করুন",
                "জাতীয় আইনগত সহায়তা সংস্থার (NLASO) সাথে যোগাযোগ করুন",
                "হটলাইন: ১৬৪৩০",
            ],
        }

    return {
        "eligible":         None,
        "action_type":      action_type,
        "reason":           f"অজানা অ্যাকশন টাইপ '{action_type}'",
        "valid_action_types": ["bail", "appeal", "legal_aid"],
        "next_steps":       ["আইনজীবীর সাথে পরামর্শ করুন"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher — called by the agent router
# ──────────────────────────────────────────────────────────────────────────────

async def dispatch_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Route a tool_use block to the correct implementation."""
    if tool_name == "search_laws":
        result = await search_laws(
            query=tool_input.get("query", ""),
            limit=int(tool_input.get("limit", 5)),
            db=db,
        )
        return {"laws": result, "count": len(result)}

    if tool_name == "get_law_details":
        return await get_law_details(
            law_name=tool_input.get("law_name", ""),
            db=db,
        )

    if tool_name == "search_legal_templates":
        result = search_legal_templates(
            query=tool_input.get("query", ""),
            category=tool_input.get("category", "all"),
        )
        return {"templates": result, "count": len(result)}

    if tool_name == "calculate_legal_deadline":
        return calculate_legal_deadline(
            event_type=tool_input.get("event_type", ""),
            start_date=tool_input.get("start_date", ""),
            jurisdiction=tool_input.get("jurisdiction", "bangladesh"),
        )

    if tool_name == "get_court_info":
        return get_court_info(
            court_type=tool_input.get("court_type", ""),
            district=tool_input.get("district", "dhaka"),
        )

    if tool_name == "check_legal_eligibility":
        return check_legal_eligibility(
            action_type=tool_input.get("action_type", ""),
            case_details=tool_input.get("case_details", {}),
        )

    return {"error": f"Unknown tool: {tool_name}"}
