# Current Handoff

- Last updated: 2026-07-08
- Current agent: Claude
- Last commit before this session's changes: `f13ff45` "Add native text PDF
  expense harvesting" (Codex). This session's OCR-lane work is implemented but
  **not yet committed** — see "Do not touch" below.

## Current objective

Close the OCR lane Codex named as the exact next step (scanned/image-only
rent-roll and P&L extraction), then maintain a safe Claude ↔ Codex handoff
baseline before connecting external services.

## Completed

- Confirmed the canonical copied project is accessible in the shared folder.
- Inventoried the code, templates, assignments, integrations, and current
  documentation.
- Compared `PROJECT_STATE.md` claims with the implemented command paths.
- Ran non-mutating CLI and delivery-readiness checks.
- Scanned existing generated reports for unresolved placeholders.
- Confirmed the apparent client data was dummy data, then replaced it with a
  conspicuously fictional fixture identity.
- Expanded `.gitignore` to protect client data, secrets, databases, ingest
  staging, generated files, and caches.
- Added shared `AGENTS.md`, agent-neutral `PROJECT_STATE.md`, and this handoff.
- Initialized a dedicated Git repository at the platform root.
- Added non-mutating `axiom.py validate <file_no>`.
- Added validation of ordinary fields, block handlers, formula caches, and
  possible JSON/workbook staleness.
- Updated dashboard readiness to include unresolved document blocks.
- Gated final `deliver` on validation success.
- Added explicit `deliver <file_no> --draft`; draft output receives a `DRAFT_`
  filename and does not alter delivery stage.
- Added a post-generation placeholder scan before the delivered-state
  transition.
- Delivery failures now retain the previous stage and record attempt status and
  blocker count.
- Removed the `fill_engine.py` invalid-escape warning.
- Replaced the former realistic sample identity with the fictional
  `DEMO-001` profile across JSON, Word, Excel, assignment names, comparable
  addresses, and tenant names.
- Scrubbed Word author/revision metadata while retaining Axiom branding and
  appraiser credentials.
- Added the approved `tests/fixtures/DEMO-001` regression fixture.
- Added fixture compatibility coverage; five tests now pass.
- Verified all six sanitized workbooks contain zero matches for the retired
  sample identifiers.
- Verified all 16 modified DOCX packages open successfully with unchanged part,
  paragraph, table, section, and media counts.
- Removed three obsolete `v14_page-*.jpg` QA screenshots; one contained a
  retired salutation baked into pixels and none were referenced by runtime code.
- Created the initial safe baseline commit with Git LFS tracking Word and Excel
  source artifacts.
- Added convention-based map, sketch, subject-photo, and lease-photo handlers.
- New assignments now receive the standard report-media folder structure.
- Validation reports the exact media path required for each missing image block.
- Added ownership-history table generation from the existing owner and
  prior-transfer fields.
- Expanded the automated baseline to seven passing tests.
- Fixed nested narrative model configuration and routed adjustment and
  reconciliation prose through their configured command models.
- Expanded the automated baseline to eight passing tests.
- Added versioned field registry v1 with 220 scalar fields and 20 pipeline
  blocks.
- Added `axiom.py contract` to detect workbook/template contract drift.
- Assignment creation now records application and schema versions; delivery
  records the template filename and SHA-256 hash.
- Corrected variable loading so numeric comp rows cannot leak into the scalar
  field dictionary.
- Added the previously missing land-sale location-map media convention.
- Expanded the automated baseline to nine passing tests.
- Advanced the field contract to v1.1.0 and the application to v0.3.0.
- Added deterministic derivation for six report-facing presentation variants.
- Updated the canonical Intake workbook so `VALUE_WORDS_FORMAL` is visibly
  calculated from `VALUE_WORDS` rather than entered twice.
- Removed stored presentation duplicates from the source-controlled fixture;
  fixture loading now proves they are regenerated from canonical facts.
- Kept semantically meaningful short/full property and value labels explicit.
- Expanded the automated baseline to twelve passing tests.
- Replaced workbook/JSON modification-time warnings with exact comparisons of
  canonical Intake-owned fields.
- Validation now names changed Intake keys and requires a fresh JSON export
  before final delivery.
- Engagement generation uses the same freshness gate and stops before creating
  documents when canonical Intake fields differ.
