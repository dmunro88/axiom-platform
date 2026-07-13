# Axiom Platform — Project State

- Last verified: 2026-07-13
- Status: Functional prototype in active local use; production safeguards and
  repeatable tests are incomplete.
- Phase 6 (Adjustment Grid) shipped complete 2026-07-10 and has since been
  through four rounds of Fable-model adversarial review; all four rounds
  found real bugs, and all are fixed and committed (`9d198a5`, `9026f2e`,
  `4db2456`, plus round 4's Q1-Q9 fixes committed 2026-07-13). See
  `HANDOFF.md`'s "Completed this session (Claude, Phase 6 hardening rounds
  1-4 — 2026-07-11)" and its "Round 4 fixes — completed 2026-07-13" note
  for details. No round-5 Fable review has been spawned — don't spawn one
  without checking with Derek first (usage-consumption concern he's
  raised previously). The live-fire test on a real assignment remains a
  separate, unscheduled step.
- **A git-integrity gap was found and fixed 2026-07-13:** `ingest.py` and
  `narrative_generator.py` (plus `.gitignore`, `HANDOFF.md`, this file, and
  `docs/ADJUSTMENT_GRID_DESIGN.md`) had been *committed* with content
  truncated mid-statement — the known bash/OneDrive large-file-truncation
  bug (see "Known limitations" below) had, this one time, landed inside a
  commit rather than being caught before one. `ingest.py`'s committed
  version (unchanged since `8400e01`, 2026-07-09) actually raised
  `SyntaxError` if compiled as committed. Fixed by committing the working
  tree's already-correct content (`a646c51`). No functional behavior
  changed — this restores content, it doesn't add it. See `HANDOFF.md`'s
  "Completed this session (Claude, git-integrity fix — 2026-07-13)" for the
  full account, including the stale git-lock workaround needed to commit on
  this mount and 10 orphaned scratch files cleaned up in the same pass.
- **The full test suite was verified live the same day (2026-07-13) on
  Derek's own real machine** (the first time it ran here rather than in the
  prior cloud sandbox), surfacing and closing two environment gaps: a
  pre-existing Windows-incompatible hardcoded `/tmp` path in one test (fixed,
  `2623a2a`), and this repo having no dependency manifest at all (fixed by
  adding `requirements.txt`, `30469b6`). See "Verified baseline" below for
  the resulting numbers and `HANDOFF.md` for the full account.
- **Track 1 visual-reference foundation started 2026-07-13:** `source_artifacts`
  now has nullable `comp_id`/`lease_comp_id` links, `db.py` has helpers for
  direct manual comp-photo attachments, and `comp_review.py`'s Browse tab can
  attach JPG/PNG photos to a selected sale or lease comp and show thumbnails
  for comps with attached photos. Uploaded images are copied under ignored
  local storage (`.local/comp_media`).
- **Current-code staging pass completed 2026-07-13 against the copied archive
  folders in `scratch/`:** six latest staged batches now exist for review,
  with 95 sale/lease rows total (57 sale comps, 38 lease comps) and zero hard
  comparable validation errors in the generated review packet. A helper script
  writes `scratch/staged_comp_review/latest_sale_lease_comp_review.csv` and
  `.md` from the newest staged batch per assignment without confirming records,
  moving staged files, or writing `axiom.db`.
- **The real local `axiom.db` was initialized schema-only on 2026-07-13.**
  It contains all current tables/migrations, including `source_artifacts`
  `comp_id`/`lease_comp_id`, and has zero rows in every application table.
  No copied archive, test, or build data was committed into the real database.
  The next database step is to ingest/review/commit actual selected records,
  not to create the database file.
- **Track 2 UI/UX consolidation started 2026-07-13:** `axiom_ui.py` is now a
  single Streamlit workbench with Dashboard, Assignment Workflow, Comp Library,
  Search, and System views. It surfaces `validate`, `contract`, dashboard
  generation, reviewed comp/financial/observation/artifact search, database
  counts, staged/confirmed counts, assignment file actions, draft delivery,
  and the existing comp-library review/browse module. `start_axiom_ui.bat`
  now installs from `requirements.txt` so the launcher matches the verified
  dependency manifest. Syntax and contract checks pass; live browser QA is
  still pending because the bundled Codex Python used here does not have
  Streamlit installed.

