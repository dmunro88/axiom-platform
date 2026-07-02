"""Extract bounded, labeled market-observation sections from Word reports."""

import re
from pathlib import Path


CATEGORY_PATTERNS = (
    ("regional_economy", (
        "regional analysis",
        "regional overview",
        "economic overview",
        "economic analysis",
        "area economy",
    )),
    ("market_area", (
        "market area analysis",
        "market area",
        "market overview",
        "submarket overview",
    )),
    ("neighborhood", (
        "neighborhood analysis",
        "neighborhood description",
        "neighborhood overview",
        "location analysis",
    )),
    ("property_market", (
        "office market",
        "retail market",
        "industrial market",
        "multifamily market",
        "apartment market",
        "land market",
        "lodging market",
        "self storage market",
        "market analysis",
    )),
    ("supply_demand", (
        "supply and demand",
        "supply & demand",
        "market conditions",
        "competitive supply",
        "vacancy analysis",
        "rental market",
    )),
)

MIN_SECTION_CHARACTERS = 80
MAX_SECTION_CHARACTERS = 12_000


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _category(title):
    normalized = _norm(title)
    for category, patterns in CATEGORY_PATTERNS:
        if any(pattern == normalized or pattern in normalized for pattern in patterns):
            return category
    return None


def _is_heading(paragraph):
    text = paragraph.text.strip()
    if not text:
        return False
    style = _norm(getattr(paragraph.style, "name", ""))
    if "heading" in style or style in {"title", "subtitle"}:
        return True
    if len(text) <= 100 and text == text.upper() and any(char.isalpha() for char in text):
        return True
    return False


def extract_market_observations(document, source_path):
    """Return recognized report sections with paragraph-level locators."""
    source_path = str(Path(source_path))
    paragraphs = document.paragraphs
    records = []
    active = None

    def finish(end_index):
        nonlocal active
        if not active:
            return
        text = "\n\n".join(active["paragraphs"]).strip()
        if len(text) >= MIN_SECTION_CHARACTERS:
            if len(text) > MAX_SECTION_CHARACTERS:
                text = text[:MAX_SECTION_CHARACTERS].rstrip()
                active["truncated"] = True
            data = {
                "category": active["category"],
                "title": active["title"],
                "text": text,
            }
            if active.get("truncated"):
                data["truncated"] = "true"
            records.append({
                "data": data,
                "confidence": {
                    "category": "high",
                    "title": "high",
                    "text": "high",
                },
                "source": source_path,
                "source_locator": (
                    f"paragraphs:{active['start_index'] + 1}-{end_index}"
                ),
            })
        active = None

    for index, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip()
        if _is_heading(paragraph):
            finish(index)
            category = _category(text)
            if category:
                active = {
                    "category": category,
                    "title": text,
                    "start_index": index,
                    "paragraphs": [],
                }
            continue
        if active and text:
            active["paragraphs"].append(text)
    finish(len(paragraphs))
    return records