- Formula-cache checks now inspect only workbook-owned fields required by the
  conditionally trimmed report; disabled approaches no longer create blockers.
- Corrected output ownership so same-row formatting formulas do not falsely
  claim Intake/JSON fields.
- Populated the approved fictional fixture's Intake sheet from its canonical
  JSON for full registry-aware testing.
- Advanced the field contract to v1.1.1 and the application to v0.4.0.
- Expanded the automated baseline to sixteen passing tests.
- Added three fully fictional comparable-sale rows to the approved fixture.
- Added a deterministic generator for eleven synthetic QA map, sketch, subject,
  and lease-comparable images; every image is visibly marked as non-evidence.
- Added end-to-end tests proving three comp pages and all nine registered media
  blocks inject without unresolved placeholders.
- Replaced a Unicode console checkmark that crashed comp insertion under the
  Windows CP-1252 console.
- Expanded the automated baseline to eighteen passing tests.
- Added 21 isolated torture cases for malformed inputs, split Word runs,
  corrupt/oversized images, unsafe paths, locked files, 50 comps, 50 photos,
  long Unicode text, and interrupted generation.
- Delivery now builds to a same-directory temporary file and atomically
  replaces prior output only after all report insertion steps succeed.
- Failed input loading and generation preserve the prior report and assignment
  stage, clean temporary files, and record `input_failed` or
  `generation_failed`.
- Added strict assignment filename safety and exact file-number lookup.
- Added comp quality checks for duplicate numbers, missing addresses, and
  missing sale prices.
- Made placeholder and contract scanning run-aware throughout DOCX packages.
- Added image readability checks and a 25 MB per-image preflight limit.
- Added explicit optional-blank field metadata in contract v1.2.0 and advanced
  the application to v0.5.0.
- Engagement now uses temporary outputs and cannot transition to `engaged`
  when templates are missing or document generation fails.
- Expanded the automated baseline to thirty-nine passing tests.
- Added a complete deterministic DEMO-001 report builder and normalized
  structural golden fingerprint.
- Fixed cloned comp images whose source relationship IDs incorrectly resolved
  to the report's `settings.xml`; comp image relationships are now copied.
- Comp drawings now receive unique IDs, assignment media receives descriptive
  filename-derived alt text, and remaining template images receive baseline
  alt text.
- Accessibility high-severity findings on the generated report fell from 40
  to 0; 65 table-header findings remain for semantic/manual review.
- Advanced the application to v0.5.1 and expanded the baseline to forty-one
  passing tests.
- Added comparable-record contract v1.0.0 with canonical numeric/date
  semantics, stable sale/lease identities, content-hash provenance, explicit
  review status, reviewer/timestamp/edit history, and validation findings.
- Replaced sale-price-only deduplication with transaction identity; distinct
  properties at the same price are retained.
- Added SQLite migrations and unique indexes for source hashes and comparable
  identities.
- Confirmed batches now commit transactionally; unreviewed/invalid batches
  roll back, moved identical sources deduplicate, and changed sources require
  re-extraction.
- Added reviewed sale/lease search plus CSV and workbook `comp_data` export.
- Added CLI entry points for ingest, review, commit, and search.
- Verified a fictional historical workbook through extraction, review,
  database commit, repeat commit, search, CSV export, and report-workbook
  export.
- Replaced extraction CLI status glyphs that crashed Windows CP-1252 consoles.
- Advanced the application to v0.6.0 and expanded the baseline to forty-seven
  passing tests.
- Added canonical assignment-conclusion and income-snapshot contracts with
  stable identities, source hashes, review provenance, validation, and
  reviewed-only search.
- Activated standalone income-document extraction for period, PGI, vacancy,
  EGI, expenses, NOI, and applied cap rate; these files were previously
  classified but not processed.
- Added additive SQLite migrations, unique identity indexes, transactional
  commit, duplicate recommit handling, and UI review/edit support for both
  record types.
- Verified the full path with a generated fictional historical report and
  income chart, including rollback and legacy migration tests.
- Advanced the application to v0.7.0 and expanded the baseline to fifty-one
  passing tests.
- Activated the previously dormant rent-roll workbook lane and added explicit
  operating-expense workbook classification.