This file is agent-neutral and describes verified current behavior. Historical
notes in the parent folder are retained for context but are not authoritative.

## Product

Axiom is a local commercial-appraisal workflow platform for Axiom Commercial
Appraisal. It creates assignment workspaces, generates engagement documents,
supports appraisal calculations in Excel, fills Word reports, manages a comp
library, and can draft selected narrative sections with AI.

The appraiser remains responsible for facts, analysis, judgment, review, and
the signed deliverable.

## Current architecture

1. `workbook.xlsx`
   - Intake sheet for assignment facts
   - Calculation sheets for appraisal analysis
   - `outputs` sheet for keyed report values
2. `*_variables.json`
   - Exported from the workbook by a VBA macro
   - Loaded before workbook output values
3. `schemas/field_registry.v1.json`
   - Versioned contract for scalar fields and pipeline blocks
   - Records producers, source of truth, value kind, and consuming stages
4. Python orchestration
   - `axiom.py`: assignment commands and dashboard
   - `fill_engine.py`: Word substitution and conditional removal
   - `comp_builder.py`: comparable-sale page injection
   - `narrative_generator.py`: Anthropic-backed narrative drafting
   - `db.py`, `extractor.py`, `ingest.py`: comp extraction/review/database
   - `axiom_ui.py`: Streamlit v1 workbench shell
   - `comp_review.py`: comp-library extract/review/database/browse module
5. Local integrations
   - `adobe_sign.py`: Acrobat Sign OAuth client
   - `xero_client.py`: Xero custom-connection client

## Verified commands

| Command | Current behavior |
|---|---|
| `new` | Creates an assignment folder, workbook copy, output folder, and `.axiom.json` state |
| `engage` | Locally generates engagement letter, document request, and invoice after canonical Intake/JSON freshness passes |
| `deliver` | Generates a final report only after validation passes; `--draft` generates a distinctly named draft without changing delivery stage |
| `validate` | Checks fields, block handlers, workbook formula caches, and possible JSON staleness without changing assignment files or state |
| `contract` | Audits workbook and configured template keys against field registry v1 |
| `dilmore` | Fixed (2026-07-10): now calls the shared `dilmore_summary(subject_gba, comp_gbas, curve)` helper (correct ratio = comp/subject, correct 2-arg calls) instead of the old inline 3-arg call that raised `TypeError` on every real run. Invalid curve values in `size_adj!B3` now fail loudly with no partial write, instead of a raw traceback. A same-day follow-up correction (also 2026-07-10, before Phase 6 work began) fixed a second bug in that same fix: it wrote Size Factor/Adj % to columns 3/4 (C/D) instead of the real `size_adj` layout's columns 4/5 (D/E) — column C holds a pre-existing per-row Ratio formula that the wrong mapping would have silently overwritten on any real run. Found by inspecting the real `templates/workbook.xlsx` header row directly rather than trusting the original (self-consistent but wrong) test fixture. Two regression tests (`test_dilmore_uses_correct_ratio_direction_and_signature`, `test_dilmore_invalid_curve_fails_loudly_without_writing` in `tests/test_torture.py`) now build a fixture matching the real header row/formula and assert column C survives untouched — this command had zero test coverage before 2026-07-10. |
| `extract` | Extracts comparable and narrative data from supported source documents |
| `comp-ingest` | Scans historical assignment folders and stages versioned comparable, assignment, financial, and observation records |
| `review-staged` / `comp-commit` | Confirms staged records and transactionally commits reviewed evidence |
| `comp-search` | Searches reviewed sale or lease comps by canonical database fields |
| `financial-search` | Searches reviewed rent-roll and operating-expense records |
| `observation-search` | Searches reviewed market observations by category, geography, property type, text, and date |
| `artifact-search` | Searches reviewed maps, charts, photos, sketches, and exhibits |
| `list` / `status` | Reads assignment metadata and files |
| `dashboard` | Regenerates a local HTML assignment dashboard |

