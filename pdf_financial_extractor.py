"""Native-PDF and scanned-PDF financial table extraction for historical
source documents.

Scanned/image-only PDFs are handled by the OCR lane (see docs/OCR_LANE_DESIGN.md):
pages are rasterized with PyMuPDF, oriented, and OCRed with Tesseract, then run
through the *same* header/column and expense-section matching logic used for
native-text PDFs. Every OCR-derived field is tagged confidence "low" regardless
of the OCR engine's own score, and never auto-commits — it flows through the
existing stage -> review -> commit gate like every other harvest record.
"""

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

try:
    import fitz  # PyMuPDF
    _FITZ_OK = True
except ImportError:
    _FITZ_OK = False

try:
    import pytesseract
    from PIL import Image
    _TESSERACT_IMPORT_OK = True
except ImportError:
    _TESSERACT_IMPORT_OK = False

OCR_DPI = 300
OCR_MIN_AVG_CONFIDENCE = 40.0
OCR_PAGES_DIR = Path(__file__).parent / "ingest" / "staged" / "ocr_pages"

_RENT_ROLL_DEDUPE_FIELDS = (
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
)
_EXPENSE_DEDUPE_FIELDS = (
    "period_year",
    "period_type",
    "category",
    "amount",
    "amount_per_sf",
)

_tesseract_binary_ok = None


def _ocr_available():
    """Whether OCR can actually run: both libraries import and the Tesseract
    binary is installed and reachable. Cached after the first check."""
    global _tesseract_binary_ok
    if not (_FITZ_OK and _TESSERACT_IMPORT_OK):
        return False
    if _tesseract_binary_ok is None:
        try:
            pytesseract.get_tesseract_version()
            _tesseract_binary_ok = True
        except Exception:
            _tesseract_binary_ok = False
    return _tesseract_binary_ok


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


def _expense_rows_from_pages(
    page_lines,
    path,
    period_year,
    period_type,
    period_confidence,
    extraction_method,
    provenance_by_page=None,
):
    """Shared expense-line-detection loop for both native text-position PDFs
    and OCR word streams. `page_lines` is an iterable of
    (page_number, lines-from-_group_words_by_line)."""
    records = []
    section = None
    force_low = extraction_method.startswith("ocr")
    for page_number, lines in page_lines:
        for line_number, line in enumerate(lines, start=1):
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
            if force_low:
                confidence = {key: "low" for key in confidence}
            source_locator = f"pdf:page:{page_number}:line:{line_number}"
            provenance = {
                "source_locator": source_locator,
                "extraction_method": extraction_method,
            }
            if provenance_by_page:
                provenance.update(provenance_by_page.get(page_number, {}))
            records.append({
                "data": data,
                "confidence": confidence,
                "source": str(path),
                "source_locator": source_locator,
                "provenance": provenance,
            })
    return records


def _extract_text_expense_rows(pdf, path, all_text):
    period_year = _period_year_from_text(all_text, path.name)
    period_type, period_confidence = _period_type_from_text(all_text)
    page_lines = []
    for page_number, page in enumerate(pdf.pages, start=1):
        words = page.extract_words(x_tolerance=2, y_tolerance=3) or []
        page_lines.append((page_number, _group_words_by_line(words)))
    return _expense_rows_from_pages(
        page_lines,
        path,
        period_year,
        period_type,
        period_confidence,
        "native_pdf_text_position_extractor",
    )


# ─── OCR lane: rasterization, orientation, word extraction ──────────────────


def _rasterize_pdf(path):
    """Render every page of a PDF to a PIL image at OCR_DPI.
    Returns a list of (page_number, PIL.Image)."""
    pages = []
    zoom = OCR_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(str(path)) as doc:
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages.append((index, image))
    return pages


