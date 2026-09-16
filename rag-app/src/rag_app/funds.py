"""Deterministic fund-name detection for retrieval.

One dense query can express only one blend of several fund names, and the
longer Orbis names dominate it: on a question naming four funds the best
Allan Gray Balanced Fund Chunk sat at rank 18 of the Fund Fact Sheet only
list. Naming the funds up front lets the search module run one fund-filtered
query per fund so each named fund gets a place in the candidate set. The
detection is a substring match against a fixed list, not a model call: it
runs before the first streamed byte and must not add latency or a second
place to misread a fund name.
"""
import re

# The 23 distinct ``fund`` metadata values in the index (from
# data/fund_fact_sheets/fund_fact_sheet_chunks.json). Hard-coded because the
# deploy image does not carry data/. Update when funds are added or renamed.
FUND_NAMES: tuple[str, ...] = (
    "Allan Gray - Orbis Global Balanced Feeder AMETF",
    "Allan Gray - Orbis Global Balanced Feeder Fund",
    "Allan Gray - Orbis Global Balanced Prescient Feeder Fund",
    "Allan Gray - Orbis Global Equity Feeder AMETF",
    "Allan Gray - Orbis Global Equity Feeder Fund",
    "Allan Gray - Orbis Global Equity Prescient Feeder Fund",
    "Allan Gray - Orbis Global Optimal Fund of Funds",
    "Allan Gray Africa Bond Fund",
    "Allan Gray Africa ex-SA Equity Fund",
    "Allan Gray Balanced Fund",
    "Allan Gray Bond Fund",
    "Allan Gray Equity Fund",
    "Allan Gray Frontier Markets Equity Fund",
    "Allan Gray Income Fund",
    "Allan Gray Interest Fund",
    "Allan Gray Money Market Fund",
    "Allan Gray Optimal Fund",
    "Allan Gray SA Equity Fund",
    "Allan Gray Stable Fund",
    "Allan Gray Tax-Free Balanced Fund",
    "Orbis Global Equity Fund",
    "Orbis SICAV Global Balanced Fund",
    "Orbis SICAV Global Cautious Fund",
)

# Short names users type on the first turn (which is not rewritten) mapped to
# the full ``fund`` value. An unqualified name means the Allan Gray fund, the
# same rule the Query Rewrite and the system prompt apply. The plain feeder
# aliases do not match the Prescient or AMETF variants because those words
# break the substring; the variants must be written out.
FUND_ALIASES: dict[str, str] = {
    "Balanced Fund": "Allan Gray Balanced Fund",
    "Stable Fund": "Allan Gray Stable Fund",
    "Tax-Free Balanced Fund": "Allan Gray Tax-Free Balanced Fund",
    "Tax Free Balanced Fund": "Allan Gray Tax-Free Balanced Fund",
    "Equity Fund": "Allan Gray Equity Fund",
    "SA Equity Fund": "Allan Gray SA Equity Fund",
    "Bond Fund": "Allan Gray Bond Fund",
    "Income Fund": "Allan Gray Income Fund",
    "Interest Fund": "Allan Gray Interest Fund",
    "Money Market Fund": "Allan Gray Money Market Fund",
    "Optimal Fund": "Allan Gray Optimal Fund",
    "Africa Bond Fund": "Allan Gray Africa Bond Fund",
    "Africa ex-SA Equity Fund": "Allan Gray Africa ex-SA Equity Fund",
    "Frontier Markets Equity Fund": "Allan Gray Frontier Markets Equity Fund",
    "Orbis Global Equity Feeder Fund": "Allan Gray - Orbis Global Equity Feeder Fund",
    "Orbis Global Balanced Feeder Fund": "Allan Gray - Orbis Global Balanced Feeder Fund",
    "Orbis Global Equity Prescient Feeder Fund": "Allan Gray - Orbis Global Equity Prescient Feeder Fund",
    "Orbis Global Balanced Prescient Feeder Fund": "Allan Gray - Orbis Global Balanced Prescient Feeder Fund",
    "Orbis Global Equity Feeder AMETF": "Allan Gray - Orbis Global Equity Feeder AMETF",
    "Orbis Global Balanced Feeder AMETF": "Allan Gray - Orbis Global Balanced Feeder AMETF",
    "Orbis Global Optimal Fund of Funds": "Allan Gray - Orbis Global Optimal Fund of Funds",
    # Articles call the SICAV funds by these names; without them "Orbis Global
    # Balanced Fund" would fall through to the Balanced Fund alias.
    "Orbis Global Balanced Fund": "Orbis SICAV Global Balanced Fund",
    "Orbis Global Cautious Fund": "Orbis SICAV Global Cautious Fund",
}


def _spellings(name: str) -> list[str]:
    """The full name plus, for the "Allan Gray - Orbis" funds, the form without
    the dash, so a rewrite or user that drops it still matches."""
    return [name, name.replace(" - ", " ")] if " - " in name else [name]


def _build_patterns() -> list[tuple[re.Pattern, str]]:
    spellings: dict[str, str] = {}
    for name in FUND_NAMES:
        for spelling in _spellings(name):
            spellings[spelling] = name
    spellings.update(FUND_ALIASES)
    # Longest first, so "Tax-Free Balanced Fund" is consumed before "Balanced
    # Fund" gets a look. Word boundaries keep "balanced funds" (the generic
    # plural) from matching the Balanced Fund.
    ordered = sorted(spellings.items(), key=lambda item: -len(item[0]))
    return [
        (re.compile(rf"(?<!\w){re.escape(spelling)}(?!\w)", re.IGNORECASE), full_name)
        for spelling, full_name in ordered
    ]


_PATTERNS = _build_patterns()


def detect_funds(text: str) -> list[str]:
    """Full ``fund`` names mentioned in ``text``, in order of first appearance,
    deduplicated. Case-insensitive; a matched span is blanked before shorter
    names are tried, so "Orbis Global Balanced Feeder Fund" does not also
    yield the Balanced Fund. Pure function, no I/O."""
    first_seen: dict[str, int] = {}
    remaining = text
    for pattern, full_name in _PATTERNS:
        for match in pattern.finditer(remaining):
            first_seen[full_name] = min(first_seen.get(full_name, match.start()), match.start())
        # Same-length blanking keeps later match positions comparable.
        remaining = pattern.sub(lambda m: " " * len(m.group(0)), remaining)
    return sorted(first_seen, key=first_seen.__getitem__)
