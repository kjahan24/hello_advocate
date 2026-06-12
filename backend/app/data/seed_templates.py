"""Seed 8 legal document templates into the database.

Usage (from project root inside the backend container):
    docker compose exec backend python app/data/seed_templates.py
Or locally:
    cd backend && python app/data/seed_templates.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.template import DocumentTemplate

SEED_TEMPLATES = [
    {
        "title":       "ভাড়া চুক্তিপত্র",
        "title_en":    "Rental Agreement",
        "category":    "land",
        "description": "আবাসিক বা বাণিজ্যিক সম্পত্তি ভাড়ার জন্য আইনি চুক্তিপত্র তৈরি করুন।",
        "is_pro":      False,
        "fields": [
            {"key": "landlord_name",    "label": "বাড়িওয়ালার নাম",     "placeholder": "সম্পূর্ণ নাম লিখুন",          "type": "text",     "required": True},
            {"key": "tenant_name",      "label": "ভাড়াটের নাম",        "placeholder": "সম্পূর্ণ নাম লিখুন",          "type": "text",     "required": True},
            {"key": "property_address", "label": "সম্পত্তির ঠিকানা",    "placeholder": "সম্পূর্ণ ঠিকানা লিখুন",       "type": "textarea", "required": True},
            {"key": "monthly_rent",     "label": "মাসিক ভাড়া (টাকা)",  "placeholder": "যেমন: ১৫,০০০",                "type": "text",     "required": True},
            {"key": "duration",         "label": "চুক্তির মেয়াদ",       "placeholder": "যেমন: ১ বছর / ১২ মাস",        "type": "text",     "required": True},
            {"key": "security_deposit", "label": "জামানতের পরিমাণ (টাকা)", "placeholder": "যেমন: ৩০,০০০",            "type": "text",     "required": True},
        ],
    },
    {
        "title":       "কর্মসংস্থান চুক্তি",
        "title_en":    "Employment Contract",
        "category":    "business",
        "description": "কর্মী নিয়োগের জন্য পেশাদার চুক্তিপত্র — বেতন, দায়িত্ব ও শর্তাবলী সহ।",
        "is_pro":      True,
        "fields": [
            {"key": "employer_name",  "label": "নিয়োগকর্তার নাম/প্রতিষ্ঠান", "placeholder": "প্রতিষ্ঠানের নাম",        "type": "text",     "required": True},
            {"key": "employee_name",  "label": "কর্মীর নাম",                   "placeholder": "সম্পূর্ণ নাম",             "type": "text",     "required": True},
            {"key": "designation",    "label": "পদবি",                          "placeholder": "যেমন: সফটওয়্যার ইঞ্জিনিয়ার", "type": "text",   "required": True},
            {"key": "salary",         "label": "মাসিক বেতন (টাকা)",            "placeholder": "যেমন: ৫০,০০০",            "type": "text",     "required": True},
            {"key": "joining_date",   "label": "যোগদানের তারিখ",               "placeholder": "যেমন: ০১ জুলাই ২০২৬",     "type": "text",     "required": True},
            {"key": "workplace",      "label": "কর্মস্থল",                      "placeholder": "অফিসের ঠিকানা",            "type": "text",     "required": True},
        ],
    },
    {
        "title":       "বিক্রয় চুক্তি",
        "title_en":    "Sale Agreement",
        "category":    "business",
        "description": "পণ্য বা সম্পত্তি ক্রয়-বিক্রয়ের জন্য আইনি চুক্তি।",
        "is_pro":      False,
        "fields": [
            {"key": "seller_name",     "label": "বিক্রেতার নাম",           "placeholder": "সম্পূর্ণ নাম",          "type": "text",     "required": True},
            {"key": "buyer_name",      "label": "ক্রেতার নাম",             "placeholder": "সম্পূর্ণ নাম",          "type": "text",     "required": True},
            {"key": "item_description","label": "পণ্য/সম্পত্তির বিবরণ",   "placeholder": "বিস্তারিত বিবরণ দিন",   "type": "textarea", "required": True},
            {"key": "price",           "label": "মূল্য (টাকা)",            "placeholder": "যেমন: ৫,০০,০০০",       "type": "text",     "required": True},
            {"key": "payment_terms",   "label": "পরিশোধের শর্ত",           "placeholder": "যেমন: নগদ / কিস্তি",    "type": "text",     "required": True},
        ],
    },
    {
        "title":       "তালাকনামা আবেদন",
        "title_en":    "Divorce Application",
        "category":    "family",
        "description": "আদালতে তালাকের আবেদনপত্র তৈরি করুন — মুসলিম পারিবারিক আইন অনুযায়ী।",
        "is_pro":      True,
        "fields": [
            {"key": "applicant_name",        "label": "আবেদনকারীর নাম",             "placeholder": "সম্পূর্ণ নাম",             "type": "text",     "required": True},
            {"key": "respondent_name",        "label": "বিবাদীর নাম",               "placeholder": "সম্পূর্ণ নাম",             "type": "text",     "required": True},
            {"key": "marriage_date",          "label": "বিবাহের তারিখ",             "placeholder": "যেমন: ১৫ মার্চ ২০১৮",      "type": "text",     "required": True},
            {"key": "marriage_registration",  "label": "বিবাহের রেজিস্ট্রেশন নম্বর","placeholder": "কাবিন রেজিস্ট্রি নম্বর",  "type": "text",     "required": True},
            {"key": "divorce_reason",         "label": "তালাকের কারণ",              "placeholder": "বিস্তারিত কারণ উল্লেখ করুন","type": "textarea", "required": True},
        ],
    },
    {
        "title":       "উইল/অসিয়তনামা",
        "title_en":    "Will / Testament",
        "category":    "family",
        "description": "সম্পত্তি ও উত্তরাধিকার বণ্টনের জন্য আইনি উইল তৈরি করুন।",
        "is_pro":      True,
        "fields": [
            {"key": "testator_name",         "label": "উইলকারীর নাম",              "placeholder": "সম্পূর্ণ নাম",                  "type": "text",     "required": True},
            {"key": "address",               "label": "ঠিকানা",                    "placeholder": "সম্পূর্ণ বর্তমান ঠিকানা",       "type": "textarea", "required": True},
            {"key": "property_description",  "label": "সম্পত্তির বিবরণ",           "placeholder": "সব সম্পত্তির বিস্তারিত বিবরণ", "type": "textarea", "required": True},
            {"key": "heirs",                 "label": "উত্তরাধিকারীদের নাম ও অংশ","placeholder": "নাম, সম্পর্ক ও অংশ উল্লেখ করুন","type": "textarea","required": True},
        ],
    },
    {
        "title":       "সাধারণ আমমোক্তারনামা",
        "title_en":    "General Power of Attorney",
        "category":    "other",
        "description": "কাউকে আপনার পক্ষে আইনি কাজ করার ক্ষমতা দিন।",
        "is_pro":      False,
        "fields": [
            {"key": "principal_name",     "label": "মূলীয়ের নাম (ক্ষমতা দাতা)",  "placeholder": "সম্পূর্ণ নাম",              "type": "text",     "required": True},
            {"key": "attorney_name",      "label": "আমমোক্তারের নাম (ক্ষমতা গ্রহীতা)","placeholder": "সম্পূর্ণ নাম",          "type": "text",     "required": True},
            {"key": "powers_description", "label": "ক্ষমতার বিবরণ",               "placeholder": "কী কী কাজ করতে পারবেন তার বিস্তারিত","type": "textarea","required": True},
            {"key": "duration",           "label": "মেয়াদ",                        "placeholder": "যেমন: ১ বছর / অনির্দিষ্টকাল","type": "text",    "required": True},
        ],
    },
    {
        "title":       "শ্রমিক অভিযোগ দরখাস্ত",
        "title_en":    "Labor Complaint Application",
        "category":    "labor",
        "description": "শ্রম আদালতে অভিযোগ দাখিলের জন্য দরখাস্ত তৈরি করুন।",
        "is_pro":      False,
        "fields": [
            {"key": "complainant_name",   "label": "অভিযোগকারীর নাম",    "placeholder": "সম্পূর্ণ নাম",              "type": "text",     "required": True},
            {"key": "organization_name",  "label": "প্রতিষ্ঠানের নাম",    "placeholder": "কোম্পানি/প্রতিষ্ঠানের নাম", "type": "text",     "required": True},
            {"key": "complaint_subject",  "label": "অভিযোগের বিষয়",      "placeholder": "যেমন: অবৈধ ছাঁটাই / বেতন বকেয়া","type": "text","required": True},
            {"key": "incident_date",      "label": "ঘটনার তারিখ",         "placeholder": "যেমন: ০১ জুন ২০২৬",         "type": "text",     "required": True},
            {"key": "details",            "label": "বিস্তারিত বিবরণ",     "placeholder": "সমস্ত ঘটনার বিস্তারিত বিবরণ","type": "textarea", "required": True},
        ],
    },
    {
        "title":       "জমি ক্রয়-বিক্রয় দলিল",
        "title_en":    "Land Sale Deed",
        "category":    "land",
        "description": "জমি হস্তান্তরের জন্য আইনসম্মত দলিল — সাব-রেজিস্ট্রি অফিসে দাখিলের উপযোগী।",
        "is_pro":      True,
        "fields": [
            {"key": "seller_name_nid",  "label": "বিক্রেতার নাম ও NID নম্বর",    "placeholder": "নাম এবং জাতীয় পরিচয়পত্র নম্বর","type": "text","required": True},
            {"key": "buyer_name_nid",   "label": "ক্রেতার নাম ও NID নম্বর",      "placeholder": "নাম এবং জাতীয় পরিচয়পত্র নম্বর","type": "text","required": True},
            {"key": "land_area",        "label": "জমির পরিমাণ",                   "placeholder": "যেমন: ১০ শতাংশ / ০.১০ একর",     "type": "text","required": True},
            {"key": "mouza",            "label": "মৌজার নাম",                     "placeholder": "মৌজার নাম",                      "type": "text","required": True},
            {"key": "khatian",          "label": "খতিয়ান নম্বর",                 "placeholder": "RS/BS খতিয়ান নম্বর",            "type": "text","required": True},
            {"key": "dag",              "label": "দাগ নম্বর",                     "placeholder": "দাগ নম্বর",                       "type": "text","required": True},
            {"key": "price",            "label": "বিক্রয় মূল্য (টাকা)",          "placeholder": "যেমন: ২০,০০,০০০",               "type": "text","required": True},
        ],
    },
]


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            existing = (await session.execute(select(DocumentTemplate))).scalars().all()
            existing_titles = {t.title for t in existing}

            added = 0
            for data in SEED_TEMPLATES:
                if data["title"] in existing_titles:
                    print(f"  skip (exists): {data['title']}")
                    continue
                template = DocumentTemplate(
                    title=data["title"],
                    title_en=data.get("title_en"),
                    category=data["category"],
                    description=data.get("description"),
                    fields=data["fields"],
                    is_pro=data["is_pro"],
                )
                session.add(template)
                added += 1
                print(f"  added: {data['title']} ({'PRO' if data['is_pro'] else 'FREE'})")

            print(f"\nDone — {added} template(s) added, {len(existing_titles)} already existed.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
