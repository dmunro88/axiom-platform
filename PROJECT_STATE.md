# Axiom Platform — Project State

- Last verified: 2026-07-09
- Status: Functional prototype in active local use; production safeguards and
  repeatable tests are incomplete.

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
   - `axiom_ui.py`, `comp_review.py`: Streamlit interfaces
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
| `dilmore` | Writes size-adjustment calculations into the assignment workbook |
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

- The CLI imports and displays help using Python 3.13 from the Codex bundled
  runtime.
- Seventy-seven automated validation, delivery-state, stress, golden-DOCX,
  comparable, historical-harvest, media, comp-page,
  structured-block, model-routing, contract, presentation-derivation, and
  OCR-lane tests pass, confirmed live with `python -m unittest discover -s
  tests -v` in this checkout. As of 2026-07-09, the seven OCR tests run
  against a real local Tesseract install instead of being skipped (one of the
  seven, the orientation-scoring test, doesn't require Tesseract at all). The
  suite currently contains 77 tests after adding OCR orientation-scoring
  coverage, placeholder lease-expiration normalization, nested financial PDF
  routing, and statement expense fallback coverage.
- The platform folder arrived without dedicated Git history. A dedicated
  repository is initialized with a safe baseline commit.
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
- Field registry v1 contains 220 scalar fields and 20 pipeline blocks.
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
7. Add database migrations/backfills for any legacy local comp rows before
   importing a real historical archive.

### P2 — Integrations

Live-test Adobe Sign and Xero only after the core workflow has delivery
integrity. External actions must be idempotent and retain provider IDs,
timestamps, and failure states.

## Known external blockers

- Adobe Sign requires a usable API application and local credentials.
- Xero requires a configured custom connection and local credentials.
- AI narrative generation requires the Anthropic package, network access, and
  `ANTHROPIC_API_KEY`.