Important: `engage` does not currently transmit documents. Adobe Sign and Xero
are separate modules and are not wired into the command workflow.

## Verified baseline

Checks were performed without regenerating or modifying assignment outputs.

- The CLI imports and displays help. Verified 2026-07-13 using Python 3.14
  from a real local install on Derek's own machine; earlier verifications
  (through 2026-07-11) used Python 3.13 from the Codex cloud sandbox's
  bundled runtime.
- **155 automated tests pass, 0 skipped, 16 subtests passed — confirmed live
  in a single full run** (`pytest tests/ -q`) on 2026-07-13, covering
  validation, delivery-state, stress, golden-DOCX, comparable,
  historical-harvest, media, comp-page, structured-block, model-routing,
  contract, presentation-derivation, narrative-data-guard, Phase 6
  adjustment-grid, and OCR-lane tests. All 6 real-Tesseract OCR tests in
  `test_financial_harvest.py` ran against a genuine local Tesseract 5.5.0
  install with English tessdata already present on this machine — no test
  was skipped or split into batches, since the prior cloud sandbox's
  per-command time limit doesn't apply here. `requirements.txt` (added the
  same day) now pins the 10 third-party packages this required. See
  `HANDOFF.md`'s per-session entries for the full test-count growth history
  (77 -> 146 tests across 2026-07-08 through 2026-07-11) leading up to this
  count.
