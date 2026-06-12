"""Seed sample lawyers into the database.

Usage (from project root inside the backend container):
    docker compose exec backend python app/data/seed_lawyers.py
Or locally:
    cd backend && python app/data/seed_lawyers.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.lawyer import Lawyer

SEED_LAWYERS = [
    {
        "name":                 "অ্যাডভোকেট মোহাম্মদ রহমান",
        "email":                "rahman@helloadvocate.example",
        "phone":                "01711-234567",
        "bar_number":           "BAR-DH-2009-001",
        "specializations":      ["family", "civil"],
        "experience_years":     15,
        "fee_per_hour":         "3000.00",
        "fee_per_consultation": "1500.00",
        "location":             "ঢাকা",
        "bio":                  "অ্যাডভোকেট রহমান ঢাকা বার কাউন্সিলের একজন সিনিয়র সদস্য। পারিবারিক আইনে বিশেষজ্ঞ — বিবাহ, তালাক, ভরণপোষণ ও সম্পত্তি বিভাজন মামলায় ১৫ বছরের অভিজ্ঞতা।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.8",
        "total_reviews":        124,
    },
    {
        "name":                 "অ্যাডভোকেট ফাতেমা বেগম",
        "email":                "fatema@helloadvocate.example",
        "phone":                "01819-345678",
        "bar_number":           "BAR-CTG-2014-002",
        "specializations":      ["land_property", "civil"],
        "experience_years":     10,
        "fee_per_hour":         "2500.00",
        "fee_per_consultation": "1200.00",
        "location":             "চট্টগ্রাম",
        "bio":                  "অ্যাডভোকেট ফাতেমা চট্টগ্রামের অন্যতম প্রথম সারির জমি ও সম্পত্তি আইন বিশেষজ্ঞ। জমির দলিল যাচাই, দখলচ্যুতি মামলা ও ক্রয়-বিক্রয় চুক্তিতে দক্ষ।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.7",
        "total_reviews":        89,
    },
    {
        "name":                 "অ্যাডভোকেট আব্দুল করিম",
        "email":                "karim@helloadvocate.example",
        "phone":                "01912-456789",
        "bar_number":           "BAR-DH-2004-003",
        "specializations":      ["commercial_business", "banking_finance"],
        "experience_years":     20,
        "fee_per_hour":         "5000.00",
        "fee_per_consultation": "2500.00",
        "location":             "ঢাকা",
        "bio":                  "অ্যাডভোকেট করিম কর্পোরেট আইনে বাংলাদেশের শীর্ষস্থানীয় বিশেষজ্ঞদের একজন। কোম্পানি নিবন্ধন, চুক্তি প্রণয়ন, ব্যাংকিং বিরোধ ও বাণিজ্যিক মামলায় ২০ বছরের অভিজ্ঞতা।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.9",
        "total_reviews":        203,
    },
    {
        "name":                 "অ্যাডভোকেট নাসরিন সুলতানা",
        "email":                "sultana@helloadvocate.example",
        "phone":                "01615-567890",
        "bar_number":           "BAR-DH-2018-004",
        "specializations":      ["labor_employment"],
        "experience_years":     8,
        "fee_per_hour":         "2000.00",
        "fee_per_consultation": "1000.00",
        "location":             "ঢাকা",
        "bio":                  "অ্যাডভোকেট সুলতানা শ্রম আইন ও কর্মসংস্থান বিরোধ নিষ্পত্তিতে বিশেষজ্ঞ। অন্যায় বরখাস্ত, মজুরি ও শ্রম আদালতের মামলায় শ্রমিক ও নিয়োগকর্তা উভয়কেই প্রতিনিধিত্ব করেন।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.6",
        "total_reviews":        67,
    },
    {
        "name":                 "অ্যাডভোকেট মোহাম্মদ ইসলাম",
        "email":                "islam@helloadvocate.example",
        "phone":                "01517-678901",
        "bar_number":           "BAR-SYL-2012-005",
        "specializations":      ["criminal"],
        "experience_years":     12,
        "fee_per_hour":         "3500.00",
        "fee_per_consultation": "1800.00",
        "location":             "সিলেট",
        "bio":                  "অ্যাডভোকেট ইসলাম সিলেট জেলা ও দায়রা আদালতে ফৌজদারি মামলা পরিচালনায় অভিজ্ঞ। হত্যা, মাদক, জামিন ও আপিল মামলায় বিশেষজ্ঞ।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.5",
        "total_reviews":        91,
    },
    {
        "name":                 "অ্যাডভোকেট রেহানা বেগম",
        "email":                "rehana@helloadvocate.example",
        "phone":                "01318-789012",
        "bar_number":           "BAR-DH-2020-006",
        "specializations":      ["consumer_rights", "civil"],
        "experience_years":     6,
        "fee_per_hour":         "1500.00",
        "fee_per_consultation": "800.00",
        "location":             "ঢাকা",
        "bio":                  "অ্যাডভোকেট রেহানা ভোক্তা অধিকার ও সুরক্ষায় কাজ করেন। পণ্যের মান, প্রতারণামূলক বিজ্ঞাপন ও ই-কমার্স বিরোধ সংক্রান্ত মামলায় দক্ষ।",
        "is_verified":          True,
        "is_available":         True,
        "rating":               "4.4",
        "total_reviews":        42,
    },
]


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        async with db.begin():
            for data in SEED_LAWYERS:
                existing = await db.execute(
                    select(Lawyer).where(Lawyer.bar_number == data["bar_number"])
                )
                if existing.scalar_one_or_none() is not None:
                    print(f"  skip (already exists): {data['name']}")
                    continue

                lawyer = Lawyer(**data)
                db.add(lawyer)
                print(f"  added: {data['name']}")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
