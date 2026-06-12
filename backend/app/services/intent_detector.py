"""
Two-stage intent classifier for Bangladesh legal queries.

Stage 1 (~0 ms):  Keyword/regex rules covering ~80% of queries.
Stage 2 (~400 ms): Claude API fallback when Stage 1 confidence < THRESHOLD.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import anthropic
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Domain enums
# ──────────────────────────────────────────────────────────────────────────────

class Intent(str, Enum):
    FIND_LAW       = "FIND_LAW"
    FIND_SECTION   = "FIND_SECTION"
    FIND_CASE      = "FIND_CASE"
    EXPLAIN_RIGHTS = "EXPLAIN_RIGHTS"
    CHECK_PROCESS  = "CHECK_PROCESS"
    COMPARE_LAWS   = "COMPARE_LAWS"
    GET_DOCUMENT   = "GET_DOCUMENT"
    GENERAL_INFO   = "GENERAL_INFO"
    UNKNOWN        = "UNKNOWN"


class Category(str, Enum):
    CRIMINAL            = "criminal"
    CIVIL               = "civil"
    FAMILY              = "family"
    LAND_PROPERTY       = "land_property"
    LABOR_EMPLOYMENT    = "labor_employment"
    CONSTITUTIONAL      = "constitutional"
    COMMERCIAL_BUSINESS = "commercial_business"
    BANKING_FINANCE     = "banking_finance"
    TENANCY_RENT        = "tenancy_rent"
    CONSUMER_RIGHTS     = "consumer_rights"
    DIGITAL_CYBER       = "digital_cyber"
    IMMIGRATION         = "immigration"


# ──────────────────────────────────────────────────────────────────────────────
# Result type
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class IntentResult:
    intent:       Intent
    category:     Category
    confidence:   float          # 0.0 – 1.0
    language:     str            # "bn" | "en" | "mixed"
    key_concepts: List[str]
    stage:        int            # 1 = keyword, 2 = LLM


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — keyword/regex rules
# ──────────────────────────────────────────────────────────────────────────────

# Bengali digit range (০-৯) and ASCII digits both accepted.
_BN_DIGIT = r"[০-৯\d]"

# Each rule: (Intent, base_confidence, list_of_patterns)
# Patterns are matched case-insensitively; Bengali patterns are exact.
_INTENT_RULES: List[Tuple[Intent, float, List[str]]] = [
    # ── FIND_SECTION ──────────────────────────────────────────────────────────
    (
        Intent.FIND_SECTION, 0.92,
        [
            rf"ধারা\s*{_BN_DIGIT}+",          # ধারা ৩০২
            rf"অনুচ্ছেদ\s*{_BN_DIGIT}+",      # অনুচ্ছেদ ২৭
            rf"উপধারা\s*{_BN_DIGIT}+",        # উপধারা ৫
            r"\bsection\s+\d+",               # section 302
            r"\bsec\.\s*\d+",
            r"\bclause\s+\d+",
            r"\barticle\s+\d+\b",
            r"\bsub-?section\s+\d+",
        ],
    ),
    # ── COMPARE_LAWS ──────────────────────────────────────────────────────────
    (
        Intent.COMPARE_LAWS, 0.88,
        [
            r"পার্থক্য\s*(কী|কি|কী\?)?",
            r"তুলনা\s*(কর|করুন)?",
            r"বনাম",
            r"\bdifference\s+between\b",
            r"\bcompare\b",
            r"\bversus\b",
            r"\b vs \b",
            r"\bcontrast\b",
        ],
    ),
    # ── GET_DOCUMENT ──────────────────────────────────────────────────────────
    (
        Intent.GET_DOCUMENT, 0.87,
        [
            r"কোন\s+ফর্ম",
            r"কী\s+কাগজ",
            r"কী\s+কী\s+কাগজ",
            r"দলিল",
            r"সনদ\b",
            r"আবেদনপত্র",
            r"\bwhat\s+form\b",
            r"\bwhich\s+form\b",
            r"\bdocuments?\s+(needed|required|necessary)\b",
            r"\bpapers?\s+(needed|required)\b",
            r"\bcertificate\b",
            r"\baffidavit\b",
        ],
    ),
    # ── CHECK_PROCESS ─────────────────────────────────────────────────────────
    (
        Intent.CHECK_PROCESS, 0.85,
        [
            r"কীভাবে\b",
            r"কিভাবে\b",
            r"পদ্ধতি\s*(কী|কি)?",
            r"প্রক্রিয়া\s*(কী|কি)?",
            r"কী\s+করতে\s+হবে",
            r"কী\s+করব",
            r"মামলা\s+দায়ের",
            r"মামলা\s+করতে",
            r"\bhow\s+to\b",
            r"\bhow\s+do\s+i\b",
            r"\bhow\s+can\s+i\b",
            r"\bprocess\s+(of|for|to)\b",
            r"\bprocedure\s+(for|to)\b",
            r"\bsteps\s+(to|for)\b",
            r"\bfile\s+a\s+(case|complaint|suit|petition)\b",
        ],
    ),
    # ── EXPLAIN_RIGHTS ────────────────────────────────────────────────────────
    (
        Intent.EXPLAIN_RIGHTS, 0.85,
        [
            r"আমার\s+অধিকার",
            r"কী\s+কী\s+অধিকার",
            r"মৌলিক\s+অধিকার",
            r"সাংবিধানিক\s+অধিকার",
            r"\bmy\s+rights?\b",
            r"\bright\s+to\b",
            r"\bam\s+i\s+entitled\b",
            r"\bwhat\s+are\s+(my\s+)?rights?\b",
            r"\bfundamental\s+rights?\b",
            r"\blegal\s+rights?\b",
            r"\bhuman\s+rights?\b",
        ],
    ),
    # ── FIND_CASE ─────────────────────────────────────────────────────────────
    (
        Intent.FIND_CASE, 0.88,
        [
            r"নজির",
            r"মামলার\s+রায়",
            r"আদালতের\s+রায়",
            r"판결",                           # Korean borrowed usage in Bangladeshi legal texts
            r"\bcase\s+law\b",
            r"\bprecedent\b",
            r"\bjudgment\b",
            r"\bjudgement\b",
            r"\bcourt\s+ruling\b",
            r"\bcase\s+study\b",
            r"\bverdict\b",
            r"\bcitation\b",
            r"\bdlr\b",                        # Dhaka Law Reports abbreviation
        ],
    ),
    # ── GENERAL_INFO ──────────────────────────────────────────────────────────
    (
        Intent.GENERAL_INFO, 0.78,
        [
            r"কোথায়\s+পাব",
            r"আইনজীবী\s+কোথায়",
            r"বার\s+কাউন্সিল",
            r"\bwhere\s+can\s+i\s+find\b",
            r"\bhow\s+to\s+find\s+a\s+lawyer\b",
            r"\bbar\s+council\b",
            r"\blegal\s+aid\b",
            r"\blawyer\s+(contact|address|fee)\b",
        ],
    ),
    # ── FIND_LAW (broadest — must stay last) ─────────────────────────────────
    (
        Intent.FIND_LAW, 0.80,
        [
            r"শাস্তি\s*(কী|কি)",
            r"দণ্ড\s*(কী|কি)",
            r"কোন\s+আইনে",
            r"কোন\s+আইন",
            r"আইন\s+(কী|কি|আছে)",
            r"\bpunishment\s+for\b",
            r"\bpenalty\s+for\b",
            r"\bwhat\s+(is\s+the\s+)?law\b",
            r"\bunder\s+what\s+(law|act|section)\b",
            r"\bwhat\s+act\b",
            r"\blegal\s+provision\b",
            r"\boffence\b",
            r"\boffense\b",
        ],
    ),
]

# Category keyword map — first match wins.
_CATEGORY_RULES: List[Tuple[Category, List[str]]] = [
    (
        Category.CRIMINAL,
        [
            r"চুরি", r"ডাকাতি", r"হত্যা", r"খুন", r"ধর্ষণ", r"মারধর",
            r"প্রতারণা", r"জালিয়াতি", r"অপহরণ", r"সন্ত্রাস",
            r"\btheft\b", r"\brobbery\b", r"\bmurder\b", r"\brape\b",
            r"\bassault\b", r"\bfraud\b", r"\bkidnap", r"\bterror",
            r"\bcriminal\b", r"\bpenal\b", r"\bfir\b", r"\bcognizable\b",
        ],
    ),
    (
        Category.FAMILY,
        [
            r"বিবাহ", r"বিয়ে", r"তালাক", r"খোরপোষ", r"সন্তান\s+হেফাজত",
            r"উত্তরাধিকার", r"দেনমোহর", r"বহুবিবাহ",
            r"\bmarriage\b", r"\bdivorce\b", r"\balimony\b", r"\bcustody\b",
            r"\bdower\b", r"\binheritance\b", r"\bpolygamy\b", r"\bfamily\b",
        ],
    ),
    (
        Category.LAND_PROPERTY,
        [
            r"জমি", r"ভূমি", r"সম্পত্তি", r"দখল", r"খাজনা", r"রেজিস্ট্রি",
            r"\bland\b", r"\bproperty\b", r"\breal\s+estate\b", r"\bpossession\b",
            r"\bdeed\b", r"\bregistration\b", r"\beviction\b",
        ],
    ),
    (
        Category.LABOR_EMPLOYMENT,
        [
            r"শ্রমিক", r"কর্মচারী", r"বেতন", r"ছাঁটাই", r"ছুটি", r"শ্রম আদালত",
            r"\bworker\b", r"\bemployee\b", r"\bsalary\b", r"\btermination\b",
            r"\blabou?r\b", r"\bemployment\b", r"\bwage\b", r"\bleave\b",
            r"\bgratuity\b", r"\bprovident\s+fund\b",
        ],
    ),
    (
        Category.CONSTITUTIONAL,
        [
            r"সংবিধান", r"মৌলিক\s+অধিকার", r"রিট", r"সাংবিধানিক",
            r"\bconstitution\b", r"\bfundamental\s+rights?\b", r"\bwrit\b",
            r"\bconstitutional\b", r"\bhigh\s+court\b", r"\bsupreme\s+court\b",
        ],
    ),
    (
        Category.BANKING_FINANCE,
        [
            r"ব্যাংক", r"ঋণ", r"সুদ", r"চেক", r"ডিসঅনার",
            r"\bbank\b", r"\bloan\b", r"\binterest\b", r"\bcheque\b",
            r"\bdishono(?:u)?r\b", r"\bmortgage\b", r"\bnbl\b", r"\bnrb\b",
        ],
    ),
    (
        Category.TENANCY_RENT,
        [
            r"ভাড়া", r"বাড়িওয়ালা", r"ভাড়াটিয়া", r"উচ্ছেদ",
            r"\brent\b", r"\blandlord\b", r"\btenant\b", r"\beviction\b",
            r"\blease\b", r"\btenancy\b",
        ],
    ),
    (
        Category.CONSUMER_RIGHTS,
        [
            r"ভোক্তা", r"পণ্যের\s+মান", r"প্রতারণামূলক\s+বিজ্ঞাপন",
            r"\bconsumer\b", r"\bproduct\s+(defect|quality)\b",
            r"\brefund\b", r"\bwarranty\b", r"\bmisleading\s+ad",
        ],
    ),
    (
        Category.DIGITAL_CYBER,
        [
            r"ডিজিটাল", r"সাইবার", r"হ্যাকিং", r"ইন্টারনেট", r"তথ্য\s+প্রযুক্তি",
            r"\bdigital\b", r"\bcyber\b", r"\bhacking\b", r"\bonline\b",
            r"\bict\b", r"\binternet\b", r"\bsocial\s+media\b", r"\bdata\s+protect",
        ],
    ),
    (
        Category.IMMIGRATION,
        [
            r"ভিসা", r"পাসপোর্ট", r"নাগরিকত্ব", r"বিদেশ\s+গমন",
            r"\bvisa\b", r"\bpassport\b", r"\bcitizenship\b", r"\bimmigration\b",
            r"\bnationality\b", r"\bforeign\s+travel\b",
        ],
    ),
    # civil is the broadest catch-all for contract/tort/civil disputes
    (
        Category.CIVIL,
        [
            r"চুক্তি", r"দেওয়ানি", r"ক্ষতিপূরণ",
            r"\bcontract\b", r"\bcivil\b", r"\btort\b", r"\bdamages\b",
            r"\bcompensation\b", r"\bsuit\b",
        ],
    ),
    (
        Category.COMMERCIAL_BUSINESS,
        [
            r"ব্যবসা", r"কোম্পানি", r"অংশীদারিত্ব", r"ট্রেডমার্ক",
            r"\bbusiness\b", r"\bcompany\b", r"\bpartnership\b",
            r"\btrademark\b", r"\bcommercial\b", r"\bcorporate\b",
        ],
    ),
]


def _detect_language(text: str) -> str:
    """Return 'bn', 'en', or 'mixed' based on script presence."""
    has_bn = bool(re.search(r"[ঀ-৿]", text))
    has_en = bool(re.search(r"[a-zA-Z]", text))
    if has_bn and has_en:
        return "mixed"
    if has_bn:
        return "bn"
    return "en"


def _match_intent(text: str) -> Tuple[Intent, float]:
    """Return the first intent rule that fires and its confidence, or UNKNOWN."""
    lower = text.lower()
    for intent, confidence, patterns in _INTENT_RULES:
        for pat in patterns:
            if re.search(pat, lower):
                return intent, confidence
    return Intent.UNKNOWN, 0.0


def _match_category(text: str) -> Optional[Category]:
    """Return the first category whose keywords match, or None."""
    lower = text.lower()
    for category, patterns in _CATEGORY_RULES:
        for pat in patterns:
            if re.search(pat, lower):
                return category
    return None


def _extract_key_concepts(text: str, intent: Intent, category: Optional[Category]) -> List[str]:
    """Pull a handful of salient tokens to surface in the response."""
    concepts: List[str] = []
    if intent != Intent.UNKNOWN:
        concepts.append(intent.value.lower().replace("_", " "))
    if category:
        concepts.append(category.value.replace("_", " "))
    # Extract any explicit section numbers
    for m in re.finditer(rf"(?:ধারা|section|sec\.|article|clause)\s*([{_BN_DIGIT[1:-1]}\d]+)", text, re.IGNORECASE):
        concepts.append(f"section {m.group(1)}")
    return concepts[:5]


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Claude LLM classifier
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = "You are a legal intent classifier for Bangladesh law. Return only valid JSON."

_USER_PROMPT_TEMPLATE = """\
Classify this legal query for the Bangladesh jurisdiction.
Query: "{query}"

