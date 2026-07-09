# OCR Lane Design (Implemented v1)

Derek approved all three open questions below as originally proposed:
Tesseract may be installed locally, v1 scope is rent roll + operating
expenses only (no scanned narrative reports), and low-quality scans bail out
with a warning rather than staging speculative rows.

## Scope

Today, `pdf_financial_extractor.py` handles native-text PDFs: table-structured
rent rolls (`_extract_table_rows`) and text-position operating-expense
statements (`_extract_text_expense_rows`). When a PDF has no extractable text
layer, `extract_financial_pdf` returns early with:

  "PDF has no extractable text or tables; OCR is required."

This document describes the OCR lane that resolves that warning for scanned or
photographed rent rolls and operating statements. It reuses the existing
extract → stage → review → commit pipeline (`ingest.py`, `db.py`,
`harvest_contract.py`) rather than introducing a parallel one. No schema
change is required to store OCR-derived records; only new provenance keys and
one new confidence caveat.

Out of scope for v1: scanned narrative appraisal reports (assignments,
observations, artifacts). Those already have low-friction native-text
extraction; if scanned narrative reports become common, they can reuse the
same rasterization/OCR primitives built here.

## Why this is review-first by construction, not just by policy

`insert_rent_roll_entry` / `insert_operating_expense` are only ever called
from `commit_confirmed`, which only processes files that `review_staged`
already moved into `ingest/confirmed/` after a human confirmed each record in
the terminal (or Streamlit). OCR output plugs into the same staged-JSON shape
(`data` / `confidence` / `source` / `source_locator` / `provenance`) already
used by the native extractors, so the mandatory human gate before database
commit is inherited for free — it is not something the OCR lane has to
reimplement.

What OCR *does* need beyond that existing gate, because its error mode is
different from narrative-regex "low confidence" (misread characters and
misaligned columns, not just under-specified text):

