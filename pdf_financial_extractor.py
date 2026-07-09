"""Native-PDF and scanned-PDF financial table extraction for historical
source documents.

Scanned/image-only PDFs are handled by the OCR lane (see docs/OCR_LANE_DESIGN.md):
pages are rasterized with PyMuPDF, oriented, and OCRed with Tesseract, then run
through the *same* header/column and expense-section matching logic used for
native-text PDFs. Every OCR-derived field is tagged confidence "low" regardless
of the OCR engine's own score, and never auto-commits — it flows through the
existing stage -> review -> commit gate like every other harvest record.
"""

import json
import os
import re
from pathlib import Path

import pdfplumber

from harvest_contract import enforce_ocr_low_confidence
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
OCR_MAX_PAGES = 6
OCR_MAX_RENDER_EDGE_PX = 3600
OCR_PAGES_DIR = Path(__file__).parent / "ingest" / "staged" / "ocr_pages"


def _ocr_pages_dir():
    """Directory OCR page-review images are written to. Defaults to
    OCR_PAGES_DIR, but honors AXIOM_OCR_PAGES_DIR (consistent with the
    AXIOM_TESSERACT_CMD/AXIOM_TESSDATA_DIR override pattern) so tests and
    alternate staging locations are not forced to litter the real
    checkout's ingest/staged/ocr_pages/ folder."""
    override = os.environ.get("AXIOM_OCR_PAGES_DIR")
    return Path(override) if override else OCR_PAGES_DIR

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
_tesseract_configured = False


def _candidate_tesseract_commands():
    env_cmd = os.environ.get("AXIOM_TESSERACT_CMD")
    if env_cmd:
        yield Path(env_cmd)

    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
    except Exception:
        config = {}
    ocr_config = config.get("ocr", {}) if isinstance(config, dict) else {}
    for key in ("tesseract_cmd", "tesseract_path"):
        configured = ocr_config.get(key)
        if configured:
            yield Path(configured)

    yield Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    yield Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")


def _candidate_tessdata_dirs(config):
    env_dir = os.environ.get("AXIOM_TESSDATA_DIR")
    if env_dir:
        yield Path(env_dir)

    ocr_config = config.get("ocr", {}) if isinstance(config, dict) else {}
    configured = ocr_config.get("tessdata_dir")
    if configured:
        yield Path(configured)

    root = Path(__file__).parent
    yield root / ".local" / "tessdata"
    yield Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    yield Path(r"C:\Program Files (x86)\Tesseract-OCR\tessdata")


def _configure_tesseract_command():
    global _tesseract_configured
    if _tesseract_configured or not _TESSERACT_IMPORT_OK:
        return
    _tesseract_configured = True
    config = {}
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
    except Exception:
        pass

    for candidate in _candidate_tesseract_commands():
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            break
    for candidate in _candidate_tessdata_dirs(config):
        if (candidate / "eng.traineddata").is_file():
            os.environ["TESSDATA_PREFIX"] = str(candidate)
            break


def _ocr_available():
    """Whether OCR can actually run: both libraries import and the Tesseract
    binary is installed and reachable. Cached after the first check."""
    global _tesseract_binary_ok
    if not (_FITZ_OK and _TESSERACT_IMPORT_OK):
        return False
    _configure_tesseract_command()
    if _tesseract_binary_ok is None:
        try:
            pytesseract.get_tesseract_version()
            _tesseract_binary_ok = True
        except Exception:
            _tesseract_binary_ok = False
    return _tesseract_binary_ok


def _ocr_max_pages():
    try:
        return max(1, int(os.environ.get("AXIOM_OCR_MAX_PAGES", OCR_MAX_PAGES)))
    except ValueError:
        return OCR_MAX_PAGES


def _ocr_max_render_edge_px():
    try:
        return max(
            1200,
            int(os.environ.get(
                "AXIOM_OCR_MAX_RENDER_EDGE_PX",
                OCR_MAX_RENDER_EDGE_PX,
            )),
        )
    except ValueError:
        return OCR_MAX_RENDER_EDGE_PX


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


