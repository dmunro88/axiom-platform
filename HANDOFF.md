# Current Handoff

- Last updated: 2026-07-09
- Current agent: Claude
- Commits this session: pending — see "Completed this session (Claude,
  stress-test hardening — 2026-07-09)" below for the adversarial stress-test
  pass and its four auto-fixed, low-risk hardening changes. Prior commit
  `6ad25af` — see "Completed this session (Claude, hardening pass —
  2026-07-08)". Prior to that, `dde13b8` covered Codex's 2026-07-09 work plus
  the review-pass fixes described under "Completed this session (Claude,
  review pass — 2026-07-08)". Not pushed to any remote.

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
  (`test_ocr_lane_degrades_gracefully_without_tesseract`).
- Ran the full suite live in this checkout — `python -m unittest discover -s
  tests -v` — and confirmed 71/71 pass, then `python axiom.py contract`
  passed at v1.2.0. Committed as `af29fb2`.
- Asked for and got three parallel Fable-model reviews of `af29fb2`
  (data-safety/confidentiality, architecture-consistency, and an OCR
  column-detection deep-dive). Two issues warranted an immediate follow-up
  fix rather than backlog:
  - The commit had shipped `HANDOFF.md`/`PROJECT_STATE.md` text saying the
    work was "not yet committed" and the live test run "has not yet been
    re-confirmed" — self-contradictory the moment it landed. Corrected in
    this update.
  - The 4 new OCR tests imported `fitz`/`numpy`/`Pillow` unguarded at module
    level and had no skip guard for a missing Tesseract binary — since this
    repo has no tracked `requirements.txt`, either could crash or fail the
    whole test module on a machine that doesn't have them yet (exactly the
    machine HANDOFF told the next session to test on). Added a guarded
    import block plus `unittest.skipUnless` on all OCR tests (Tesseract-
    dependent ones additionally gated on a live `_ocr_available()` check).
  - The column-detection deep-dive independently confirmed a real (not just
    theoretical) risk: an OCR-misread digit on an otherwise well-formed row
    can slip past confidence="low" plus a review image because nothing
    catches internal arithmetic inconsistency, and a page whose OCR'd text
    has no recognizable header (e.g. an unheaded continuation page of a
    multi-page rent roll) silently drops all its rows with no warning at
    all. Added both checks to `pdf_financial_extractor.py`:
    `_rent_roll_arithmetic_warning` (annual rent vs. monthly rent x 12,
    rent/SF vs. annual rent / leased SF) and
    `_rent_roll_total_reconciliation_warning` (summed column values vs. the
    page's own discarded Total row), plus a warning whenever
    `_ocr_rent_roll_rows` can't find a header on a page at all. Rows that
    fail these checks are still staged for review (not dropped) — the
    checks only add a warning naming the page/row.
  - Two new regression tests cover these:
    `test_ocr_arithmetic_mismatch_warns_without_dropping_row` and
    `test_ocr_continuation_page_without_header_warns_instead_of_silent_loss`.
  - The remaining review findings (page-image cleanup/lifecycle, the
    rent-roll OCR path not being unified with the native path the way the
    expense path was, the OCR→low-confidence rule being enforced by a
    string-prefix check in three places instead of centrally, no
    `app_version` bump for this lane) were judged lower-priority hardening,
    not immediate bugs — left as backlog, not fixed this session.
  - Ran the full suite live again — 73/73 pass (71 prior + 2 new regression
    tests) — then `python axiom.py contract` passed at v1.2.0. Committed as
    a follow-up to `af29fb2`.

## Completed this session (Codex, 2026-07-09)

- Reconfirmed the canonical project root and reread `AGENTS.md`,
  `PROJECT_STATE.md`, and `HANDOFF.md` before edits.
- Investigated the dirty Office/template status. The files on disk are still
  real DOCX/XLSX ZIP packages matching the committed blob sizes; Git shows
  them dirty because `.gitattributes` now routes Office files through the LFS
  clean filter while the committed blobs are full binaries. Do not stage those
  Office artifacts until the LFS normalization decision is made deliberately.
- Installed Python OCR dependencies into the bundled Codex Python runtime:
  `PyMuPDF` and `pytesseract`.
- Installed UB Mannheim Tesseract 5.5.0 under
  `C:\Program Files\Tesseract-OCR`. The silent installer included `osd` but
  not English traineddata, so `eng.traineddata` was downloaded from the
  official `tesseract-ocr/tessdata_fast` repository into ignored local
  `.local/tessdata`.
- Hardened `pdf_financial_extractor.py` so OCR does not depend on PATH:
  it now detects `AXIOM_TESSERACT_CMD`, optional `config.json` OCR paths, and
  normal Windows install locations for `tesseract.exe`, plus
  `AXIOM_TESSDATA_DIR`, optional `config.json`, local `.local/tessdata`, and
  normal Windows tessdata locations for English OCR data.
- Added `.local/` to `.gitignore` so local OCR model files stay out of source
  control.
- Verified `_ocr_available()` now returns true and points to
  `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Ran all six OCR tests directly: all passed.
- Ran the full suite live with real OCR enabled:
  `python -m unittest discover -s tests -v` passed 73/73 with zero skips.
- Ran `python axiom.py contract`: passed at v1.2.0 with 220 fields and
  20 blocks.
- Live-tested a live archive rent-roll PDF supplied by Derek without printing
  tenant names, rent amounts, or the source filename. The original PDF has
  extractable table structure, so normal extraction used
  `native_pdf_table_extractor` and returned 2 rent-roll rows with no warnings.
- To exercise the OCR lane against the same real document, rendered it into a
  temporary image-only PDF outside the repo and ran extraction there. OCR
  returned 15 low-confidence rent-roll rows via `ocr_pdf_table_extractor` and
  one expected missing-header warning for page 2. Review-page image provenance
  was verified in ignored `.local/ocr_review_test`, then that temporary
  confidential image directory was deleted.
- Live-tested a live archive operating-statement PDF supplied by Derek without
  printing categories, amounts, or the source filename. The original PDF has
  a native text layer, so normal extraction used
  `native_pdf_text_position_extractor` and returned 4 operating-expense lines
  with no warnings.
- A temporary image-only rendering of the same proforma exposed an OCR
  orientation issue: Tesseract OSD could rotate the landscape page into
  column-like text with high confidence but no extractable expense rows.
  Hardened OCR orientation selection to score all four rotations by recovered
  financial rows first, then confidence. After the fix, the image-only
  proforma recovered 1 low-confidence expense line at 200 DPI and 3 at 300
  DPI. At 400 DPI it over-read the mixed rent/proforma grid as rent-roll rows,
  so naturally scanned mixed-layout proformas still need careful human review.
- Added `test_ocr_orientation_prefers_financial_rows_over_word_count` to lock
  the orientation-selection behavior without depending on a brittle real OCR
  fixture.
- Ran `comp-ingest` end-to-end against a copied live archive assignment
  folder under `scratch/historical_ingest_test/`. The staging run found 12
  sale comps, 10 lease comps, 3 market observations, 226 artifacts, and 6
  warnings. Warnings included unmapped workbook headers and a naturally
  image-only income-statement PDF that OCRed with good confidence but did not
  match current rent-roll/expense section rules, so no speculative financial
  rows were staged.
- Simulated review/commit of that staged batch into a temporary database
  rather than the real local database. First attempt exposed a real blocker:
  a lease comp had `lease_expiration: "N/A"`, which failed comparable-date
  validation. Fixed comparable date normalization so placeholder date values
  (`N/A`, `NA`, `none`, `not applicable`, `-`) canonicalize to blank.
- After the fix, simulated review/commit into a temp DB succeeded with
  1 assignment, 12 sale comps, 10 lease comps, 3 market observations,
  226 source artifacts, and 34 source documents. No rent-roll or
  operating-expense rows were committed from this copied folder.
- Added `test_placeholder_lease_expiration_canonicalizes_to_blank`.
- Added `scratch/` to `.gitignore` so copied live archive folders are not
  accidentally staged.
- Deleted the generated OCR page snapshot for the live income statement
  after confirming no staged row referenced it.
- Ran a second copied archive batch from `scratch/historical_ingest_test_2`
  containing five assignment folders. The five staged JSON batches contain,
  after canonical staging, 45 sale comps, 28 lease comps, 962 rent-roll rows,
  0 operating-expense rows, 10 market observations, 1,570 source artifacts,
  365 source documents, and 9 warnings. Warnings were primarily unmapped
  workbook headers; the main extraction gap remains operating expenses.
- Simulated confirming and committing those five staged batches into a
  temporary database using the app's normal `get_conn` path. The simulation
  succeeded for all five batches with 5 assignments, 38 new sale comps,
  7 duplicate sale comps skipped, 28 lease comps, 962 rent-roll entries,
  10 market observations, 1,570 source artifacts, and 365 sources. The real
  local database was not touched.
- Fixed the operating-expense miss exposed by that second batch. The source
  P&L PDFs were nested under source-material subfolders that the assignment
  scanner intentionally skipped at the root level, so they were indexed as
  artifacts but never sent through `extract_financial_pdf`. The scanner now
  recursively routes strictly named financial PDFs (`rent roll`, `P&L`,
  `profit and loss`, `income statement`, etc.) into the financial parser while
  leaving broad document scanning unchanged.
- Added a conservative PDF statement fallback for P&L/income statements that
  have income/gross-profit boundaries and expense-like money lines but omit an
  explicit `Expense` heading. The fallback requires at least two candidate
  rows and stages fallback records with low/medium confidence for review.
- Added OCR batch-performance controls: image-only PDFs default to the first
  6 OCR pages with a warning when truncated, very large embedded scans are
  downscaled before OCR, and later pages reuse the first page's detected
  orientation unless confidence drops. Both limits can be overridden with
  `AXIOM_OCR_MAX_PAGES` and `AXIOM_OCR_MAX_RENDER_EDGE_PX`.
- Re-ran `comp-ingest` against `scratch/historical_ingest_test_2` after the
  nested-PDF/OCR-performance changes. The latest five staged JSON batches
  contain 45 sale comps, 28 lease comps, 962 rent-roll rows, 196
  operating-expense rows, 10 market observations, 1,570 artifacts, 409
  source references, and 48 warnings. Expense rows came from the normal
  OCR text-position expense extractor; the statement fallback is covered by
  synthetic regression tests but was not needed for those live-copy rows.
- Simulated confirming and committing the latest five staged batches into a
  temporary database. The simulation succeeded for all five with 5
  assignments, 38 new sale comps, 7 duplicate sale comps skipped, 28 lease
  comps, 962 rent-roll entries, 196 operating expenses, 10 market
  observations, 1,570 source artifacts, and 365 source documents. The real
  local database was not touched.

## Completed this session (Claude, review pass — 2026-07-08)

- Per `AGENTS.md`'s start-of-session protocol, verified Codex's 2026-07-09
  handoff against the actual files instead of trusting it at face value.
  Found the bash sandbox's OneDrive mount has two issues worse than
  previously documented: `git status`/`git diff` can falsely report "clean"
  due to a stale stat-cache (only `git hash-object` vs `git ls-tree HEAD`
  gives a truthful answer), and bash `cp`/`cat` can silently truncate large
  files (`pdf_financial_extractor.py`, `comparable_contract.py`,
  `extractor.py`, both changed test files) mid-statement — confirmed via
  `python -m py_compile` syntax errors on files that `Read` showed were
  complete and correct. Re-synced all five truncated files into bash via
  heredoc from verified `Read` content before doing anything else.
- Asked for and got three parallel Fable-model reviews of Codex's uncommitted
  work (logic/correctness, data-safety, docs-consistency). Findings and
  fixes:
  - This handoff's own header misattributed my `af29fb2`/`278951e` commits
    to "this session" under Codex's byline, and never stated that Codex's
    8 changed files were uncommitted — corrected above.
  - Real assignment identifiers (file number, street/city fragment, real
    filenames) had leaked into this handoff's prose — genericized.
  - `PROJECT_STATE.md` had two stale sentences left over from before the
    77-test count (73 vs. 77, "six" vs. seven OCR tests) — corrected.
  - `docs/OCR_LANE_DESIGN.md` named wrong `extraction_method` values and
    still had leftover pre-approval "proposes"/"needs your sign-off"
    language despite being titled "(Implemented v1)" — corrected.
  - Two stray files (`zzz_discard_me.bak`, a broken `node_modules` symlink)
    couldn't be deleted from this sandbox (same unlink restriction as stale
    git locks) — added `*.bak` and a bare `node_modules` line to
    `.gitignore` instead; see "Known limitations".
  - The nested-financial-PDF-routing change actually lives in `extractor.py`
    (`scan_assignment_folder`), which had been omitted from every prior
    changed-files list — added above. No logic bug was found in it once
    verified against the untruncated file (see next bullet); the earlier
    apparent test failure was the bash-truncation artifact, not a real bug.
  - Two real-but-lower-priority design gaps flagged for future hardening,
    not fixed this pass: nested-PDF routing has no staleness/duplicate
    defense (a stale prior-year PDF or one copied into two subfolders
    parses with no distinguishing warning), and OCR orientation re-detection
    on later pages only triggers on low confidence, not "no financial
    structure found" (a mixed-orientation scan bundle could silently lose a
    page's rows).
- Ran `tests/test_financial_harvest.py` (all 18 tests, including the 7 that
  need live Tesseract) and `tests/test_comp_pipeline.py` (all 7 tests) live
  against the re-synced, verified-correct files — 25/25 pass, zero failures,
  zero skips. `python axiom.py contract` passed at v1.2.0 (220 fields, 20
  blocks). `python -m compileall` passed for the whole repo.
- This session's fixes are being committed together with Codex's verified
  2026-07-09 work as a single commit describing the combined behavior.

## Completed this session (Claude, hardening pass — 2026-07-08)

Closed out both remaining items from `dde13b8`'s "Exact next step" (the
lower-priority OCR hardening backlog and the DB-migration item), per Derek's
explicit "let's just knock the rest of it out" instruction. Verified in an
isolated sandbox mirror first (with a real Tesseract 5.5.0 install and live
OCR), then ported the same verified edits into this checkout and re-ran
everything live here too — see "Baseline checks run" below.

- **OCR page-image retention.** `OCR_PAGES_DIR` now respects an
  `AXIOM_OCR_PAGES_DIR` override (`_ocr_pages_dir()`), matching the existing
  `AXIOM_TESSERACT_CMD`/`AXIOM_TESSDATA_DIR` config pattern. Added
  `prune_ocr_pages()` plus a new `axiom.py ocr-cleanup` command: it deletes
  rendered page PNGs under `ingest/staged/ocr_pages/` that are no longer
  referenced by any staged or confirmed `.json` batch still awaiting
  review/commit. It's a manual command, not automatic, so an image is never
  deleted while a human might still want to cross-check it.
- **Unified OCR/native rent-roll row logic.** Added
  `_finalize_rent_roll_row()` in `pdf_financial_extractor.py`: the shared
  post-cell-extraction logic (deriving/normalizing fields, detecting
  total/subtotal rows, attaching `as_of_date`, applying the OCR confidence
  policy, building the staged record) that both `_extract_table_rows`
  (native) and `_ocr_rent_roll_rows` (OCR) now call, instead of duplicating
  it. Column/cell extraction itself stays separate (native has real table
  cells; OCR only has word positions), which is the genuine difference
  between the two paths.
- **Centralized the OCR confidence="low" rule.** Added
  `enforce_ocr_low_confidence(confidence, extraction_method)` to
  `harvest_contract.py`. Replaced three separate ad hoc implementations in
  `pdf_financial_extractor.py` (`_expense_rows_from_pages`,
  `_statement_expense_rows_from_pages`, and the rent-roll path's hardcoded
  force-low) with calls to the shared helper. This also fixed a real,
  previously undetected bug: the statement-expense-fallback path never
  actually forced `period_type` confidence down to `"low"` for OCR-derived
  rows (it left whatever `_period_type_from_text` had assigned, often
  `"medium"`) — silently violating the documented "no OCR field is ever
  medium/high" invariant from `docs/OCR_LANE_DESIGN.md`. No test exercised
  that specific combination before, so nothing was silently broken by the
  fix; it just makes the invariant actually hold.
- **Nested-PDF staleness/duplicate warning.** Added
  `_nested_financial_pdf_warnings()` in `extractor.py`, called from
  `scan_assignment_folder`: when more than one rent-roll or
  operating-statement PDF is found for an assignment — including ones
  discovered by the nested-subfolder scan (e.g. under "Information
  Provided") — it warns naming each file's location and modified date so
  Derek can check for stale/duplicate copies before review. It doesn't try
  to auto-resolve which file wins; the extractor has no reliable way to know
  that, and the existing human-review gate already catches bad data before
  DB commit.
- **OCR orientation re-detection trigger fix.** Added
  `_financial_structure_signals()`/`_page_has_financial_structure()` in
  `pdf_financial_extractor.py` (factored out of
  `_choose_financial_ocr_orientation`'s existing per-rotation scoring).
  Later pages in `_extract_via_ocr` now re-run full orientation detection
  when the current orientation yields no recognizable rent-roll/expense
  structure at all, not just when OCR confidence is low — closing the gap
  where a mixed-orientation scan bundle (e.g. portrait cover page followed
  by a landscape rent roll) could silently lose a page's rows because
  garbled-but-still-legible sideways text can score confidence high enough
  to skip re-detection. Verified this doesn't regress the existing
  headerless-continuation-page case (a legitimately no-structure page still
  correctly keeps its original orientation, just at the cost of one extra
  OCR pass) — `test_ocr_continuation_page_without_header_warns_instead_of_silent_loss`
  still passes.
- **Legacy comp-row identity backfill (P1 comparable-intelligence item).**
  Added `backfill_legacy_identities(conn)` to `db.py`, called automatically
  from `init_db()` after `_apply_migrations()`. Computes and stores
  `identity_key` for any `comps`/`lease_comps`/`assignments`/
  `income_snapshots` rows that predate the identity-key column (still NULL).
  Without this, a legacy row is invisible to `comparable_id_by_identity`/
  `harvest_id_by_identity` — both match on `identity_key`, and NULL never
  matches — so importing Derek's real historical archive would insert
  duplicates for anything already in the database from before identity
  keys existed, instead of being recognized and skipped. Defensively checks
  column existence per table first (safe against unusual legacy schemas).
  `rent_roll_entries`/`operating_expenses`/`market_observations`/
  `source_artifacts` don't need this: those tables were introduced with
  `identity_key` already part of their schema, so every row in them already
  has one.
- Added 5 new tests across `tests/test_financial_harvest.py` (4) and
  `tests/test_comp_pipeline.py` (1) covering all of the above. Full suite is
  now 82 tests (was 77).
- Ran the full suite live in this checkout — `python -m unittest discover -s
  tests -v` equivalent, run per-module due to sandbox time limits — 82/82
  pass, zero skips (real Tesseract available). `python axiom.py contract`
  passed at v1.2.0 (220 fields, 20 blocks).

## Completed this session (Claude, stress-test hardening — 2026-07-09)

Per Derek's request ("run a tough stress test from start to finish of the
entire built project so far... should we have Fable model do this?"), ran an
adversarial multi-agent stress test using the Fable model — an agent that
didn't write this code and has no bias toward believing it already works.
Derek's explicit governing instruction for this pass: **auto-fix low-risk
issues (missing guards, unhandled exceptions, unclear errors) and report
them; flag anything touching data safety, DB schema, or business logic for
his own review instead of silently changing it.**

- Built three isolated rsync'd sandbox mirrors (`stress_golden` baseline plus
  `stress_A`/`stress_B`/`stress_C` working copies) excluding real client data
  directories (`ingest/`, `scratch/`, `.sanitization_work/`, `.local/`), so
  adversarial testing could freely mutate/break things with zero risk to real
  data or the real database. Confirmed the golden baseline green (82 tests +
  contract check) before any agent touched a copy.
- Spawned three parallel Fable-model agents, one per subsystem: (A) report
  generation/delivery pipeline, (B) comp/financial ingestion + OCR, (C)
  DB/ingest/review/commit + CLI misuse. All three did substantial real work
  (111/87/148 tool calls respectively) but hit a session limit before
  returning final written summaries; their raw artifacts (report files,
  attack scripts, partial logs) were read directly and any script whose
  output wasn't captured to disk was re-run to recover the findings — no work
  was lost, and one incomplete script (Agent B's `attack_e_routing.py`,
  genuinely truncated mid-write, not a stale-mount artifact) was completed
  before running it.
- **Four low-risk fixes were verified in a sandbox mirror, then ported into
  this checkout and re-verified live** (all four compile clean and the full
  82-test suite plus `python axiom.py contract` pass with zero regressions):
  1. **Illegal-XML-character guard in `fill_engine.py`.** A field value
     containing a C0/C1 control character (e.g. a stray `\x07` in a
     copy-pasted narrative) used to crash opaquely deep inside
     `doc.save()`. Added `_reject_illegal_xml_value()`: raises a clear
     field-named error (naming the field and the exact code point) before
     substitution instead of a bare python-docx traceback.
  2. **NaN/Infinity rejection in `financial_extractor.py` and
     `harvest_contract.py`'s `_number()` helpers.** Python's `float()`
     accepts the literal strings `"nan"`/`"inf"`/`"Infinity"`, and
     `json.dump` then emits these as bare (invalid-JSON) tokens into staged
     batches. A malformed or OCR-misread cell containing one of these
     strings would previously produce a non-finite rent/expense amount that
     corrupts arithmetic checks and dedupe. Both `_number()` helpers now
     check `math.isfinite()` and degrade to `None` (missing) instead,  so
     review catches it as an ordinary missing value.
  3. **Malformed-staged/confirmed-JSON guards in `ingest.py`.** `review_staged()`
     and `commit_confirmed()` used to crash the entire batch run on one
     corrupt or non-object JSON file. Both now catch
     `json.JSONDecodeError`/`RecursionError`/`OSError`/`ValueError`, print a
     clear "SKIPPED unreadable file: ..." message, and continue to the next
     file rather than aborting the whole run.
  4. **Wrong-type list-field validation in `ingest.py`'s
     `commit_extraction_resu