Return ONLY this JSON structure, no other text:
{{
  "intent": "{intents}",
  "category": "{categories}",
  "confidence": <float 0.0-1.0>,
  "language": "bn|en|mixed",
  "key_concepts": ["concept1", "concept2"]
}}

Valid intents: {intents_list}
Valid categories: {categories_list}
"""


def _build_llm_prompt(query: str) -> str:
    intents_list   = ", ".join(i.value for i in Intent)
    categories_list = ", ".join(c.value for c in Category)
    return _USER_PROMPT_TEMPLATE.format(
        query=query,
        intents="<one of the valid intents>",
        categories="<one of the valid categories>",
        intents_list=intents_list,
        categories_list=categories_list,
    )


def _parse_llm_response(raw: str) -> Tuple[Intent, Category, float, str, List[str]]:
    """Parse Claude's JSON response; fall back to UNKNOWN on any error."""
    try:
        data = json.loads(raw)
        intent   = Intent(data["intent"])
        category = Category(data["category"])
        confidence = float(data.get("confidence", 0.75))
        language   = data.get("language", "mixed")
        concepts   = [str(c) for c in data.get("key_concepts", [])][:5]
        return intent, category, confidence, language, concepts
    except Exception as exc:
        logger.warning("llm_parse_failed", error=str(exc), raw=raw[:200])
        return Intent.UNKNOWN, Category.CIVIL, 0.0, "mixed", []