- **Phase 6 Adjustment Grid, complete (2026-07-10):** `size_adj` was
  replaced by `sca_adjustment_grid` (full sales-comparison net-adjustment
  grid, one time-adjustment checkpoint then summed category adjustments —
  see `docs/ADJUSTMENT_GRID_DESIGN.md`), and the old 3-section `land` tab
  was replaced by `land_adjustment_grid` (same pattern, Location/
  Topography/Surrounding Land Uses categories per `adjustment_factors.json`'s
  land preset, no Dilmore/Size column — land comps never had a real
  building-GBA-elasticity basis for one). `sca_qualitative`/
  `land_qualitative` (0/1/-1 per-factor manual scoring, Overall =
  AVERAGE() ignoring blanks, Rating via an adjustable threshold cell) were
  added, `field_registry.py` now registers all 4 `*_GRID_BLOCK` markers
  under the `comparables` handler and enforces a reverse-direction
  contract-drift check (registry -> template, not just template ->
  registry), and `adjustment_grid.py` (new) reads all 4 grid tabs via a
  runtime header-row column map (not a fixed letter map) and injects each
  as a Word table, wired into `axiom.py`'s deliver stage. Fixed three real
  pre-existing bugs found along the way: `size_adj!B4`'s Subject GBA
  reference pointed at the wrong Intake row; `narrative_generator._read_land_adj`
  read the wrong row range from the old `land` tab (crashed on realistic
  data — see git log for `9b832a7`); and `adjustment_grid.py`'s own row
  scan initially misread a grid's MEAN/summary rows below the comps as
  extra phantom comps until anchored on the "Sale No. N" comp label (see
  `test_adjustment_grid.py`'s `test_stops_at_mean_and_summary_rows_below_comps`).
  Also fixed an unrelated defect in the real `templates/workbook.xlsx`
  found while running the full suite: the Intake sheet's `REPORT_TYPE` row
  was merged across all 4 columns like a section header, so it had no
  actual cell to type a value into.
- **Phase 6 hardening, all four rounds complete (round 4 fixed
  2026-07-13).** An iterative Fable-model adversarial-review cycle (spawn a
  review agent, fix real findings, re-spawn to verify, repeat) against
  Phase 6 found and fixed real bugs across four rounds: round 1
  (`9d198a5`, findings A1-A5), round 2 (`9026f2e`, finding N1 plus
  residual gaps in round 1's A1/A3/A5 fixes), round 3 (`4db2456`,
  findings P1-P4 — a false-positive stale-formula-cache deadlock that
  could permanently block valid deliveries, a last-comp orphan-anchor gap
  that could silently drop a comp from a delivered report, a Dilmore/
  report-reader row-scan disagreement, and a `--draft` mode side effect
  that could mutate the workbook/delivery state despite promising not
  to), and round 4 (committed 2026-07-13, findings Q1-Q9 — comp-library
  export not marking the formula cache stale like a real Dilmore write
  does, Dilmore writing to hardcoded columns instead of header-resolved
  ones, a live-formula comp GBA cell being read as raw formula text
  instead of its cached value, draft mode erasing a still-relevant prior
  delivery error message, an unhelpfully generic draft-mode skip message,
  the stale-cache flag never being cleared after a successful delivery,
  plus a bonus fix to `_save_state`'s atomic-write fallback found while
  testing Q8). See `HANDOFF.md`'s "Round 4 fixes — completed 2026-07-13"
  for the full list, severities, and which files/tests changed. No
  round-5 Fable review has been spawned yet — don't spawn one without
  checking with Derek first.
- The platform folder arrived without dedicated Git history. A dedicated
  repository is initialized with a safe baseline commit.
- As of 2026-07-13, `HEAD` for `ingest.py` and `narrative_generator.py`
  compiles cleanly and contains their complete, intended content — verified
  directly via `git show HEAD:<path>` piped through `py_compile`, not just
  by reading the working tree. Prior commits back to 2026-07-09 had silently
  carried truncated versions of these files (see the git-integrity note
  above).
- The live assignment directory now contains one clearly labeled fictional
  assignment: `DEMO-001_Northstar_Example_Holdings`.
- `tests/fixtures/DEMO-001` is the approved source-controlled regression
  fixture.
- Fixture validation reports 0 ordinary missing keys and 8 unresolved block
  placeholders, all intentionally local AI narratives.
- The fixture includes three fictional comparable-sale rows and eleven
  deterministic synthetic QA images. Tests inject all three comp pages and all
  nine registered media blocks (eleven total images).
- Dashboard readiness now counts ordinary missing fields and unresolved blocks.
- Final delivery now stops before generation when validation fails.
- Draft generation remains available through explicit `--draft` and does not
  change delivery stage.
- Final output is scanned after comp and narrative injection; remaining
  placeholders prevent the delivered-state transition.
- Delivery attempts record status and blocker count while preserving the
  previous assignment stage on failure.
- Delivery documents are generated to same-directory temporary files and
  atomically replace prior output only after all insertion steps succeed.
- Contract v1.2.0 distinguishes required fields from two explicitly optional
  blank assumption/condition fields; this behavior was introduced in
  application v0.5.0.
- Stress coverage includes malformed inputs, split-run placeholders, corrupt
  and oversized media, unsafe paths, locked outputs, 50 comps, 50 photos, and
  long Unicode text. See `docs/STRESS_TEST_REPORT.md`.
- Complete-report structural golden coverage detects normalized OOXML, package,
  relationship, media, text/style, table, section, and page-break drift.
- Comp-template images now copy their relationships into the report package;
  cloned drawings receive unique IDs and all output images receive baseline
  alt text. Application version is v0.5.1.
- Comparable contract v1.0.0 defines canonical sale/lease data, decimal rate
  semantics, stable transaction identity, immutable source hashes, review
  provenance, and validation.
- Historical extraction now stages versioned records, commits only confirmed
  batches in SQLite transactions, deduplicates moved sources by content and
  comps by identity, and rejects sources changed after extraction.
- Reviewed comp search and CSV/workbook `comp_data` export are verified through
  a fictional historical-workbook vertical slice. Application version is
  v0.6.0. See `docs/COMPARABLE_INTELLIGENCE.md`.
- Assignment conclusions and compact income snapshots now use canonical
  identities, immutable source provenance, explicit review, transactional
  commit, reviewed-only search, and additive SQLite migrations. Standalone
  income Word files are no longer ignored. Application version is v0.7.0.
  See `docs/HISTORICAL_HARVESTING.md`.
- Rent-roll workbooks and normalized operating-expense tables now produce
  reviewed row-level records with assignment linkage, worksheet/row
  provenance, stable identities, transactional commit, search APIs, CLI
  search, and Streamlit review. Application version is v0.8.0.
- Recognized report sections now produce bounded market observations with
  effective date, geography, property type, paragraph-range provenance,
  explicit review/edit history, reviewed search, and transactional commit.
  Application version is v0.9.0.
- External and Office-embedded maps, charts, photos, sketches, and exhibits
  now produce searchable source-artifact records with binary/container hashes,
  dimensions, package locators, alternate duplicate provenance, explicit
  review, and changed-source rejection. Application version is v0.10.0.
- Basic wide multi-year operating statements now explode into canonical
  operating-expense lines, combining amount and per-square-foot columns by
  year/scenario while preserving worksheet row/column provenance. Application
  version is v0.10.1.
- Specialty Excel rent rolls now recognize mini-storage, mobile-home,
  apartment, and RV/site-style headers; tolerate worksheets with missing
  dimension metadata; and collapse duplicate master-list/category-sheet rows
  before review. Application version is v0.10.2.
- Native PDF rent-roll tables now produce canonical rent-roll entries with
  page/table/row provenance and reviewed commit/search behavior, while
  scanned/image-only PDFs remain reserved for a later OCR lane. Application
  version is v0.10.3.
- Native text-position accounting PDFs now produce canonical operating-expense
  lines after recognized expense sections, with period inference and
  page/line provenance. Application version is v0.10.4.
- Maps, building sketches, and photo blocks use documented assignment asset
  paths; validation identifies missing files and delivery embeds available
  JPG/PNG assets.
- Ownership history is generated as a table from the existing owner,
  transfer-history, and prior-price fields.
- Narrative generation honors `models.per_command`: drafting, adjustment
  justification, and reconciliation can use separate configured models.
- Field registry v1 contains 220 scalar fields and 24 pipeline blocks.
- Contract auditing detects unregistered workbook keys, template placeholders,
  assignment JSON keys, and pipeline blocks without handlers.
- New assignments record application/schema versions; delivery records the
  template filename and SHA-256 hash.
- Contract v1.1 derives lowercase property labels, lowercase value-interest
  text, title-case value words, and zoning table aliases from canonical facts.
- The canonical Intake workbook derives `VALUE_WORDS_FORMAL` visibly from
  `VALUE_WORDS`; legacy stored variants remain fallback-compatible.
- JSON freshness compares canonical Intake values directly; file timestamps no
  longer create false warnings after normal calculation work.
- Formula-cache validation is limited to workbook-owned keys still required
  after conditional report sections are removed.
- Cached Excel formula values are loaded with `openpyxl(data_only=True)`.
  Validation detects missing/error cached results, but cannot prove that a
  valid-looking cached value is fresh without an Excel-side calculation stamp.
- Blank workbook templates contain expected formula errors until required
  inputs are populated; these are existing model behaviors, not introduced by
  fictionalization.
- `README.txt` now reflects the current workbook name, invoice stage,
  validation command, comp marker, and draft-delivery behavior.
- Scanned/image-only rent-roll and operating-expense PDFs are no longer a
  dead end: an OCR lane (PyMuPDF rasterization + Tesseract, see
  `docs/OCR_LANE_DESIGN.md`) rasterizes each page, corrects orientation, and
  reuses the existing native-PDF table/expense matching logic against the
  OCR'd words. Every OCR-derived field is forced to `confidence: "low"` and
  flows through the same stage -> review -> commit gate as every other
  harvest record — no new commit path was introduced. Pages that OCR too
  poorly to trust (below ~40/100 average word confidence) are skipped with a
  warning instead of staging speculative rows. Streamlit's comp-review view
  shows the actual rendered page image inline for OCR-sourced rows so Derek
  can visually cross-check before confirming.
- Requires Tesseract OCR (a system binary, not a pip package) installed
  locally for the OCR lane to activate; if it's missing, extraction degrades
  to a clear warning instead of failing. This checkout now auto-detects
  `AXIOM_TESSERACT_CMD`, optional `config.json` OCR paths, and the normal
  Windows install path. English OCR data may be supplied by
  `AXIOM_TESSDATA_DIR`, optional `config.json`, or the ignored local
  `.local/tessdata` folder.
- A same-day follow-up hardening pass, prompted by a Fable-model review, added
  two more safeguards to the OCR rent-roll lane: an arithmetic cross-check per
  row (annual rent vs. monthly rent x12, rent/SF vs. annual rent / leased SF)
  that warns on likely OCR digit errors without dropping the row, and a
  warning whenever a page's OCR'd text has no recognizable rent-roll header
  at all (previously silent — the common case on continuation pages of
  multi-page rent rolls that don't repeat the header row).
- Seven tests cover the OCR lane: end-to-end scanned rent-roll extraction
  through commit, rotated-scan orientation recovery, illegible-scan bail-out,
  graceful degradation when Tesseract isn't installed, an arithmetic-mismatch
  warning case, a headerless-continuation-page warning case, and an
  orientation-scoring regression test that locks in preferring recovered
  financial rows over raw word count/confidence (the only one of the seven
  that doesn't require a real Tesseract install).
- A live archive rent-roll PDF supplied by Derek was tested at extraction
  level on 2026-07-09. Its original file had native table structure and used
  native extraction; a temporary image-only rendering of the same file
  exercised the OCR lane and produced low-confidence OCR rows plus a
  missing-header warning for a continuation page. Full staging/review against
  a naturally image-only scanned archive file remains pending.
- A live archive proforma PDF supplied by Derek was also tested at extraction
  level. Its original file used native text-position extraction and returned
  operating-expense lines. A temporary image-only rendering exposed an OCR
  orientation issue on landscape mixed rent/proforma layouts; OCR orientation
  selection now scores rotations by recovered financial rows before raw OCR
  confidence. The image-only proforma still shows resolution/layout
  sensitivity and remains a human-review case.
- A copied live archive folder was run through `comp-ingest` on 2026-07-09.
  The staged batch contained sale comps, lease comps, market observations,
  source artifacts, and a naturally image-only income statement that OCRed
  with good confidence but did not match current expense-section parsing
  rules. A simulated review/commit to a temporary database succeeded after
  normalizing placeholder lease-expiration values such as `N/A` to blank.
- A second copied archive batch with five assignment folders was run through
  `comp-ingest` on 2026-07-09. The staged JSON batches contain sale comps,
  lease comps, rent-roll rows, market observations, and source artifacts, and
  simulated review/commit into a temporary database succeeded for all five.
  This batch again produced no reviewable operating-expense rows, making
  non-standard/scanned income-statement expense extraction the next adapter
  target.
- The second copied archive batch was re-run after nested financial PDF
  routing and OCR batch-performance controls were added. The latest staged
  batches now include reviewable OCR-derived operating-expense rows from
  nested P&L PDFs, while comp/rent-roll/market observation totals remain
  consistent with the prior conservative run. Simulated review/commit to a
  temporary database succeeded; the real local database was not touched.
- OCR page-review images now honor an `AXIOM_OCR_PAGES_DIR` override and can
  be pruned of anything no longer referenced by an active staged/confirmed
  batch via `axiom.py ocr-cleanup` (manual, not automatic, so a page image is
  never deleted while still needed for review).
- Native-table and OCR rent-roll row extraction now share one code path
  (`_finalize_rent_roll_row`) for everything downstream of raw cell/column
  values, instead of duplicating anchor/total-row/as-of-date logic.
- The "OCR fields are always confidence=low" policy is enforced by a single
  `harvest_contract.enforce_ocr_low_confidence` helper rather than ad hoc
  string-prefix checks scattered across extractors; fixed a real gap this
  surfaced where OCR-derived statement-fallback expense rows could
  previously keep a `period_type` confidence of `medium`.
- Scanning an assignment folder now warns when more than one rent-roll or
  operating-statement PDF is found across subfolders (including nested
  "Information Provided"-style folders), naming each file's location and
  modified date so stale/duplicate copies can be checked before review.
- OCR orientation re-detection on later pages of a multi-page scan now also
  triggers when no financial structure is recognized at all, not only on low
  OCR confidence, closing a gap where a mixed-orientation scan bundle could
  silently lose a page's rows.
- Legacy `comps`/`lease_comps`/`assignments`/`income_snapshots` rows that
  predate the identity-key column now get one backfilled automatically on
  every `init_db()` call, so importing a real historical archive correctly
  recognizes already-ingested rows as duplicates instead of re-inserting
  them.
- A 2026-07-09 adversarial Fable-model stress test across three isolated
  sandbox mirrors (report generation/delivery, comp/financial ingestion +
  OCR, DB/ingest/commit + CLI misuse) found and fixed four low-risk
  hardening gaps: an opaque crash on illegal-XML field characters (now a
  clear named error), NaN/Infinity values silently corrupting rent/expense
  fields (now rejected to a clean "missing" value), and two ingest.py crashes
  on malformed staged/confirmed JSON or wrong-typed record fields (now clear
  skip/error messages instead of aborting the batch run). SQL-injection
  resistance and transactional-atomicity-under-kill were independently
  confirmed sound. A further set of design-level findings (rent-roll
  identity excluding dollar amount from dedupe, a silent zero-row "committed"
  batch, small-angle-skew and watermark OCR routing gaps, symlink
  folder-boundary escapes, a legacy-schema migration crash risk) were
  flagged for Derek's review rather than auto-fixed. See `HANDOFF.md`,
  "Completed this session (Claude, stress-test hardening — 2026-07-09)" for
  the full list.
- Two of those flagged findings were resolved the same day per Derek's
  explicit decision: rent-roll identity now includes the rent amount
  (`monthly_rent`/`annual_rent`), matching expense identity, so a mid-lease
  rent change no longer collapses into the prior rent during dedupe; and an
  unconfirmed comp/lease_comp inside an otherwise-confirmed batch now raises
  instead of silently skipping, matching every other harvest record type.
  See `HANDOFF.md`, "Completed this session (Claude, stress-test follow-up —
  2026-07-09)".
- **Phase 7 (AI narrative drafting) was live-tested end to end on
  2026-07-10, per Derek's explicit go-ahead, and confirmed working.** A real
  `ANTHROPIC_API_KEY` on Derek's own machine (not this sandbox — see "Known
  limitations") ran `python axiom.py deliver DEMO-001 --draft` and generated
  real prose for all 6 narrative blocks. `MARKET_AREA_OVERVIEW` and
  `CAP_RATE_NARRATIVE` produced polished, submarket-specific USPAP-style
  prose. The other three (`SCA_ADJUSTMENT_NARRATIVE`, `SCA_CONCLUSION_NARRATIVE`,
  `RECONCILIATION_NARRATIVE`) correctly refused to fabricate numbers because
  DEMO-001's underlying pre-Phase-6 adjustment/valuation data contains real
  unresolved Excel formula errors (`#DIV/0!`, `#VALUE!`) and a $0 concluded
  value — the expected, already-documented gap this same fixture shows
  elsewhere, not a new bug. The model's refusal was the correct behavior for
  a signed deliverable, but its raw meta-commentary ("I must flag a data
  issue before providing the narrative...") was being injected into the
  document verbatim. `narrative_generator.py` now pre-checks each
  data-dependent narrative's key inputs (Excel error tokens, or a
  currency-like value that's zero/negative) *before* calling the API; when
  bad data is detected the API call is skipped entirely (no wasted cost) and
  a clean `[Pending — <reason>. ...]` placeholder is injected instead.
  16 new tests in `tests/test_narrative_data_guard.py` cover the error-token
  detection, money parsing, per-narrative field checks, the
  developed-approach-aware reconciliation check, and an end-to-end case
  proving the Claude API is never called when the guard fires.

## Data-safety status

- The project data was confirmed to be dummy data and fictionalized on
  2026-07-01.
- Client, contact, owner, subject, comparable, tenant, utility, legal, FEMA,
  and file-number examples now use the `DEMO-001` identity.
- Word author/revision metadata was scrubbed from project DOCX files.
- Axiom branding, business contact information, and appraiser credentials were
  intentionally retained because they belong to the product owner, not the
  demo assignment.
- `.gitignore` now excludes assignments, credentials, local databases, ingest
  work areas, generated dashboards, caches, and Office lock files.
- Source Office artifacts passed structural package checks after
  fictionalization. LibreOffice was unavailable, so DOCX visual rendering
  could not be completed in this environment.

## Current priorities

### P0 — Delivery integrity

1. **Completed:** add non-mutating `axiom.py validate <file_no>`.
2. **Completed:** distinguish ordinary required fields, pipeline-handled
   blocks, and unsupported/unresolved blocks.
3. **Completed:** refuse final delivery unless validation passes; provide an
   explicit `--draft` path with a distinct output filename.
4. **Completed:** record validation, input, placeholder, and generation
   failures without overwriting prior output or delivered state.

### P0 — Safe repository baseline

1. **Completed:** create a dedicated Git repository in this code root.
2. **Completed:** privacy scan and fictionalization of source Office artifacts.
3. **Completed:** create the initial source commit with Git LFS tracking Office
   artifacts.

### P1 — Repeatable testing

1. **Completed:** build a genuinely fictional fixture under `tests/fixtures/`.
2. **Completed for comp and media insertion:** add representative fictional
   comp rows, reproducible synthetic media, and end-to-end block tests. Visual
   formatting review remains.
3. **Completed for adversarial structural behavior:** add temporary-assignment
   torture tests covering malformed, extreme, interrupted, and path-safety
   cases.
4. **Completed:** add a metadata-normalized structural DOCX golden comparison.
   Desktop Word visual comparison remains.

### P1 — Data contract

1. **Completed:** introduce a versioned field registry/schema independent of
   Word templates.
2. **Completed for six deterministic variants:** derive presentation variants
   rather than entering duplicate facts. Semantically distinct short/full
   labels remain explicit.
3. **Completed for canonical Intake drift and missing/error caches:** detect
   stale JSON and scope cache checks to active workbook-owned report fields.
   Valid-but-stale cache proof still requires an Excel-side calculation stamp.
4. **Completed for new assignments and delivery attempts:** record template,
   schema, and application versions per assignment.

### P1 — Comparable intelligence

1. **Completed:** define canonical sale/lease record contract, provenance,
   review status, identity, and database idempotency.
2. **Completed:** verify fictional extract → stage → review → commit → search →
   CSV/workbook export.
3. **Completed:** extend provenance/review to assignment conclusions and
   compact income snapshots.
4. **Completed:** extend the model to row-level rent rolls, specialty Excel
   rent-roll layouts, native PDF rent-roll tables, native text-position PDF
   expenses, normalized operating expenses, and basic wide multi-year
   operating statements.
5. **Completed:** extend the model to bounded reusable market observations.
6. **Completed:** extend the model to external and Office-embedded charts,
   maps, photos, sketches, and archived exhibits.
7. **Completed:** add database migrations/backfills for any legacy local
   comp rows before importing a real historical archive
   (`backfill_legacy_identities` in `db.py`, run automatically by
   `init_db()`).
8. **Completed for manual visual reference:** add nullable comp/lease-comp
   links to `source_artifacts`, manually attach local JPG/PNG photos to a
   selected sale or lease comp from the Browse tab, and show attached-photo
   thumbnails in that same Browse view. Automated photo-to-comp extraction
   remains deferred pending real archive layout review.
9. **Completed for staged review prep:** add a non-mutating staged-comp review
   packet builder and run a current-code staging pass against the copied
   archive folders under `scratch/`, producing a latest-batch sale/lease CSV
   for human review before any real database commit.

### P2 — Integrations

Live-test Adobe Sign and Xero only after the core workflow has delivery
integrity. External actions must be idempotent and retain provider IDs,
timestamps, and failure states.

## Known external blockers

- Adobe Sign requires a usable API application and local credentials.
- Xero requires a configured custom connection and local credentials.
- AI narrative generation requires the Anthropic package, network access, and
  `ANTHROPIC_API_KEY` — confirmed working end to end on 2026-07-10 (see
  "Verified baseline" above). Note: this cloud sandbox's own network routes
  through an intercepting proxy that blocks/misrepresents calls to
  `api.anthropic.com`, so live AI narrative testing must happen on Derek's
  own machine, not in this sandbox.