def _ocr_words(image):
    """Run Tesseract on a page image. Returns (words, avg_confidence) where
    words is a list of {"text", "x0", "x1", "top"} dicts — the same shape
    pdfplumber.extract_words() produces, so downstream line/table matching is
    shared between native and OCR sources."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = []
    confidences = []
    for i in range(len(data.get("text", []))):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        if re.fullmatch(r"[|_\-~=]+", text):
            # Table gridlines/borders are frequently misread as bare
            # punctuation by OCR; they carry no field content and only
            # pollute line grouping and column assignment.
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf >= 0:
            confidences.append(conf)
        left = float(data["left"][i])
        top = float(data["top"][i])
        width = float(data["width"][i])
        words.append({"text": text, "x0": left, "x1": left + width, "top": top})
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return words, avg_confidence


def _correct_orientation(image):
    """Return (oriented_image, degrees_applied). Tries Tesseract's own
    orientation/script detection first; falls back to a brute-force scan of
    the four right-angle rotations (scored by word count * avg confidence)
    when OSD fails, which is common on noisy or low-contrast scans."""
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        rotate = int(osd.get("rotate", 0)) % 360
        if rotate:
            return image.rotate(-rotate, expand=True), rotate
        return image, 0
    except Exception:
        pass
    best_image, best_degrees, best_score = image, 0, -1.0
    for degrees in (0, 90, 180, 270):
        candidate = image if degrees == 0 else image.rotate(-degrees, expand=True)
        try:
            words, avg_confidence = _ocr_words(candidate)
        except Exception:
            continue
        score = len(words) * avg_confidence
        if score > best_score:
            best_image, best_degrees, best_score = candidate, degrees, score
    return best_image, best_degrees


def _save_review_image(image, source_sha256, page_number):
    """Save the (oriented) page image for the human reviewer to visually
    cross-check OCR output against. Returns a path relative to the platform
    root, or None on failure."""
    try:
        OCR_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{(source_sha256 or 'unknown')[:16]}_p{page_number}.png"
        dest = OCR_PAGES_DIR / filename
        if not dest.exists():
            image.save(dest, format="PNG")
        return str(dest.relative_to(Path(__file__).parent))
    except Exception:
        return None


# Gap threshold for treating adjacent OCR words as the same header cell vs.
# different columns. Empirically, at OCR_DPI=300 a multi-word cell like
# "Monthly Rent" (one visual header, OCR'd as two word boxes) has an internal
# gap of roughly 10-15px, while genuine column gutters run 50px+. This is
# DPI-relative because we control the rasterization DPI ourselves.
_HEADER_CELL_GAP_PX = OCR_DPI * 0.12


def _cluster_header_cells(words):
    """Group a header line's words into visual cells using horizontal gaps,
    so a multi-word header like "Monthly Rent" is matched as one cell instead
    of guessed at via word n-grams (which can spuriously span two unrelated
    adjacent columns, e.g. a "Tenant" column immediately followed by a "Use"
    column misread as the single phrase "tenant use")."""
    if not words:
        return []
    cells = [[words[0]]]
    for prev, word in zip(words, words[1:]):
        gap = word["x0"] - prev["x1"]
        if gap > _HEADER_CELL_GAP_PX:
            cells.append([word])
        else:
            cells[-1].append(word)
    return cells


def _ocr_header_bands(lines, synonyms, minimum_fields, max_header_lines=12):
    """Find the best header line among the first few OCR lines and return
    (header_line, bands) where each band is
    {"field", "x0", "x1", "center"} — a horizontal zone owned by that field."""
    best = (None, [])
    for line in lines[:max_header_lines]:
        bands = []
        claimed = set()
        for cell in _cluster_header_cells(line["words"]):
            phrase = " ".join(w["text"] for w in cell)
            field = _field_for_header(phrase, synonyms)
            if not field or field in claimed:
                continue
            x0 = cell[0]["x0"]
            x1 = cell[-1]["x1"]
            bands.append({
                "field": field,
                "x0": x0,
                "x1": x1,
                "center": (x0 + x1) / 2,
            })
            claimed.add(field)
        if len(bands) >= minimum_fields:
            return line, sorted(bands, key=lambda b: b["center"])
        if len(bands) > len(best[1]):
            best = (line, sorted(bands, key=lambda b: b["center"]))
    if best[0] is not None and len(best[1]) >= minimum_fields:
        return best
    return None, []


def _assign_words_to_bands(words, bands):
    """Assign each word in a data line to a column by splitting the page
    width at the midpoints between adjacent header bands' edges (not their
    centers), then join same-band words in reading order. Edge-based
    boundaries track a narrow header sitting inside a wide data column
    (e.g. "Use" over data that runs wider than the header text) better than
    pure center-distance would; column jitter in OCR bounding boxes is still
    tolerated since boundaries are derived once per header, not per word."""
    if not bands or not words:
        return {}
    ordered = sorted(bands, key=lambda band: band["center"])
    boundaries = [
        (ordered[i]["x1"] + ordered[i + 1]["x0"]) / 2
        for i in range(len(ordered) - 1)
    ]
    cells = {band["field"]: [] for band in ordered}
    for word in words:
        word_center = (word["x0"] + word["x1"]) / 2
        index = 0
        while index < len(boundaries) and word_center >= boundaries[index]:
            index += 1
        cells[ordered[index]["field"]].append(word)
    result = {}
    for field, field_words in cells.items():
        if not field_words:
            continue
        field_words.sort(key=lambda w: w["x0"])
        result[field] = " ".join(w["text"] for w in field_words)
    return result


def _ocr_rent_roll_rows(lines, path, page_number, as_of_date, extra_provenance=None):
    header_line, bands = _ocr_header_bands(lines, RENT_ROLL_SYNONYMS, 3)
    if header_line is None:
        return []
    header_index = lines.index(header_line)
    records = []
    for row_number, line in enumerate(lines[header_index + 1:], start=1):
        cells = _assign_words_to_bands(line["words"], bands)
        data = {}
        confidence = {}
        for field, raw_value in cells.items():
            value = _coerce_rent(field, raw_value)
            if value is not None:
                data[field] = value
                confidence[field] = "low"
        data, confidence = _prepare_rent_data(data, confidence)
        confidence = {key: "low" for key in confidence}
        anchor = data.get("tenant_name") or data.get("unit_id") or data.get("suite")
        if not anchor:
            continue
        label = _norm(anchor)
        if label.startswith(("total", "subtotal", "average", "grand total")):
            continue
        if as_of_date:
            data["as_of_date"] = as_of_date
            confidence["as_of_date"] = "low"
        source_locator = f"pdf:page:{page_number}:ocr_table:row:{row_number}"
        provenance = {
            "source_locator": source_locator,
            "extraction_method": "ocr_pdf_table_extractor",
        }
        if extra_provenance:
            provenance.update(extra_provenance)
        records.append({
            "data": data,
            "confidence": confidence,
            "source": str(path),
            "source_locator": source_locator,
            "provenance": provenance,
        })
    return records


def _extract_via_ocr(path):
    """OCR lane entry point: rasterize -> orient -> OCR -> reuse the native
    table/expense matchers on the OCR'd words. Returns the same
    {"rent_roll_entries", "expense_records", "warnings"} shape as
    extract_financial_pdf. Never raises; degrades to a warning instead."""
    result = {"rent_roll_entries": [], "expense_records": [], "warnings": []}
    if not _ocr_available():
        result["warnings"].append(
            f"  [{path.name}] PDF has no extractable text or tables; OCR is "
            "required but Tesseract is not installed on this machine. "
            "See docs/OCR_LANE_DESIGN.md."
        )
        return result

    try:
        raw_pages = _rasterize_pdf(path)
    except Exception as exc:
        result["warnings"].append(f"Could not rasterize {path.name} for OCR: {exc}")
        return result
    if not raw_pages:
        result["warnings"].append(
            f"  [{path.name}] PDF produced no renderable pages for OCR."
        )
        return result

    try:
        from comparable_contract import source_metadata
        source_sha256 = source_metadata(path)["source_sha256"]
    except Exception:
        source_sha256 = None

    page_lines = []
    provenance_by_page = {}
    all_text_parts = []
    for page_number, image in raw_pages:
        oriented, degrees = _correct_orientation(image)
        try:
            words, avg_confidence = _ocr_words(oriented)
        except Exception as exc:
            result["warnings"].append(
                f"  [{path.name}] page {page_number}: OCR failed ({exc})."
            )
            continue
        if not words or avg_confidence < OCR_MIN_AVG_CONFIDENCE:
            result["warnings"].append(
                f"  [{path.name}] page {page_number}: OCR confidence too low "
                f"({avg_confidence:.0f}/100) to extract reliably; needs a "
                "cleaner scan or manual entry."
            )
            continue
        lines = _group_words_by_line(words)
        page_lines.append((page_number, lines))
        all_text_parts.append(" ".join(word["text"] for word in words))
        page_provenance = {
            "ocr_engine": "tesseract",
            "ocr_avg_word_confidence": round(avg_confidence, 1),
            "rotation_degrees_applied": degrees,
        }
        rendered_page_image = _save_review_image(oriented, source_sha256, page_number)
        if rendered_page_image:
            page_provenance["rendered_page_image"] = rendered_page_image
        provenance_by_page[page_number] = page_provenance

    if not page_lines:
        return result

    all_text = "\n".join(all_text_parts)
    as_of_date = _as_of_date_from_text(all_text, path.name)
    period_year = _period_year_from_text(all_text, path.name)
    period_type, period_confidence = _period_type_from_text(all_text)

    for page_number, lines in page_lines:
        result["rent_roll_entries"].extend(
            _ocr_rent_roll_rows(
                lines,
                path,
                page_number,
                as_of_date,
                provenance_by_page.get(page_number),
            )
        )

    result["expense_records"].extend(
        _expense_rows_from_pages(
            page_lines,
            path,
            period_year,
            period_type,
            period_confidence,
            "ocr_pdf_text_position_extractor",
            provenance_by_page,
        )
    )

    if not result["rent_roll_entries"] and not result["expense_records"]:
        result["warnings"].append(
            f"  [{path.name}] OCR completed but found no recognizable "
            "rent-roll table or expense section; review the source scan "
            "manually."
        )
    return result


def extract_financial_pdf(path):
    """Extract financial records from a PDF.

    PDFs with a native text layer are parsed directly (table extraction for
    rent rolls, text-position parsing for expense statements). Scanned/
    image-only PDFs fall through to the OCR lane (`_extract_via_ocr`), which
    reuses the same matching logic against Tesseract-derived words and tags
    every field confidence "low". See docs/OCR_LANE_DESIGN.md.
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
        result["rent_roll_entries"], _RENT_ROLL_DEDUPE_FIELDS
    )
    result["expense_records"] = _dedupe_records(
        result["expense_records"], _EXPENSE_DEDUPE_FIELDS
    )
    if not result["rent_roll_entries"] and not result["expense_records"]:
        if has_extractable_text:
            result["warnings"].append(
                f"  [{path.name}] No native PDF financial table/text found."
            )
        else:
            ocr_result = _extract_via_ocr(path)
            result["rent_roll_entries"] = _dedupe_records(
                ocr_result["rent_roll_entries"], _RENT_ROLL_DEDUPE_FIELDS
            )
            result["expense_records"] = _dedupe_records(
                ocr_result["expense_records"], _EXPENSE_DEDUPE_FIELDS
            )
            result["warnings"].extend(ocr_result["warnings"])
    return result