# ──────────────────────────────────────────────────────────────────────────────
# Public detector class
# ──────────────────────────────────────────────────────────────────────────────

class IntentDetector:
    """
    Two-stage intent classifier.

    Stage 1 keyword classifier runs synchronously (~0 ms).
    If confidence < CONFIDENCE_THRESHOLD the query is escalated to
    Stage 2, which calls the Claude API asynchronously (~400 ms).
    """

    CONFIDENCE_THRESHOLD = 0.70
    LLM_MODEL            = "claude-sonnet-4-5"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ── Stage 1 ───────────────────────────────────────────────────────────────

    def _stage1(self, query: str) -> IntentResult:
        intent, confidence = _match_intent(query)
        category           = _match_category(query) or Category.CIVIL
        language           = _detect_language(query)
        concepts           = _extract_key_concepts(query, intent, category)

        return IntentResult(
            intent=intent,
            category=category,
            confidence=confidence,
            language=language,
            key_concepts=concepts,
            stage=1,
        )

    # ── Stage 2 ───────────────────────────────────────────────────────────────

    async def _stage2(self, query: str) -> IntentResult:
        log = logger.bind(query=query[:80])
        try:
            response = await self._client.messages.create(
                model=self.LLM_MODEL,
                max_tokens=256,
                temperature=0,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_llm_prompt(query)}],
            )
            raw = response.content[0].text.strip()
            log.debug("llm_response", raw=raw[:200])
        except anthropic.APIError as exc:
            log.error("llm_api_error", error=str(exc))
            return IntentResult(
                intent=Intent.UNKNOWN,
                category=Category.CIVIL,
                confidence=0.0,
                language=_detect_language(query),
                key_concepts=[],
                stage=2,
            )

        intent, category, confidence, language, concepts = _parse_llm_response(raw)
        return IntentResult(
            intent=intent,
            category=category,
            confidence=confidence,
            language=language,
            key_concepts=concepts,
            stage=2,
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def detect(self, query: str) -> IntentResult:
        """
        Classify a legal query.  Returns an IntentResult indicating intent,
        category, confidence, detected language, and which stage classified it.
        """
        query = query.strip()
        if not query:
            return IntentResult(
                intent=Intent.UNKNOWN,
                category=Category.CIVIL,
                confidence=0.0,
                language="en",
                key_concepts=[],
                stage=1,
            )

        result = self._stage1(query)
        log = logger.bind(query=query[:80], stage=1, intent=result.intent, confidence=result.confidence)

        if result.confidence >= self.CONFIDENCE_THRESHOLD:
            log.info("intent_classified")
            return result

        log.info("intent_low_confidence_escalating_to_llm")
        result = await self._stage2(query)
        logger.bind(query=query[:80], stage=2, intent=result.intent, confidence=result.confidence).info(
            "intent_classified"
        )
        return result