- Added canonical rent-roll-entry and operating-expense-line contracts,
  assignment-scoped identities, worksheet/row provenance, review/edit support,
  SQLite tables, unique indexes, reviewed search APIs, and
  `financial-search`.
- Kept subject rent-roll evidence separate from market lease comps and excluded
  total/subtotal expense rows to prevent analytical double counting.
- Verified fictional extraction, exact-row collapse, review edits,
  transactional rollback, duplicate recommit, and reviewed search.
- Advanced the application to v0.8.0 and expanded the baseline to fifty-five
  passing tests.
- Added bounded heading-based extraction for regional, market-area,
  neighborhood, property-market, and supply/demand observations.
- Added canonical observation identity, paragraph-range source provenance,
  inherited effective date/geography/property type, explicit truncation,
  Streamlit text review, SQLite storage, reviewed search API, and
  `observation-search`.
- Verified that short fragments and unrelated reconciliation content are not
  harvested, review edits persist, duplicate recommit is safe, and an
  unconfirmed section rolls back the entire batch.
- Advanced the application to v0.9.0 and expanded the baseline to fifty-eight
  passing tests.
- Added non-mutating indexing for external image/PDF artifacts,
  Word-embedded drawing images, Excel-embedded images, and native Excel chart
  objects.
- Added binary artifact hashes separate from container hashes, pixel
  dimensions, package/file locators, duplicate-location provenance, review
  metadata, SQLite storage, reviewed search, and `artifact-search`.
- Verified duplicate-binary collapse, Word alt-text map classification, native
  chart indexing, review edits, changed-source rejection, duplicate recommit,
  and full transactional rollback.
- Advanced the application to v0.10.0 and expanded the baseline to sixty-two
  passing tests.
- Added a basic wide operating-statement adapter for multi-year Excel layouts
  with year/scenario columns, including two-row year-over-Actual/`$/SF`
  headers.
- Wide statements now explode to canonical operating-expense lines, combine
  amount and amount-per-square-foot columns by year/scenario, skip total rows,
  and retain worksheet row/column layout provenance.
- Verified fictional wide-statement extraction, review, commit, persisted
  layout metadata, and reviewed search.
- Advanced the application to v0.10.1 and expanded the baseline to sixty-three
  passing tests.
- Added specialty Excel rent-roll handling for mini-storage, mobile-home,
  apartment, and RV/site-style headers without changing the database schema.
- Rent-roll parsing now understands site/lot/room/apartment identifiers,
  resident/name fields, move-in dates, lease-expiration variants, generic rent
  columns, status, discounts, and notes.
- Added defensive worksheet-dimension handling for workbooks whose `max_row`
  metadata is missing.
- Exact duplicate rent-roll and expense source rows collapse before review,
  retaining alternate worksheet provenance.
- Verified fictional specialty rent-roll extraction, duplicate collapse,
  review, commit, reviewed search, and no-dimension header detection.
- Advanced the application to v0.10.2 and expanded the baseline to sixty-five
  passing tests.
- Added native PDF rent-roll table extraction for PDFs with extractable table
  structure.
- Rent-roll PDFs are classified during assignment scanning, parsed into the
  canonical `axiom.rent_roll.entry` contract, indexed as source artifacts, and
  retain page/table/row provenance.
- Scanned/image-only PDFs intentionally return warnings instead of OCR output;
  OCR remains a separate later lane.
- Verified fictional ReportLab/PDF rent-roll extraction, staging, review,
  commit, reviewed search, and source-artifact coexistence.
- Advanced the application to v0.10.3 and expanded the baseline to sixty-six
  passing tests.
- Added native text-position accounting PDF extraction for PDFs with
  selectable text but no clean table structure.
- Accounting PDFs are scanned for recognized expense sections, parsed into
  canonical `axiom.operating_expense.line` records, and retain page/line
  provenance through `native_pdf_text_position_extractor`.
- Period year/type are inferred conservatively from the statement text and
  filename; totals, subtotals, income, NOI, and net-income rows are excluded.
- Expense-statement PDFs are now processed through the main historical
  assignment pipeline, not only direct parser calls.
- Verified fictional ReportLab/PDF P&L extraction, staging, review, commit,
  and reviewed operating-expense search.
- Scanned/image-only PDFs still return OCR-required warnings instead of
  speculative output.
