"""Native-PDF financial table extraction for historical source documents."""

import re
from pathlib import Path

import pdfplumber

from financial_extractor import (
    RENT_ROLL_SYNONYMS,
    _coerce_rent,
    _date,
    _dedupe_records,
    _field_for_header,
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


def extract_financial_pdf(path):
    """Extract native PDF table rent-roll rows from a PDF.

    Scanned/image-only PDFs are intentionally not OCRed here; they return a
    warning and remain a separate OCR lane.
    """
    path = Path(path)
    result = {
        "rent_roll_entries": [],
        "expense_records": [],
        "warnings": [],
    }
    try:
        with pdfplumber.open(path) as pdf:
            all_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
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
    if not result["rent_roll_entries"]:
        result["warnings"].append(
            f"  [{path.name}] No native PDF rent-roll table found."
        )
    elif table_count == 0:
        result["warnings"].append(
            f"  [{path.name}] PDF has no extractable tables; OCR is required."
        )
    return result
