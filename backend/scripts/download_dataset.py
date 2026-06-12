#!/usr/bin/env python3
"""
download_dataset.py — Download Bangladesh Legal Acts from HuggingFace as JSON.

Primary method uses huggingface_hub.snapshot_download() to fetch the raw
Parquet files and converts them with pyarrow — no schema inference issues.

If the download fails (network error, auth, dataset unavailable) the script
falls back to 20 built-in sample acts so you can test the full ingestion
pipeline immediately without touching HuggingFace.

Usage
-----
  cd backend
  python scripts/download_dataset.py                # full dataset → data/acts.json
  python scripts/download_dataset.py --output out.json
  python scripts/download_dataset.py --limit 30     # first 30 rows (quick test)
  python scripts/download_dataset.py --sample-only  # skip HuggingFace, use built-in samples

Then ingest
-----------
  python scripts/ingest_acts.py --from-file data/acts.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

# ── optional dependency guards ─────────────────────────────────────────────────

try:
    from huggingface_hub import snapshot_download  # type: ignore[import]
    _HF_HUB_OK = True
except ImportError:
    _HF_HUB_OK = False
    snapshot_download = None  # type: ignore[assignment]

try:
    import pyarrow.parquet as pq  # type: ignore[import]
    _PYARROW_OK = True
except ImportError:
    _PYARROW_OK = False
    pq = None  # type: ignore[assignment]

DATASET_ID = "sakhadib/Bangladesh-Legal-Acts-Dataset"

# Confirmed working URL (HEAD 200, 2026-06-10):
_HF_JSON_URL = (
    "https://huggingface.co/datasets/{dataset_id}/resolve/main/"
    "Contextualized_Bangladesh_Legal_Acts.json"
)

# ══════════════════════════════════════════════════════════════════════════════
# HuggingFace download
# ══════════════════════════════════════════════════════════════════════════════


def _download_via_hub(
    dataset_id: str,
    limit: int | None,
    tmp_dir: str,
) -> list[dict[str, Any]]:
    """Download Parquet files via huggingface_hub, return list of row dicts."""
    if not _HF_HUB_OK:
        raise ImportError(
            "huggingface_hub is not installed.  "
            "Run: pip install huggingface_hub"
        )
    if not _PYARROW_OK:
        raise ImportError(
            "pyarrow is not installed.  "
            "Run: pip install pyarrow"
        )

    print(f"  Downloading '{dataset_id}' via huggingface_hub…", flush=True)
    local_dir: str = snapshot_download(  # type: ignore[misc]
        repo_id=dataset_id,
        repo_type="dataset",
        allow_patterns=["*.parquet"],
        ignore_patterns=["*.md", "*.txt", "*.json", "*.gitattributes"],
        local_dir=tmp_dir,
    )

    parquet_files = sorted(Path(local_dir).rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(
            f"No .parquet files found under {local_dir!r} — "
            "the dataset may have changed its file layout."
        )

    print(f"  Found {len(parquet_files)} Parquet file(s).", flush=True)

    all_rows: list[dict[str, Any]] = []
    for pf in parquet_files:
        table = pq.read_table(str(pf))  # type: ignore[union-attr]
        rows  = table.to_pylist()
        take  = (limit - len(all_rows)) if limit else len(rows)
        all_rows.extend(rows[:take])
        print(
            f"  {pf.name}: {len(rows):,} rows  (running total: {len(all_rows):,})",
            flush=True,
        )
        if limit and len(all_rows) >= limit:
            break

    return all_rows


# ══════════════════════════════════════════════════════════════════════════════
# Direct JSON download (Method 2 — faster, no snapshot_download needed)
# ══════════════════════════════════════════════════════════════════════════════


def _download_via_direct_json(
    dataset_id: str,
    limit: int | None,
) -> list[dict[str, Any]]:
    """
    Download Contextualized_Bangladesh_Legal_Acts.json directly via requests.

    File structure: {"dataset_info": {...}, "acts": [ 1484 dicts ... ]}
    Each act: act_title, act_no, act_year, sections[].section_content, source_url, ...
    """
    try:
        import requests as _req  # type: ignore[import]
    except ImportError:
        raise ImportError("requests not installed — run: pip install requests")

    url = _HF_JSON_URL.format(dataset_id=dataset_id)
    print(f"  Downloading JSON: {url}", flush=True)
    r = _req.get(url, timeout=120)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and "acts" in data:
        acts: list[dict[str, Any]] = data["acts"]
        print(f"  Found {len(acts):,} acts in wrapper JSON.", flush=True)
    elif isinstance(data, list):
        acts = data
    else:
        raise ValueError(f"Unexpected JSON root type: {type(data).__name__}")

    if limit:
        acts = acts[:limit]
    return acts


# ══════════════════════════════════════════════════════════════════════════════
# Built-in sample acts (fallback / offline mode)
# ══════════════════════════════════════════════════════════════════════════════


def _make_samples() -> list[dict[str, Any]]:
    """
    20 realistic Bangladesh legal acts covering every category.
    Field names match the aliases in ingest_acts.py:parse_record():
      act_id / title / title_bn / year / full_text / sections[].{section_no, heading, text}
    """
    return [
        # ── criminal ──────────────────────────────────────────────────────────
        {
            "act_id": "ACT-0001",
            "title": "The Penal Code, 1860",
            "title_bn": "দণ্ডবিধি, ১৮৬০",
            "year": 1860,
            "full_text": (
                "An Act to provide a general Penal Code for Bangladesh. "
                "It defines offences against the state, body, property, reputation, "
                "and public tranquility, along with associated punishments."
            ),
            "sections": [
                {
                    "section_no": "302",
                    "heading": "Punishment for murder",
                    "text": (
                        "Whoever commits murder shall be punished with death, or "
                        "imprisonment for life, and shall also be liable to fine."
                    ),
                },
                {
                    "section_no": "379",
                    "heading": "Punishment for theft",
                    "text": (
                        "Whoever commits theft shall be punished with imprisonment of "
                        "either description for a term which may extend to three years, "
                        "or with fine, or with both."
                    ),
                },
                {
                    "section_no": "420",
                    "heading": "Cheating and dishonestly inducing delivery of property",
                    "text": (
                        "Whoever cheats and thereby dishonestly induces the person "
                        "deceived to deliver any property to any person shall be punished "
                        "with imprisonment for a term which may extend to seven years, "
                        "and shall also be liable to fine."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0002",
            "title": "The Code of Criminal Procedure, 1898",
            "title_bn": "ফৌজদারি কার্যবিধি, ১৮৯৮",
            "year": 1898,
            "full_text": (
                "An Act to consolidate the law relating to Criminal Procedure. "
                "It governs arrest, bail, trial procedure, and investigation powers of police."
            ),
            "sections": [
                {
                    "section_no": "54",
                    "heading": "Arrest without warrant",
                    "text": (
                        "Any police officer may, without an order from a Magistrate and "
                        "without a warrant, arrest any person who has been concerned in "
                        "any cognizable offence or against whom a reasonable complaint "
                        "has been made or credible information has been received."
                    ),
                },
                {
                    "section_no": "167",
                    "heading": "Procedure when investigation cannot be completed in twenty-four hours",
                    "text": (
                        "Whenever any person is arrested and detained in custody and it "
                        "appears that the investigation cannot be completed within the "
                        "period of twenty-four hours, the officer in charge shall transmit "
                        "to the nearest Judicial Magistrate a copy of the diary entries "
                        "together with the accused, and the Magistrate may authorise "
                        "detention not exceeding fifteen days in total."
                    ),
                },
            ],
        },
        # ── civil ─────────────────────────────────────────────────────────────
        {
            "act_id": "ACT-0003",
            "title": "The Code of Civil Procedure, 1908",
            "title_bn": "দেওয়ানি কার্যবিধি, ১৯০৮",
            "year": 1908,
            "full_text": (
                "An Act to consolidate and amend the laws relating to the procedure "
                "of the Courts of Civil Judicature. It governs filing of suits, "
                "service of summons, trial procedure, and appeals."
            ),
            "sections": [
                {
                    "section_no": "9",
                    "heading": "Courts to try all civil suits unless barred",
                    "text": (
                        "The Courts shall have jurisdiction to try all suits of a civil "
                        "nature excepting suits of which their cognizance is either "
                        "expressly or impliedly barred."
                    ),
                },
                {
                    "section_no": "96",
                    "heading": "Appeal from original decree",
                    "text": (
                        "Save where otherwise expressly provided in the body of this Code "
                        "or by any other law for the time being in force, an appeal shall "
                        "lie from every decree passed by any Court exercising original "
                        "jurisdiction to the Court authorised to hear appeals from the "
                        "decisions of such Court."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0004",
            "title": "The Evidence Act, 1872",
            "title_bn": "সাক্ষ্য আইন, ১৮৭২",
            "year": 1872,
            "full_text": (
                "An Act to consolidate, define, and amend the law of Evidence. "
                "It prescribes what facts may be proved, how they may be proved, "
                "and by whom, and governs admissibility of documents and witnesses."
            ),
            "sections": [
                {
                    "section_no": "3",
                    "heading": "Interpretation — Evidence",
                    "text": (
                        "Evidence means and includes: (1) all statements which the Court "
                        "permits or requires to be made before it by witnesses in relation "
                        "to matters of fact under inquiry — called oral evidence; "
                        "(2) all documents including electronic records produced for the "
                        "inspection of the Court — called documentary evidence."
                    ),
                },
                {
                    "section_no": "101",
                    "heading": "Burden of proof",
                    "text": (
                        "Whoever desires any Court to give judgment as to any legal right "
                        "or liability dependent on the existence of facts which he asserts "
                        "must prove that those facts exist. When a person is bound to prove "
                        "the existence of any fact, it is said that the burden of proof "
                        "lies on that person."
                    ),
                },
            ],
        },
        # ── commercial / contract ─────────────────────────────────────────────
        {
            "act_id": "ACT-0005",
            "title": "The Contract Act, 1872",
            "title_bn": "চুক্তি আইন, ১৮৭২",
            "year": 1872,
            "full_text": (
                "An Act to define and amend certain parts of the law relating to contracts. "
                "It governs formation, validity, performance, breach, and remedies for contracts."
            ),
            "sections": [
                {
                    "section_no": "10",
                    "heading": "What agreements are contracts",
                    "text": (
                        "All agreements are contracts if they are made by the free consent "
                        "of parties competent to contract, for a lawful consideration and "
                        "with a lawful object, and are not hereby expressly declared to be void."
                    ),
                },
                {
                    "section_no": "73",
                    "heading": "Compensation for loss or damage caused by breach of contract",
                    "text": (
                        "When a contract has been broken, the party who suffers by such "
                        "breach is entitled to receive from the party who has broken the "
                        "contract, compensation for any loss or damage caused to him "
                        "thereby which naturally arose in the usual course of things from "
                        "such breach, or which the parties knew, when they made the "
                        "contract, to be likely to result from the breach of it."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0006",
            "title": "The Companies Act, 1994",
            "title_bn": "কোম্পানি আইন, ১৯৯৪",
            "year": 1994,
            "full_text": (
                "An Act to consolidate and amend the law relating to companies in Bangladesh. "
                "It governs incorporation, management, winding-up, and regulation of companies."
            ),
            "sections": [
                {
                    "section_no": "11",
                    "heading": "Memorandum of association",
                    "text": (
                        "The memorandum of every company shall state: the name of the company; "
                        "the address of the registered office; the objects of the company; "
                        "the liability of the members; the amount of share capital with which "
                        "the company proposes to be registered and its division into shares."
                    ),
                },
                {
                    "section_no": "93",
                    "heading": "Annual general meeting",
                    "text": (
                        "Every company shall in each year hold a general meeting as its annual "
                        "general meeting in addition to any other meeting in that year and shall "
                        "specify the meeting as such in the notices calling it. Not more than "
                        "fifteen months shall elapse between the date of one annual general "
                        "meeting and that of the next."
                    ),
                },
            ],
        },
        # ── land / property ───────────────────────────────────────────────────
        {
            "act_id": "ACT-0007",
            "title": "The Transfer of Property Act, 1882",
            "title_bn": "সম্পত্তি হস্তান্তর আইন, ১৮৮২",
            "year": 1882,
            "full_text": (
                "An Act to amend the law relating to the Transfer of Property by act of parties. "
                "It governs sale, mortgage, lease, exchange, and gift of immovable property."
            ),
            "sections": [
                {
                    "section_no": "5",
                    "heading": "Transfer of property defined",
                    "text": (
                        "In the following sections 'transfer of property' means an act by "
                        "which a living person conveys property, in present or in future, "
                        "to one or more other living persons, or to himself, or to himself "
                        "and one or more other living persons; and 'to transfer property' "
                        "is to perform such act."
                    ),
                },
                {
                    "section_no": "54",
                    "heading": "Sale defined",
                    "text": (
                        "Sale is a transfer of ownership in exchange for a price paid or "
                        "promised or part-paid and part-promised. Sale of immovable property "
                        "of the value of one hundred taka and upwards can be made only by a "
                        "registered instrument."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0008",
            "title": "The Registration Act, 1908",
            "title_bn": "রেজিস্ট্রেশন আইন, ১৯০৮",
            "year": 1908,
            "full_text": (
                "An Act to consolidate the enactments relating to the Registration of "
                "documents. Registration ensures permanent public record of transactions "
                "relating to immovable property."
            ),
            "sections": [
                {
                    "section_no": "17",
                    "heading": "Documents of which registration is compulsory",
                    "text": (
                        "The following documents shall be registered: instruments of gift of "
                        "immovable property; non-testamentary instruments which purport or "
                        "operate to create, declare, assign, limit, or extinguish any right, "
                        "title or interest of the value of one hundred taka and upwards to "
                        "or in immovable property."
                    ),
                },
                {
                    "section_no": "49",
                    "heading": "Effect of non-registration of documents required to be registered",
                    "text": (
                        "No document required by section 17 to be registered shall affect "
                        "any immovable property comprised therein, or be received as evidence "
                        "of any transaction affecting such property, unless it has been registered."
                    ),
                },
            ],
        },
        # ── family ────────────────────────────────────────────────────────────
        {
            "act_id": "ACT-0009",
            "title": "The Muslim Family Laws Ordinance, 1961",
            "title_bn": "মুসলিম পারিবারিক আইন অধ্যাদেশ, ১৯৬১",
            "year": 1961,
            "full_text": (
                "An Ordinance to give effect to certain recommendations of the Commission "
                "on Marriage and Family Laws. It regulates marriage, polygamy, and talaq "
                "procedures for Muslim citizens of Bangladesh."
            ),
            "sections": [
                {
                    "section_no": "5",
                    "heading": "Registration of marriages",
                    "text": (
                        "Every marriage solemnised under Muslim Law shall be registered in "
                        "accordance with the provisions of this Ordinance. The Union Parishad "
                        "shall grant a certificate of marriage to the parties upon registration."
                    ),
                },
                {
                    "section_no": "6",
                    "heading": "Polygamy",
                    "text": (
                        "No man, during the subsistence of an existing marriage, shall except "
                        "with the previous permission in writing of the Arbitration Council, "
                        "contract another marriage. An application for permission shall state "
                        "reasons for the proposed marriage and whether the existing wife or "
                        "wives have given their consent."
                    ),
                },
                {
                    "section_no": "7",
                    "heading": "Talaq",
                    "text": (
                        "Any man who wishes to divorce his wife shall, as soon as may be after "
                        "the pronouncement of talaq in any form whatsoever, give the Chairman "
                        "notice in writing of his having done so, and shall supply a copy thereof "
                        "to the wife. A talaq, unless revoked earlier expressly or otherwise, "
                        "shall not be effective until the expiration of ninety days from the day "
                        "on which notice is delivered to the Chairman."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0010",
            "title": "The Child Marriage Restraint Act, 2017",
            "title_bn": "বাল্যবিবাহ নিরোধ আইন, ২০১৭",
            "year": 2017,
            "full_text": (
                "An Act to restrain child marriage in Bangladesh. "
                "It raises the minimum marriage age and penalises those who solemnise, "
                "permit, or contract child marriages."
            ),
            "sections": [
                {
                    "section_no": "2",
                    "heading": "Definitions",
                    "text": (
                        "In this Act, 'child' means a person who, if male, has not completed "
                        "twenty-one years of age, and if female, has not completed eighteen "
                        "years of age. 'Child marriage' means a marriage to which either of "
                        "the contracting parties is a child."
                    ),
                },
                {
                    "section_no": "7",
                    "heading": "Punishment for contracting child marriage",
                    "text": (
                        "Whoever contracts a child marriage shall be punished with imprisonment "
                        "for a term which may extend to two years or with fine which may extend "
                        "to one lakh taka, or with both."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0011",
            "title": "The Domestic Violence (Prevention and Protection) Act, 2010",
            "title_bn": "পারিবারিক সহিংসতা (প্রতিরোধ ও সুরক্ষা) আইন, ২০১০",
            "year": 2010,
            "full_text": (
                "An Act to prevent domestic violence and to protect victims of domestic violence "
                "in Bangladesh. It provides civil remedies including protection orders, "
                "residence orders, and monetary relief."
            ),
            "sections": [
                {
                    "section_no": "3",
                    "heading": "Acts constituting domestic violence",
                    "text": (
                        "The following acts shall constitute domestic violence: physical abuse "
                        "including assault causing bodily injury; sexual abuse or coercion; "
                        "psychological or emotional abuse including verbal abuse, harassment and "
                        "intimidation; economic abuse including wrongful deprivation of financial "
                        "resources to which the aggrieved person is entitled."
                    ),
                },
                {
                    "section_no": "10",
                    "heading": "Protection order",
                    "text": (
                        "The Court may, on application by the aggrieved person or a protection "
                        "officer, pass a protection order in favour of the aggrieved person and "
                        "prohibit the respondent from committing any act of domestic violence; "
                        "entering the workplace or school frequented by the aggrieved person; "
                        "making any communication with the aggrieved person."
                    ),
                },
            ],
        },
        # ── labour ────────────────────────────────────────────────────────────
        {
            "act_id": "ACT-0012",
            "title": "The Bangladesh Labour Act, 2006",
            "title_bn": "বাংলাদেশ শ্রম আইন, ২০০৬",
            "year": 2006,
            "full_text": (
                "An Act to consolidate and unify the laws relating to employment of workers, "
                "relations between workers and employers, determination of minimum wages, "
                "payment of wages, compensation for injuries to workers, and formation of "
                "trade unions."
            ),
            "sections": [
                {
                    "section_no": "26",
                    "heading": "Payment of wages on termination of employment",
                    "text": (
                        "Where a worker's service is terminated by the employer, all wages "
                        "including wages in lieu of notice and any compensation to which he "
                        "may be entitled shall be paid to him within seven working days from "
                        "the date of such termination."
                    ),
                },
                {
                    "section_no": "117",
                    "heading": "Maternity benefit",
                    "text": (
                        "A woman worker shall be entitled to maternity benefit for a period "
                        "of eight weeks preceding the expected delivery and eight weeks "
                        "following delivery, provided she has worked for the employer for "
                        "at least six months preceding the date of expected delivery."
                    ),
                },
            ],
        },
        # ── constitutional ────────────────────────────────────────────────────
        {
            "act_id": "ACT-0013",
            "title": "The Constitution of the People's Republic of Bangladesh, 1972",
            "title_bn": "গণপ্রজাতন্ত্রী বাংলাদেশের সংবিধান, ১৯৭২",
            "year": 1972,
            "full_text": (
                "The supreme law of Bangladesh. It establishes the framework of government, "
                "guarantees fundamental rights to citizens, and defines the relationship "
                "between the state and its citizens."
            ),
            "sections": [
                {
                    "section_no": "27",
                    "heading": "Equality before law",
                    "text": "All citizens are equal before law and are entitled to equal protection of law.",
                },
                {
                    "section_no": "31",
                    "heading": "Right to protection of law",
                    "text": (
                        "To enjoy the protection of the law, and to be treated in accordance "
                        "with law, and only in accordance with law, is the inalienable right "
                        "of every citizen, wherever he may be, and of every other person for "
                        "the time being within Bangladesh. No action detrimental to the life, "
                        "liberty, body, reputation or property of any person shall be taken "
                        "except in accordance with law."
                    ),
                },
                {
                    "section_no": "32",
                    "heading": "Protection of right to life and personal liberty",
                    "text": "No person shall be deprived of life or personal liberty save in accordance with law.",
                },
            ],
        },
        # ── banking / finance ─────────────────────────────────────────────────
        {
            "act_id": "ACT-0014",
            "title": "The Negotiable Instruments Act, 1881",
            "title_bn": "হস্তান্তরযোগ্য দলিল আইন, ১৮৮১",
            "year": 1881,
            "full_text": (
                "An Act to define and amend the law relating to Promissory Notes, "
                "Bills of Exchange and Cheques. It also covers cheque dishonour and "
                "related criminal liability."
            ),
            "sections": [
                {
                    "section_no": "6",
                    "heading": "Cheque defined",
                    "text": (
                        "A 'cheque' is a bill of exchange drawn on a specified banker and "
                        "not expressed to be payable otherwise than on demand and it includes "
                        "the electronic image of a truncated cheque and a cheque in the "
                        "electronic form."
                    ),
                },
                {
                    "section_no": "138",
                    "heading": "Dishonour of cheque for insufficiency of funds",
                    "text": (
                        "Where any cheque drawn by a person on an account maintained by him "
                        "with a banker for payment of any amount is returned by the bank unpaid "
                        "because the amount of money standing to the credit of that account is "
                        "insufficient, such person shall be deemed to have committed an offence "
                        "and shall be punished with imprisonment which may extend to one year, "
                        "or with fine which may extend to thrice the amount of the cheque, "
                        "or with both."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0015",
            "title": "The Bank Companies Act, 1991",
            "title_bn": "ব্যাংক কোম্পানি আইন, ১৯৯১",
            "year": 1991,
            "full_text": (
                "An Act relating to banking companies in Bangladesh. It regulates the "
                "establishment, operation, management, and winding up of banks and "
                "authorises Bangladesh Bank to supervise them."
            ),
            "sections": [
                {
                    "section_no": "27",
                    "heading": "Maintenance of cash reserve",
                    "text": (
                        "Every bank company shall maintain in Bangladesh by way of a cash "
                        "reserve a sum equivalent to not less than such percentage as may be "
                        "specified by Bangladesh Bank from time to time of its time and demand "
                        "liabilities in Bangladesh."
                    ),
                },
                {
                    "section_no": "46",
                    "heading": "Penalties for non-compliance",
                    "text": (
                        "Any bank company which fails to comply with the provisions of this "
                        "Act or any directions issued under this Act shall be liable to pay "
                        "to Bangladesh Bank a penalty not exceeding five lakh taka for each "
                        "such failure and, where the failure continues, a further penalty of "
                        "ten thousand taka for each day during which the failure continues."
                    ),
                },
            ],
        },
        # ── tenancy / rent ────────────────────────────────────────────────────
        {
            "act_id": "ACT-0016",
            "title": "The Premises Rent Control Act, 1991",
            "title_bn": "প্রাঙ্গণ ভাড়া নিয়ন্ত্রণ আইন, ১৯৯১",
            "year": 1991,
            "full_text": (
                "An Act to provide for control of rents and regulation of tenancies of "
                "premises in urban areas of Bangladesh."
            ),
            "sections": [
                {
                    "section_no": "10",
                    "heading": "Standard rent",
                    "text": (
                        "The standard rent of any premises shall be the rent which in the "
                        "opinion of the Controller is a fair and reasonable rent having "
                        "regard to the prevailing rent of similar premises in the locality, "
                        "the amenities available, and the condition of the premises."
                    ),
                },
                {
                    "section_no": "18",
                    "heading": "Eviction of tenants",
                    "text": (
                        "A landlord may apply to the Controller for an order directing the "
                        "tenant to vacate the premises where the tenant has not paid rent for "
                        "two consecutive months; or has sublet the premises without the "
                        "written consent of the landlord; or has used the premises for any "
                        "purpose other than that for which it was let."
                    ),
                },
            ],
        },
        # ── consumer rights ───────────────────────────────────────────────────
        {
            "act_id": "ACT-0017",
            "title": "The Consumer Rights Protection Act, 2009",
            "title_bn": "ভোক্তা অধিকার সংরক্ষণ আইন, ২০০৯",
            "year": 2009,
            "full_text": (
                "An Act to provide protection of consumer rights and to prevent "
                "anti-consumer activities including adulteration, false advertising, "
                "overcharging, and sale of defective goods in Bangladesh."
            ),
            "sections": [
                {
                    "section_no": "2",
                    "heading": "Definitions — Consumer rights",
                    "text": (
                        "'Consumer' means any person who purchases goods or services for "
                        "personal use and not for commercial resale. 'Consumer rights' means "
                        "the right to get goods and services at a fair price, the right to "
                        "safety, the right to be informed, and the right to redress."
                    ),
                },
                {
                    "section_no": "45",
                    "heading": "Punishment for adulteration of goods",
                    "text": (
                        "If any trader adulterates any goods for sale or sells or offers for "
                        "sale any adulterated goods, he shall be punishable with imprisonment "
                        "for a term which may extend to three years, or with fine which may "
                        "extend to two lakh taka, or with both."
                    ),
                },
            ],
        },
        # ── digital / cyber ───────────────────────────────────────────────────
        {
            "act_id": "ACT-0018",
            "title": "The Digital Security Act, 2018",
            "title_bn": "ডিজিটাল নিরাপত্তা আইন, ২০১৮",
            "year": 2018,
            "full_text": (
                "An Act to prevent digital crimes and ensure digital security in Bangladesh. "
                "It covers hacking, cyber terrorism, online defamation, and publication of "
                "offensive material in electronic form."
            ),
            "sections": [
                {
                    "section_no": "25",
                    "heading": "Publishing offensive, false, or threatening information",
                    "text": (
                        "If any person publishes or broadcasts any material in a website or "
                        "in any electronic form which is aggressive or frightening, or "
                        "knowingly publishes false information to harm reputation or cause "
                        "confusion, he shall be punished with imprisonment not exceeding "
                        "three years or with fine not exceeding three lakh taka, or with both."
                    ),
                },
                {
                    "section_no": "32",
                    "heading": "Hacking",
                    "text": (
                        "If any person illegally enters into any computer, computer system, "
                        "computer network, or digital device or destroys, alters or disables "
                        "any data therein without lawful authority, he shall be punished with "
                        "imprisonment not exceeding fourteen years or with fine not exceeding "
                        "one crore taka, or with both."
                    ),
                },
            ],
        },
        # ── immigration ───────────────────────────────────────────────────────
        {
            "act_id": "ACT-0019",
            "title": "The Passport Ordinance, 1973",
            "title_bn": "পাসপোর্ট অধ্যাদেশ, ১৯৭৩",
            "year": 1973,
            "full_text": (
                "An Ordinance to provide for the issue of passports and travel documents "
                "to citizens of Bangladesh and to regulate departure from Bangladesh."
            ),
            "sections": [
                {
                    "section_no": "3",
                    "heading": "Issue of passports",
                    "text": (
                        "The Government may issue a passport to any citizen of Bangladesh "
                        "on application made in the prescribed form on payment of the "
                        "prescribed fees. A passport shall be valid for such period and "
                        "subject to such conditions as may be specified therein."
                    ),
                },
                {
                    "section_no": "7",
                    "heading": "Prohibition on departure without valid passport",
                    "text": (
                        "No citizen of Bangladesh shall depart from Bangladesh unless he is "
                        "in possession of a valid passport or travel document issued under "
                        "this Ordinance. Any person who contravenes this provision shall be "
                        "punishable with imprisonment which may extend to three years or fine."
                    ),
                },
            ],
        },
        {
            "act_id": "ACT-0020",
            "title": "The Citizenship Act, 1951",
            "title_bn": "নাগরিকত্ব আইন, ১৯৫১",
            "year": 1951,
            "full_text": (
                "An Act to regulate the acquisition of citizenship of Bangladesh, "
                "the renunciation and deprivation of citizenship, and related matters."
            ),
            "sections": [
                {
                    "section_no": "5",
                    "heading": "Citizenship by registration",
                    "text": (
                        "A person who is not a citizen of Bangladesh may apply for registration "
                        "as a citizen if he has been ordinarily resident in Bangladesh for a "
                        "period of five years immediately preceding the date of application "
                        "and has not been sentenced to imprisonment for any offence within "
                        "those five years."
                    ),
                },
                {
                    "section_no": "14",
                    "heading": "Deprivation of citizenship",
                    "text": (
                        "The Government may, by order, deprive a person of his citizenship "
                        "if it is satisfied that the person has obtained citizenship by "
                        "registration or naturalisation by means of fraud, false "
                        "representation, or concealment of any material fact."
                    ),
                },
            ],
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Main download flow
# ══════════════════════════════════════════════════════════════════════════════


def _safe_default(obj: Any) -> str:
    """json.dumps fallback for non-serialisable pyarrow / numpy types."""
    return str(obj)


def download(
    dataset_id: str,
    output: str,
    limit: int | None,
    sample_only: bool,
) -> None:
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Output: {out_path.resolve()}", flush=True)

    rows: list[dict[str, Any]] = []

    if not sample_only:
        print("\nAttempting HuggingFace download…", flush=True)

        # Method 1: snapshot_download (Parquet via huggingface_hub)
        with tempfile.TemporaryDirectory() as tmp:
            try:
                rows = _download_via_hub(dataset_id, limit, tmp)
                print(f"\nDownloaded {len(rows):,} records via snapshot_download.", flush=True)
            except Exception as exc:
                print(f"\n  snapshot_download failed: {exc}", flush=True)
                rows = []

        # Method 2: direct JSON URL (confirmed working 2026-06-10)
        if not rows:
            print("  Trying direct JSON download…", flush=True)
            try:
                rows = _download_via_direct_json(dataset_id, limit)
                print(f"  Downloaded {len(rows):,} records via direct JSON.", flush=True)
            except Exception as exc:
                print(f"  Direct JSON download failed: {exc}", flush=True)
                print("  Falling back to built-in sample data.", flush=True)
                rows = []

    if not rows:
        samples = _make_samples()
        rows = samples[:limit] if limit else samples
        if not sample_only:
            print(f"Using {len(rows)} built-in sample records.", flush=True)
        else:
            print(f"Generating {len(rows)} built-in sample records.", flush=True)

    print(f"\nWriting {len(rows):,} records to JSON…", end=" ", flush=True)
    out_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=_safe_default),
        encoding="utf-8",
    )
    size_kb = out_path.stat().st_size / 1_024
    print(f"done  ({size_kb:.0f} KB)", flush=True)

    print()
    print("=" * 60)
    print("Next step — ingest into PostgreSQL:")
    print(f"  python scripts/ingest_acts.py --from-file {out_path}")
    print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Download Bangladesh Legal Acts from HuggingFace as local JSON. "
            "Falls back to 20 built-in sample acts if HuggingFace is unreachable."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--output",
        default="data/acts.json",
        metavar="PATH",
        help="Output JSON file path (default: data/acts.json)",
    )
    ap.add_argument(
        "--dataset",
        default=DATASET_ID,
        metavar="DATASET_ID",
        help=f"HuggingFace dataset ID (default: {DATASET_ID})",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Keep only the first N records (useful for quick smoke tests)",
    )
    ap.add_argument(
        "--sample-only",
        action="store_true",
        default=False,
        help="Skip HuggingFace entirely and write the built-in sample acts",
    )
    return ap


def main() -> None:
    args = _build_parser().parse_args()
    download(args.dataset, args.output, args.limit, args.sample_only)


if __name__ == "__main__":
    main()