- Advanced the application to v0.10.4 and expanded the baseline to sixty-seven
  passing tests.

## Completed this session (Claude, 2026-07-08)

- Designed the OCR lane in `docs/OCR_LANE_DESIGN.md` and got Derek's explicit
  sign-off on three open questions before writing code: local Tesseract
  install is approved, v1 scope is rent-roll + operating-expense PDFs only
  (no scanned narrative reports), and low-quality scans bail out with a
  warning rather than staging speculative rows.
- Implemented the OCR lane in `pdf_financial_extractor.py`: PyMuPDF
  rasterization (`_rasterize_pdf`), orientation correction with OSD +
  brute-force rotation fallback (`_correct_orientation`), Tesseract word
  extraction (`_ocr_words`, filters misread gridline punctuation), gap-based
  header-cell clustering (`_cluster_header_cells` / `_ocr_header_bands` —
  matches whole header cells instead of guessing at word n-grams, which
  avoids false multi-word matches across unrelated adjacent columns), and
  edge-boundary column assignment for data rows (`_assign_words_to_bands`).
  Refactored `_extract_text_expense_rows` into a shared
  `_expense_rows_from_pages` so native and OCR expense parsing use identical
  logic. Wired into `extract_financial_pdf`'s existing "OCR is required"
  branch — no new entry point for callers.
- Every OCR-derived field is forced to `confidence: "low"`; provenance gains
  `extraction_method` (`ocr_pdf_table_extractor` /
  `ocr_pdf_text_position_extractor`), `ocr_engine`,
  `ocr_avg_word_confidence`, `rotation_degrees_applied`, and
  `rendered_page_image` (saved under `ingest/staged/ocr_pages/`). No schema
  or DB change was needed — these are free-form provenance keys, and the
  existing stage -> review -> commit gate applies unchanged.
- Added OCR-aware review surfacing: Streamlit's comp-review view now shows a
  warning banner plus the actual rendered page image inline for OCR-sourced
  rent-roll/expense rows (reusing the Keep-checkbox gate that already existed
  for all rent-roll/expense rows); the terminal `review_staged` path prints
  an `[OCR NN/100 see <path>]` marker per OCR row. Terminal review still
  lacks true per-record keep/skip for rent-roll/expense rows generally
  (native or OCR) — that's a pre-existing gap, not newly introduced, and is
  called out as future work in the design doc.
- Added four tests to `tests/test_financial_harvest.py`: end-to-end scanned
  rent-roll extraction through commit
  (`test_ocr_scanned_pdf_rent_roll_end_to_end`), 180°-rotated scan orientation
  recovery (`test_ocr_rotated_scan_recovers_orientation`), illegible-scan
  bail-out (`test_ocr_illegible_scan_bails_out_with_warning`), and graceful
  degradation when Tesseract isn't installed
  (`test_ocr_lane_degrades_gracefully_without_tesseract`). All four, plus the
  9 pre-existing financial-harvest tests, pass (13/13) — verified against an
  isolated sandbox copy of the changed modules with byte-identical content to
  what's in this checkout (see "Known limitations" for why not verified
  directly in this checkout).

## In progress

- None — the OCR lane is functionally complete for its approved v1 scope.

## Exact next step

1. **Re-run the full suite in this actual checkout** —
   `python -m unittest discover -s tests -v` — to confirm all ~71 tests
   (67 prior + 4 new OCR tests) pass here, then `python axiom.py contract`
   (no field-registry keys changed, so this should still pass at v1.2.0).
   This session could not do that final live run itself; see "Known
   limitations."
2. Review and commit this session's changes (see "Do not touch" for the file
   list) — small, behavior-described commits per `AGENTS.md`.
3. After that: extend the OCR lane's real-world install (Tesseract on
   Derek's Windows machine) and do a live test against an actual scanned
   rent roll or P&L, not just the synthetic fixtures.
4. Longer-term, still open from before: add database migrations/backfills
   for legacy local comp rows before importing Derek's real historical
   archive (last remaining P1 comparable-intelligence item in
   `PROJECT_STATE.md`).

## Baseline checks run

- `python -m unittest discover -s tests -v`: 67 tests passed as of the prior
  (Codex) checkpoint. This session added 4 OCR tests and verified 13/13
  financial-harvest tests (9 prior + 4 new) pass in an isolated sandbox copy
  of only the changed modules; the full ~71-test suite has not been re-run
  live in this checkout this session — do that before committing.