- every OCR-derived field is tagged `confidence: "low"` (no OCR field is ever
  tagged `medium` or `high`, regardless of the engine's own score);
- the rasterized source page image is saved next to the staged record so
  Derek can visually check the number against the actual scan without
  reopening the original PDF and hunting for the page;
- the review CLI/Streamlit view flags OCR-sourced records distinctly (e.g. a
  visible "OCR — verify against page image" marker) instead of blending them
  into ordinary low-confidence rows.

## Dependencies

- **Rasterization: PyMuPDF (`fitz`).** Pure pip wheel, no separate system
  binary. Avoids adding a Poppler/`pdftoppm` dependency on top of Tesseract.
- **OCR: `pytesseract`** (pip, thin wrapper) **+ the Tesseract OCR engine**
  (system binary — this is the one new *operational* dependency, not just a
  pip install). On Windows this means installing the UB-Mannheim Tesseract
  build once. The extractor auto-detects `AXIOM_TESSERACT_CMD`, optional
  `config.json` OCR paths, and the normal Windows install locations. English
  traineddata can come from `AXIOM_TESSDATA_DIR`, optional `config.json`, the
  normal Tesseract `tessdata` folder, or ignored local `.local/tessdata`.
- If Tesseract isn't found at runtime, fail soft: emit the same kind of
  warning already used for missing extraction ("OCR engine not installed;
  install Tesseract to enable scanned-PDF extraction") rather than crashing
  the whole `comp-ingest` run.

This was the one item that needed Derek's sign-off before writing code: it's
the first Axiom dependency that isn't a pure Python package (see "Open
questions" resolution below). Everything else assumes local/offline
Tesseract, consistent with keeping financial document processing off
third-party services.

## Pipeline

1. **Detect.** Reuse the existing `has_extractable_text` check in
   `extract_financial_pdf`. When false, hand the PDF to the OCR lane instead
   of returning immediately.
2. **Rasterize.** Render pages via PyMuPDF at ~300 DPI to Pillow images, with
   two batch-safety caps: OCR defaults to the first 6 pages
   (`AXIOM_OCR_MAX_PAGES` can override), and very large embedded scans are
   downscaled to a maximum render edge before Tesseract sees them
   (`AXIOM_OCR_MAX_RENDER_EDGE_PX` can override). When a PDF is page-limited,
   the staged batch gets a warning telling Derek to review later pages
   manually if the statement continues.
3. **Orientation.** Evaluate 0/90/180/270 renderings on the first usable page
   and prefer the rotation that yields recognizable financial rows, then OCR
   confidence as a fallback. Later pages reuse that detected rotation and only
   fall back to full orientation scoring if confidence collapses. This avoids a
   real-world failure where Tesseract OSD rotated a landscape proforma into
   high-confidence but column-like text with no extractable expense rows, while
   keeping multi-page scanned statements fast enough for batch ingest. Record
   `rotation_degrees_applied` in provenance.
4. **OCR.** Run `pytesseract.image_to_data(..., output_type=Output.DICT)` per
   page to get word text, bounding box, and a 0–100 confidence score per word
   — the same shape of information `pdfplumber.extract_words()` already gives
   the native text-position extractor.
5. **Reuse existing table/line logic.** Generalize `_group_words_by_line` (in
   `pdf_financial_extractor.py`) to accept either pdfplumber words or
   Tesseract words (both reduce to `{text, top, x0}`), then run the *same*
   `RENT_ROLL_SYNONYMS` header matching and expense-section state machine
   already built for native PDFs against the OCR'd words. If a P&L/income
   statement has no explicit expense heading, a conservative statement
   fallback can stage expense-looking lines after income/gross-profit
   boundaries, provided it finds at least two candidate rows.
6. **Tag and stage.** Every produced field gets `confidence: "low"`. Provenance
   gains: `extraction_method: "ocr_pdf_table_extractor"` (rent roll),
   `"ocr_pdf_text_position_extractor"` (expense lines matched by the shared
   section-state logic), or `"ocr_pdf_statement_fallback"` (the no-heading
   statement fallback), plus `ocr_engine: "tesseract"`,
   `ocr_avg_word_confidence`, `rotation_degrees_applied`, and
   `rendered_page_image` (relative path to the saved page PNG under
   `ingest/staged/ocr_pages/`).
7. **Bail out on garbage.** If a page produces near-zero words or average word
   confidence falls below a threshold (proposed: 40/100), don't stage
   speculative rows — emit a warning naming the page and asking for a cleaner
   scan, mirroring today's "OCR is required" message.

## Review UI changes (as built)

- Streamlit's comp-review view already has a per-record Keep checkbox for
  every rent-roll/expense row (native or OCR). OCR-sourced rows now also get
  a distinct warning banner ("OCR-derived — verify against the source scan")
  with the OCR confidence score and the actual rendered page image displayed
  inline via `st.image`, so Derek can eyeball the scan next to the extracted
  value before deciding whether to keep it.
- The terminal `review_staged` path doesn't have per-record keep/skip for
  rent-roll/expense rows at all (native or OCR) — that's a pre-existing gap,
  not something new introduced here. What it does get: an `[OCR NN/100 see
  <path>]` marker printed next to every OCR-sourced row in the summary, so
  Derek at least sees which rows need extra scrutiny before the batch-level
  confirm. Adding real per-record terminal gating for rent-roll/expense rows
  (matching what comps/leases already have) is future work, not scoped here.

## Testing plan

Mirror the existing deterministic-fixture approach (`tests/test_financial_harvest.py`
already builds synthetic native PDFs with ReportLab):

- render a known synthetic rent roll / expense statement to an image and
  re-embed it as an image-only PDF (no text layer) → verify extraction matches
  the native-PDF fixture's expected values, with `confidence == "low"` and
  correct `extraction_method`.
- a rotated variant (90°/180°) → verify orientation correction recovers the
  same values.
- a deliberately illegible/garbage variant → verify the bail-out warning path
  fires and nothing is staged.

## Open questions — resolved

All three were approved as originally proposed (see the note at the top of
this document): local Tesseract install is approved, v1 scope stays limited
to scanned rent rolls and operating statements (not scanned narrative
reports), and the 40/100 average-word-confidence bail-out threshold stands
as-is.