def _finalize_rent_roll_row(
    data,
    confidence,
    path,
    source_locator,
    extraction_method,
    as_of_date,
    as_of_confidence="medium",
    extra_provenance=None,
):
    """Shared post-cell-extraction logic for both native table rows
    (`_extract_table_rows`) and OCR band-assigned rows (`_ocr_rent_roll_rows`)
    -- the two extractors get to the raw field/value cells very differently
    (structured table-cell indices vs. word-position band assignment), but
    everything downstream of "here are the raw fields for one row" was
    duplicated: deriving/normalizing fields, detecting total/subtotal rows,
    attaching as_of_date, applying the OCR confidence policy, and building
    the staged record dict. Centralizing it here means a fix (like the
    confidence-policy centralization above) only has to be made once.

    Returns (kind, payload):
      kind == "empty" -> no usable anchor field; caller should skip the row
      kind == "total" -> payload is the row's raw data dict, for callers
                         that reconcile summed rows against a Total row
      kind == "row"   -> payload is the finished staged record dict
    """
    data, confidence = _prepare_rent_data(data, confidence)
    anchor = data.get("tenant_name") or data.get("unit_id") or data.get("suite")
    if not anchor:
        return "empty", None
    label = _norm(anchor)
    if label.startswith(("total", "subtotal", "average", "grand total")):
        return "total", data
    if as_of_date:
        data["as_of_date"] = as_of_date
        confidence["as_of_date"] = as_of_confidence
    confidence = enforce_ocr_low_confidence(confidence, extraction_method)
    provenance = {
        "source_locator": source_locator,
        "extraction_method": extraction_method,
    }
    if extra_provenance:
        provenance.update(extra_provenance)
    return "row", {
        "data": data,
        "confidence": confidence,
        "source": str(path),
        "source_locator": source_locator,
        "provenance": provenance,
    }


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
        source_locator = f"pdf:page:{page_number}:table:{table_number}:row:{row_index}"
        kind, payload = _finalize_rent_roll_row(
            data,
            confidence,
            path,
            source_locator,
            "native_pdf_table_extractor",
            as_of_date,
            as_of_confidence="medium",
        )
        if kind == "row":
            records.append(payload)
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


def _statement_expense_fallback_allowed(text, path):
    label = _norm(" ".join([text or "", Path(path).stem]))
    return any(marker in label for marker in (
        "profit and loss",
        "p&l",
        "income statement",
        "operating statement",
    ))


def _statement_expense_state(text, current):
    label = re.sub(r"[^a-z0-9&]+", " ", _norm(text)).strip()
    if not label:
        return current
    if any(marker in label for marker in (
        "net income",
        "net operating income",
        "net ordinary income",
        "net profit",
        "cash flow",
    )):
        return "done"
    if label.startswith(("total expense", "total expenses")):
        return "done"
    if any(marker in label for marker in (
        "gross profit",
        "total income",
        "total revenue",
        "total receipts",
    )):
        return "expense_candidate"
    if any(marker in label for marker in ("revenue", "income", "sales")):
        return "income"
    return current


def _income_like_statement_category(category):
    label = re.sub(r"[^a-z0-9&]+", " ", _norm(category)).strip()
    return any(marker in label for marker in (
        "income",
        "revenue",
        "sales",
        "gross profit",
        "receipts",
    ))


