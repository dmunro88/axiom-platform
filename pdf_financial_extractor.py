"""Native-PDF financial table extraction for historical source documents."""

import re
from pathlib import Path

import pdfplumber

from financial_extractor import (
    RENT_ROLL_SYNONYMS,
    _coerce_expense,
    _coerce_rent,
    _date,
    _dedupe_records,
    _field_for_header,
    _is_total_category,
    _norm,
    _prepare_rent_data,
)


def _cell_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _find_table_header(table, synonyms, minimum_fields):
    best = None
    for row_index, row in enumerate(table[:12]):
        mapping = {}
        claimed = set()
        for column, value in enumerate(row or []):
            field = _field_for_header(_cell_text(value), synonyms)
            if field and field not in claimed:
                mapping[column] = field
                claimed.add(field)
        if len(mapping) >= minimum_fields:
            return row_index, mapping
        if best is None or len(mapping) > len(best[1]):
            best = (row_index, mapping)
    return best if best and len(best[1]) >= minimum_fields else (None, {})


def _as_of_date_from_text(text, filename):
    combined = f"{text or ''}\n{filename or ''}"
    patterns = (
        r"(?:as of|rent roll date|report date)[:\s]+"
        r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"\b(\d{4}[-_/]\d{1,2}[-_/]\d{1,2})\b",
        r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            return _date(match.group(1).replace("_", "-"))
    month_year = re.search(
        r"\b("
        r"January|February|March|April|May|June|July|August|"
        r"September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
        r")\s+(\d{4})\b",
        combined,
        re.IGNORECASE,
    )
    if month_year:
        return _date(month_year.group(0))
    return None


def _period_year_from_text(text, filename):
    combined = f"{text or ''}\n{filename or ''}"
    match = re.search(r"\b(19|20)\d{2}\b", combined)
    return int(match.group(0)) if match else None


def _period_type_from_text(text):
    normalized = _norm(text).replace("-", " ")
    if "budget" in normalized:
        return "budget", "medium"
    if "pro forma" in normalized or "proforma" in normalized:
        return "proforma", "medium"
    if "year to date" in normalized or "year-to-date" in normalized or "ytd" in normalized:
        return "ytd", "medium"
    if "actual" in normalized or "profit" in normalized or "loss" in normalized:
        return "actual", "medium"
    return "actual", "low"


def _extract_table_rows(table, header_index, mapping, path, page_number, table_number, as_of_date):
    records = []
    for row_index, row in enumerate(table[header_index + 1:], start=header_index + 2):
        data = {}
        confidence = {}
        for column, field in mapping.items():
            if column >= len(row or []):
                continue
            raw_value = _cell_text(row[column])
            if not raw_value:
                continue
            value = _coerce_rent(field, raw_value)
            if value is not None:
                data[field] = value
                confidence[field] = "high"
        data, confidence = _prepare_rent_data(data, confidence)
        anchor = data.get("tenant_name") or data.get("unit_id") or data.get("suite")
        if not anchor:
            continue
        label = _norm(anchor)
        if label.startswith(("total", "subtotal", "average", "grand total")):
            continue
        if as_of_date:
            data["as_of_date"] = as_of_date
            confidence["as_of_date"] = "medium"
        source_locator = f"pdf:page:{page_number}:table:{table_number}:row:{row_index}"
        records.append({
            "data": data,
            "confidence": confidence,
            "source": str(path),
            "source_locator": source_locator,
            "provenance": {
                "source_locator": source_locator,
                "extraction_method": "native_pdf_table_extractor",
            },
        })
    return records


def _group_words_by_line(words):
    lines = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        for line in lines:
            if abs(line["top"] - word["top"]) <= 3:
                line["words"].append(word)
                line["top"] = (line["top"] + word["top"]) / 2
                break
        else:
            lines.append({"top": word["top"], "words": [word]})
    for line in lines:
        line["words"].sort(key=lambda item: item["x0"])
    return lines


def _money_candidate(text):
    value = _cell_text(text)
    if not value or "%" in value:
        return None
    if not re.search(r"\d", value):
        return None
    if not re.fullmatch(r"\(?-?\$?\s*[\d,]+(?:\.\d{1,2})?\)?", value):
        return None
    return _coerce_expense("amount", value)


def _amount_from_line(words):
    for index in range(len(words) - 1, -1, -1):
        amount = _money_candidate(words[index]["text"])
        if amount is not None:
            return index, amount
    return None, None


def _expense_section_state(text, current):
    label = re.sub(r"[^a-z0-9]+", " ", _norm(text)).strip()
    if not label:
        return current
    expense_headings = {
        "expense",
        "expenses",
        "operating expense",
        "operating expenses",
        "other expense",
        "other expenses",
        "other operating expense",
        "other operating expenses",
    }
    if label in expense_headings:
        return "expense"
    if label.endswith(" expenses") and len(label.split()) <= 4:
        return "expense"
    if label.endswith(" expense") and len(label.split()) <= 4:
        return "expense"
    if any(marker in label for marker in ("revenue", "income", "sales")):
        return "income"
    return current


def _valid_expense_category(category):
    label = re.sub(r"[^a-z0-9]+", " ", _norm(category)).strip()
    if not label:
        return False
    if _is_total_category(category):
        return False
    if label.startswith((
        "gross profit",
        "net income",
        "net operating income",
        "noi",
        "income before",
        "cash flow",
    )):
        return False
    if label in {"expenses", "expense", "operating expenses"}:
        return False
    return bool(re.search(r"[a-zA-Z]", category))


def _extract_text_expense_rows(pdf, path, all_text):
    records = []
    period_year = _period_year_from_text(all_text, path.name)
    period_type, period_confidence = _period_type_from_text(all_text)
    section = None
    for page_number, page in enumerate(pdf.pages, start=1):
        words = page.extract_words(x_tolerance=2, y_tolerance=3) or []
        for line_number, line in enumerate(_group_words_by_line(words), start=1):
            line_words = line["words"]
            text = " ".join(word["text"] for word in line_words)
            section = _expense_section_state(text, section)
            if section != "expense":
                continue
            amount_index, amount = _amount_from_line(line_words)
            if amount_index is None:
                continue
            category = " ".join(word["text"] for word in line_words[:amount_index])
            category = re.sub(r"^\W+", "", category).strip()
            if not _valid_expense_category(category):
                continue
            data = {
                "category": category,
                "amount": amount,
                "period_type": period_type,
            }
            confidence = {
                "category": "medium",
                "amount": "medium",
                "period_type": period_confidence,
            }
            if period_year is not None:
                data["period_year"] = period_year
                confidence["period_year"] = "medium"
            source_locator = f"pdf:page:{page_number}:line:{line_number}"
            records.append({
                "data": data,
                "confidence": confidence,
                "source": str(path),
                "source_locator": source_locator,
                "provenance": {
                    "source_locator": source_locator,
                    "extraction_method": "native_pdf_text_position_extractor",
                },
            })
    return records


def extract_financial_pdf(path):
    """Extract native PDF financial records from a PDF.

    Scanned/image-only PDFs are intentionally not OCRed here; they return a
    warning and remain a separate OCR lane.
    """
    path = Path(path)
    result = {
        "rent_roll_entries": [],
        "expense_records": [],
        "warnings": [],
    }
    has_extractable_text = False
    try:
        with pdfplumber.open(path) as pdf:
            all_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
            has_extractable_text = bool(all_text.strip())
            as_of_date = _as_of_date_from_text(all_text, path.name)
            table_count = 0
            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables() or []
                table_count += len(tables)
                for table_number, table in enumerate(tables, start=1):
                    header_index, mapping = _find_table_header(
                        table,
                        RENT_ROLL_SYNONYMS,
                        3,
                    )
                    if header_index is None:
                        continue
                    result["rent_roll_entries"].extend(
                        _extract_table_rows(
                            table,
                            header_index,
                            mapping,
                            path,
                            page_number,
                            table_number,
                            as_of_date,
                        )
                    )
            if has_extractable_text:
                result["expense_records"].extend(
                    _extract_text_expense_rows(pdf, path, all_text)
                )
    except Exception as exc:
        result["warnings"].append(f"Could not open {path.name}: {exc}")
        return result

    result["rent_roll_entries"] = _dedupe_records(
        result["rent_roll_entries"],
        (
            "as_of_date",
            "unit_id",
            "suite",
            "tenant_name",
            "tenant_use",
            "lease_start",
            "lease_end",
            "monthly_rent",
            "annual_rent",
            "sf_leased",
        ),
    )
    result["expense_records"] = _dedupe_records(
        result["expense_records"],
        (
            "period_year",
            "period_type",
            "category",
            "amount",
            "amount_per_sf",
        ),
    )
    if not result["rent_roll_entries"] and not result["expense_records"]:
        if has_extractable_text:
            result["warnings"].append(
                f"  [{path.name}] No native PDF financial table/text found."
            )
        else:
            result["warnings"].append(
                f"  [{path.name}] PDF has no extractable text or tables; OCR is required."
            )
    return result