- `python axiom.py contract`: passed at v1.2.0 with 220 fields and 20 blocks.
- `python -m compileall`: passed for runtime modules and tests.
- Torture ceiling exercised: 50 comps, 50 photos, approximately 64,000
  Unicode characters, malformed JSON/XLSX, corrupt/oversized media, split-run
  placeholders, simulated generation failure, and a simulated locked output.
- Complete generated-report golden: passed with 40 valid image relationships,
  unique drawing IDs, 8 sections, and zero unresolved placeholders.
- Document accessibility audit: 0 high, 65 medium table-header findings.
- Document render attempt: blocked because LibreOffice/`soffice` is not
  installed; no visual page-render claim is made.
- Fictional historical-workbook vertical slice: 2 sale comps, 1 lease comp,
  source-move idempotency, source-change rejection, rollback, reviewed search,
  CSV export, and workbook export passed.
- Registry-aware fixture freshness check: 0 stale Intake fields and 0 cache
  warnings.
- `axiom.py --help`: passed with the warning corrected.
- `DEMO-001` fixture validation: 0 ordinary missing fields, 8 unresolved
  blocks (all local AI narratives), and 10 expected sales-adjustment formula
  cache errors because the separate adjustment grid remains unpopulated.
- Fixture pipeline tests: 3 comp pages and 11 images across all 9 registered
  media blocks injected without remaining comp/media placeholders.
- Spreadsheet render review: Intake, market, lease-comps, rent-roll,
  land-sales, and output sheets retained readable formatting.
- DOCX render attempt: blocked because LibreOffice/`soffice` is unavailable;
  structural package QA passed instead.
- `axiom.py list`: passed; the active directory contains only the clearly
  labeled fictional `DEMO-001` assignment.

## Do not touch

- Use only `tests/fixtures/DEMO-001` for repeatable assignment testing.
- Do not push the repository or source Office documents to a remote.
- Do not live-test Adobe Sign, Xero, or Anthropic without explicit approval and
  local credentials.

## Uncommitted changes this session (Claude, 2026-07-08)

Not committed yet — see "Exact next step" item 1 (re-run the full suite
live in this checkout) before committing. Changed/added files:

- `pdf_financial_extractor.py` — OCR lane implementation.
- `ingest.py` — OCR-aware terminal review markers (`_is_ocr_record`,
  `_ocr_flag`); no logic changes to extraction/commit.
- `comp_review.py` — OCR warning banner + inline rendered-page-image display
  in `_render_record`.
- `tests/test_financial_harvest.py` — 4 new OCR tests + 2 fixture-building
  helpers (`_rasterize_to_scanned_pdf`, `_build_illegible_scan_pdf`).
- `docs/OCR_LANE_DESIGN.md` — new design doc (approved and implemented).
- `PROJECT_STATE.md`, `HANDOFF.md` — this update.

## Known limitations

- **This session's sandbox could not reliably run tests against this actual
  checkout.** The bash tool's mount of this OneDrive-synced folder did not
  pick up edits made through the file-editing tool even after repeated waits
  (multiple minutes); it appears to reflect a snapshot rather than a live
  sync within a session. Every change was verified correct by re-reading the
  authoritative file content after each edit, and the exact same content was
  separately verified to pass 13/13 relevant tests in an isolated sandbox
  copy — but the full suite has not been executed live in this checkout.
  **Whoever picks this up next should run
  `python -m unittest discover -s tests -v` and `python axiom.py contract`
  here first, before assuming anything beyond the financial-harvest tests is
  unaffected.**
- Plain `python` is not on PATH in the current Codex environment. The bundled
  Python runtime was used for checks.
- DOCX media layout has structural test coverage but still needs visual QA with
  representative landscape and portrait photos.
- Streamlit comparable review/browse behavior has service-level coverage but
  still needs an interactive browser pass.
- Missing/error Excel caches are detectable. A valid-looking but stale cached
  value cannot be proven stale from XLSX alone without an Excel-side
  calculation stamp or automation.
- The existing parent-folder `PROJECT_STATE.md` is historical and contains
  stale claims. This file and the project-root `PROJECT_STATE.md` are the
  canonical handoff documents going forward.
