"""
Query expansion for Bengali legal terms.

expand_query() returns the original query plus up to 3 synonyms for any
matched Bengali legal keyword, capped at 5 total terms.  These terms are
passed to the QueryRouter for ILIKE keyword search alongside vector search.
"""
from __future__ import annotations

# SYNONYM_MAP: used for ILIKE keyword filtering.
# Terms must be SPECIFIC enough not to flood the results — avoid generic legal
# words like "punishment" or "rights" that appear in thousands of sections.
SYNONYM_MAP: dict[str, list[str]] = {
    "জমি":          ["ভূমি", "জমিজমা", "ভূসম্পত্তি", "land", "property"],
    "তালাক":        ["বিবাহ বিচ্ছেদ", "divorce", "বিচ্ছেদ"],
    "মামলা":        ["মোকদ্দমা", "case", "suit", "petition"],
    "চুরি":         ["theft", "robbery", "দস্যুতা"],
    "খুন":          ["হত্যা", "হত্যাকাণ্ড", "murder", "homicide"],
    "ধর্ষণ":        ["যৌন নিপীড়ন", "rape", "sexual assault"],
    "প্রতারণা":     ["জালিয়াতি", "fraud", "forgery"],
    "শ্রমিক":       ["কর্মী", "কর্মচারী", "worker", "employee", "labor"],
    "বেতন":         ["মজুরি", "পারিশ্রমিক", "salary", "wage"],
    "ভাড়া":         ["ভাড়াটিয়া", "ইজারা", "rent", "lease", "tenancy"],
    "ব্যবসা":       ["বাণিজ্য", "কারবার", "business", "trade", "commerce"],
    "চেক":          ["cheque", "NI Act", "dishonour"],
    "জামিন":        ["bail", "bond"],
    "আপিল":         ["appeal", "revision"],
    "নোটিশ":        ["notice", "summons"],
    "দলিল":         ["deed", "registration"],
    "উত্তরাধিকার":  ["inheritance", "succession", "ওয়ারিশ"],
    "বিবাহ":        ["marriage", "nikah", "বিয়ে"],
    "ভরণপোষণ":      ["maintenance", "alimony"],
    "কারখানা":      ["factory", "industry"],
}

# FTS_EXTRAS: first ASCII synonym used ONLY for ts_rank ordering (fts_core_terms).
# These terms may be common in legal text (like "punishment") so they must NOT
# be added to ILIKE patterns, but they help rank the most relevant section first.
_FTS_EXTRAS: dict[str, str] = {
    "শাস্তি":  "punishment",
    "দণ্ড":    "punishment",
    "অধিকার": "rights",
    "হত্যা":   "murder",
    "নারী":    "woman",
    "সম্পত্তি": "property",
    "চুরি":    "theft",
    "খুন":     "murder",
    "ধর্ষণ":   "rape",
}


def expand_query(query: str) -> list[str]:
    """Return [original_query] + up to 3 synonyms per matched keyword, max 5 total."""
    expanded: list[str] = [query]
    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            expanded.extend(synonyms[:3])
    return expanded[:5]


def fts_core_terms(query: str) -> str:
    """Return a short English FTS phrase for ts_rank length-normalised ordering.

    Uses _FTS_EXTRAS (a dedicated map of Bengali concept → primary English word)
    so the phrase captures different semantic dimensions of the query (e.g.
    "theft punishment") rather than only synonyms of a single concept.
    Also includes the first ASCII synonym from SYNONYM_MAP for any matched key
    not already covered by _FTS_EXTRAS.
    Falls back to "law" if nothing matches.
    """
    seen_values: set[str] = set()
    handled_keys: set[str] = set()
    core: list[str] = []

    # Priority: _FTS_EXTRAS terms (each covers a distinct concept).
    # Track which Bengali keys were handled so we don't double-count via SYNONYM_MAP.
    for key, eng in _FTS_EXTRAS.items():
        if key in query and eng not in seen_values:
            core.append(eng)
            seen_values.add(eng)
            handled_keys.add(key)

    # Supplement with first ASCII synonym from SYNONYM_MAP only for keys NOT
    # already covered by _FTS_EXTRAS — prevents adding synonym-of-same-concept
    # (e.g. "robbery" after "theft" for "চুরি") which would create an AND penalty.
    for key, synonyms in SYNONYM_MAP.items():
        if key in query and key not in handled_keys:
            for s in synonyms:
                if s and all(ord(c) < 256 for c in s) and s not in seen_values:
                    core.append(s)
                    seen_values.add(s)
                    break

    return " ".join(core[:3]) if core else "law"