def _statement_expense_rows_from_pages(
    page_lines,
    path,
    period_year,
    period_type,
    period_confidence,
    extraction_method,
    statement_text,
    provenance_by_page=None,
):
    if not _statement_expense_fallback_allowed(statement_text, path):
        return []
    records = []
    section = None
    for page_number, lines in page_lines:
        for line_number, line in enumerate(lines, start=1):
            line_words = line["words"]
            text = " ".join(word["text"] for word in line_words)
            section = _statement_expense_state(text, section)
            if section != "expense_candidate":
                continue
            amount_index, amount = _amount_from_line(line_words)
            if amount_index is None:
                continue
            category = " ".join(word["text"] for word in line_words[:amount_index])
            category = re.sub(r"^\W+", "", category).strip()
            if (
                not _valid_expense_category(category)
                or _income_like_statement_category(category)
            ):
                continue
            data = {
                "category": category,
                "amount": amount,
                "period_type": period_type,
            }
            # Built as if this were native text-position extraction; OCR's
            # blanket "everything is low confidence" policy is applied once,
            # centrally, below rather than re-derived per field here.
            confidence = {
                "category": "low",
                "amount": "medium",
                "period_type": period_confidence or "low",
            }
            if period_year is not None:
                data["period_year"] = period_year
                confidence["period_year"] = "medium"
            confidence = enforce_ocr_low_confidence(confidence, extraction_method)
            source_locator = f"pdf:page:{page_number}:line:{line_number}"
            provenance = {
                "source_locator": source_locator,
                "extraction_method": extraction_method,
                "layout": "statement_expense_fallback",
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
    return records if len(records) >= 2 else []


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
            confidence = enforce_ocr_low_confidence(confidence, extraction_method)
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
    records = _expense_rows_from_pages(
        page_lines,
        path,
        period_year,
        period_type,
        period_confidence,
        "native_pdf_text_position_extractor",
    )
    if records:
        return records
    return _statement_expense_rows_from_pages(
        page_lines,
        path,
        period_year,
        period_type,
        period_confidence,
        "native_pdf_statement_fallback",
        all_text,
    )


# ─── OCR lane: rasterization, orientation, word extraction ──────────────────


def _rasterize_pdf(path):
    """Render every page of a PDF to a PIL image at OCR_DPI.
    Returns a list of (page_number, PIL.Image)."""
    pages = []
    base_zoom = OCR_DPI / 72.0
    max_edge = _ocr_max_render_edge_px()
    max_pages = _ocr_max_pages()
    with fitz.open(str(path)) as doc:
        for index, page in enumerate(doc, start=1):
            if index > max_pages:
                break
            zoom = min(
                base_zoom,
                max_edge / max(page.rect.width, page.rect.height),
            )
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages.append((index, image))
    return pages


def _pdf_page_count(path):
    try:
        with fitz.open(str(path)) as doc:
            return len(doc)
    except Exception:
        return None


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
        pages_dir = _ocr_pages_dir()
        pages_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{(source_sha256 or 'unknown')[:16]}_p{page_number}.png"
        dest = pages_dir / filename
        if not dest.exists():
            image.save(dest, format="PNG")
        try:
            return str(dest.relative_to(Path(__file__).parent))
        except ValueError:
            # dest is outside the platform root (e.g. AXIOM_OCR_PAGES_DIR
            # points at a test tempdir) -- an absolute path is still a
            # usable provenance pointer, just not a repo-relative one.
            return str(dest)
    except Exception:
        return None


def prune_ocr_pages(staged_dir=None, confirmed_dir=None, pages_dir=None):
    """Delete OCR page-review images that are no longer referenced by any
    *active* staged/confirmed batch (a ``.json`` file still awaiting review
    or commit). Rendered page PNGs are content-addressed by source SHA-256
    (see `_save_review_image`) and reused across runs on the same source, so
    they accumulate indefinitely under ``ingest/staged/ocr_pages/`` with no
    existing cleanup -- this is meant to be run periodically (e.g. after a
    `comp-commit`) rather than automatically, so a page image is never
    deleted while a human might still want to cross-check it.

    Returns the number of image files deleted.
    """
    pages_dir = Path(pages_dir) if pages_dir else _ocr_pages_dir()
    if not pages_dir.is_dir():
        return 0
    base = Path(__file__).parent
    staged_dir = Path(staged_dir) if staged_dir else base / "ingest" / "staged"
    confirmed_dir = (
        Path(confirmed_dir) if confirmed_dir else base / "ingest" / "confirmed"
    )

    referenced = set()
    for active_dir in (staged_dir, confirmed_dir):
        if not active_dir.is_dir():
            continue
        for batch_path in active_dir.glob("*.json"):
            try:
                with open(batch_path, encoding="utf-8") as handle:
                    batch = json.load(handle)
            except Exception:
                continue
            for key in ("rent_roll_entries", "expense_records"):
                for record in batch.get(key, []):
                    image = record.get("provenance", {}).get("rendered_page_image")
                    if image:
                        referenced.add(Path(image).name)

    deleted = 0
    for image_path in pages_dir.glob("*.png"):
        if image_path.name not in referenced:
            try:
                image_path.unlink()
                deleted += 1
            except OSError:
                continue
    return deleted


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


# Relative tolerance for cross-checking OCR'd rent-roll numbers against each
# other (e.g. annual rent vs. monthly rent x 12). OCR digit errors on an
# otherwise well-formed row (each field individually looks plausible) are the
# hardest kind of mistake for a human reviewer to catch by eye -- these
# checks catch them arithmetically instead of relying on confidence="low"
# plus a rendered page image alone.
_ARITHMETIC_TOLERANCE = 0.02
_TOTAL_ROW_TOLERANCE = 0.03


def _within_tolerance(actual, expected, tolerance=_ARITHMETIC_TOLERANCE):
    if not expected:
        return actual == expected
    return abs(actual - expected) / abs(expected) <= tolerance


def _rent_roll_arithmetic_warning(data, filename, page_number, row_number):
    """Flag a row whose OCR'd numbers don't reconcile with each other, even
    though every individual field looked plausible on its own -- usually a
    sign of a single misread digit."""
    monthly_rent = data.get("monthly_rent")
    annual_rent = data.get("annual_rent")
    sf_leased = data.get("sf_leased")
    rent_psf = data.get("rent_psf")
    issues = []
    if monthly_rent and annual_rent:
        expected_annual = monthly_rent * 12
        if not _within_tolerance(annual_rent, expected_annual):
            issues.append(
                f"annual rent {annual_rent:,.2f} does not reconcile with "
                f"monthly rent {monthly_rent:,.2f} (expected ~"
                f"{expected_annual:,.2f})"
            )
    if annual_rent and sf_leased and rent_psf:
        expected_psf = annual_rent / sf_leased
        if not _within_tolerance(rent_psf, expected_psf):
            issues.append(
                f"rent/SF {rent_psf:,.2f} does not reconcile with annual "
                f"rent divided by leased SF (expected ~{expected_psf:,.2f})"
            )
    if not issues:
        return None
    return (
        f"  [{filename}] page {page_number} row {row_number}: "
        + "; ".join(issues)
        + " -- likely an OCR digit error; verify against the source scan."
    )


def _rent_roll_total_reconciliation_warning(records, total_row_data, filename, page_number):
    """Compare summed data-row values against the page's own discarded
    Total row (if OCR found one). A mismatch usually means a row was
    misread badly enough to be dropped, or a value on a kept row was
    misread -- either way, a silent shortfall a checksum can catch even
    though every kept row individually passed review."""
    if not total_row_data:
        return None
    issues = []
    for field, label in (
        ("monthly_rent", "monthly rent"),
        ("annual_rent", "annual rent"),
        ("sf_leased", "leased SF"),
    ):
        total_value = total_row_data.get(field)
        if total_value is None:
            continue
        summed = sum(record["data"].get(field) or 0 for record in records)
        if not _within_tolerance(summed, total_value, tolerance=_TOTAL_ROW_TOLERANCE):
            issues.append(
                f"{label} column sums to {summed:,.2f} but the page's Total "
                f"row reports {total_value:,.2f}"
            )
    if not issues:
        return None
    return (
        f"  [{filename}] page {page_number}: " + "; ".join(issues)
        + " -- a row may be missing or misread; verify against the source scan."
    )


def _ocr_rent_roll_rows(lines, path, page_number, as_of_date, extra_provenance=None):
    """Returns (records, header_found, warnings). `header_found` lets the
    caller warn when a page has no recognizable rent-roll header at all
    (e.g. a continuation page of a multi-page rent roll that doesn't repeat
    the header row) instead of silently yielding zero rows for that page."""
    header_line, bands = _ocr_header_bands(lines, RENT_ROLL_SYNONYMS, 3)
    if header_line is None:
        return [], False, []
    header_index = lines.index(header_line)
    records = []
    warnings = []
    total_row_data = None
    for row_number, line in enumerate(lines[header_index + 1:], start=1):
        cells = _assign_words_to_bands(line["words"], bands)
        data = {}
        confidence = {}
        for field, raw_value in cells.items():
            value = _coerce_rent(field, raw_value)
            if value is not None:
                data[field] = value
                confidence[field] = "low"
        source_locator = f"pdf:page:{page_number}:ocr_table:row:{row_number}"
        kind, payload = _finalize_rent_roll_row(
            data,
            confidence,
            path,
            source_locator,
            "ocr_pdf_table_extractor",
            as_of_date,
            as_of_confidence="low",
            extra_provenance=extra_provenance,
        )
        if kind == "empty":
            continue
        if kind == "total":
            total_row_data = payload
            continue
        record = payload
        row_warning = _rent_roll_arithmetic_warning(
            record["data"], path.name, page_number, row_number
        )
        if row_warning:
            warnings.append(row_warning)
        records.append(record)
    total_warning = _rent_roll_total_reconciliation_warning(
        records, total_row_data, path.name, page_number
    )
    if total_warning:
        warnings.append(total_warning)
    return records, True, warnings


def _financial_structure_signals(lines, path, page_number):
    """Shared per-page probe for recognizable financial structure -- used
    both to score OCR orientation candidates (`_choose_financial_ocr_orientation`)
    and, on later pages that already have a detected orientation, to decide
    whether that orientation needs to be re-evaluated even when OCR
    confidence looks fine (`_extract_via_ocr`): a rotated page can still read
    as high-confidence text with no usable rent-roll or expense structure at
    all. Returns (expense_records, rent_records, header_found)."""
    text = " ".join(word["text"] for line in lines for word in line["words"])
    period_year = _period_year_from_text(text, path.name)
    period_type, period_confidence = _period_type_from_text(text)
    expense_records = _expense_rows_from_pages(
        [(page_number, lines)],
        path,
        period_year,
        period_type,
        period_confidence,
        "ocr_orientation_probe",
        {page_number: {}},
    )
    if not expense_records:
        expense_records = _statement_expense_rows_from_pages(
            [(page_number, lines)],
            path,
            period_year,
            period_type,
            period_confidence,
            "ocr_orientation_probe",
            text,
            {page_number: {}},
        )
    rent_records, header_found, _warnings = _ocr_rent_roll_rows(
        lines, path, page_number, None, {}
    )
    return expense_records, rent_records, header_found


def _page_has_financial_structure(lines, path, page_number):
    """True if this page's current OCR words yield any recognizable
    rent-roll header/rows or expense-candidate lines at all."""
    expense_records, rent_records, header_found = _financial_structure_signals(
        lines, path, page_number
    )
    return bool(expense_records) or bool(rent_records) or header_found


def _choose_financial_ocr_orientation(image, path, page_number):
    """Choose the OCR orientation that produces the most usable financial
    structure, not merely the highest word count. Tesseract OSD can rotate
    landscape statements into column-like text with high confidence but no
    extractable rows."""
    best = None
    for degrees in (0, 90, 180, 270):
        candidate = image if degrees == 0 else image.rotate(-degrees, expand=True)
        try:
            words, avg_confidence = _ocr_words(candidate)
        except Exception:
            continue
        lines = _group_words_by_line(words)
        expense_records, rent_records, header_found = _financial_structure_signals(
            lines, path, page_number
        )
        word_counts = [len(line["words"]) for line in lines]
        dense_lines = sum(1 for count in word_counts if count >= 4)
        amount_lines = sum(
            1
            for line in lines
            if any(_money_candidate(word["text"]) is not None for word in line["words"])
        )
        structure_score = (
            (len(expense_records) + len(rent_records)) * 1000
            + (200 if header_found else 0)
            + dense_lines * 5
            + amount_lines * 3
        )
        score = structure_score + avg_confidence + min(len(words), 100) / 10
        if best is None or score > best["score"]:
            best = {
                "image": candidate,
                "degrees": degrees,
                "words": words,
                "avg_confidence": avg_confidence,
                "score": score,
            }
    if best:
        return (
            best["image"],
            best["degrees"],
            best["words"],
            best["avg_confidence"],
        )
    oriented, degrees = _correct_orientation(image)
    words, avg_confidence = _ocr_words(oriented)
    return oriented, degrees, words, avg_confidence


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

    total_pages = _pdf_page_count(path)
    max_pages = _ocr_max_pages()
    if total_pages and total_pages > max_pages:
        result["warnings"].append(
            f"  [{path.name}] OCR limited to first {max_pages} of "
            f"{total_pages} pages for batch performance; review later pages "
            "manually if the statement continues."
        )

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
    preferred_degrees = None
    for page_number, image in raw_pages:
        try:
            if preferred_degrees is None:
                oriented, degrees, words, avg_confidence = (
                    _choose_financial_ocr_orientation(image, path, page_number)
                )
                preferred_degrees = degrees
            else:
                degrees = preferred_degrees
                oriented = image if degrees == 0 else image.rotate(-degrees, expand=True)
                words, avg_confidence = _ocr_words(oriented)
                needs_redetect = not words or avg_confidence < OCR_MIN_AVG_CONFIDENCE
                if not needs_redetect:
                    # Confidence alone isn't enough: a page rotated relative
                    # to the one that set preferred_degrees (a mixed-
                    # orientation scan bundle, e.g. a portrait cover page
                    # followed by a landscape rent roll) can still read as
                    # high-confidence text with no usable rent-roll/expense
                    # structure at all. Re-run full orientation detection in
                    # that case too, not just on low confidence.
                    needs_redetect = not _page_has_financial_structure(
                        _group_words_by_line(words), path, page_number
                    )
                if needs_redetect:
                    oriented, degrees, words, avg_confidence = (
                        _choose_financial_ocr_orientation(
                            image, path, page_number
                        )
                    )
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
        page_records, header_found, row_warnings = _ocr_rent_roll_rows(
            lines,
            path,
            page_number,
            as_of_date,
            provenance_by_page.get(page_number),
        )
        result["rent_roll_entries"].extend(page_records)
        result["warnings"].extend(row_warnings)
        if not header_found:
            result["warnings"].append(
                f"  [{path.name}] page {page_number}: no rent-roll header "
                "recognized on this page; its rows (if any) were not "
                "extracted. If this is a continuation page of a multi-page "
                "rent roll that doesn't repeat the header, review the "
                "source scan manually."
            )

    expense_records = _expense_rows_from_pages(
        page_lines,
        path,
        period_year,
        period_type,
        period_confidence,
        "ocr_pdf_text_position_extractor",
        provenance_by_page,
    )
    if not expense_records:
        expense_records = _statement_expense_rows_from_pages(
            page_lines,
            path,
            period_year,
            period_type,
            period_confidence,
            "ocr_pdf_statement_fallback",
            all_text,
            provenance_by_page,
        )
    result["expense_records"].extend(expense_records)

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
