# Current Handoff

- Last updated: 2026-07-01
- Current agent: Codex
- Last commit: Comparable intelligence vertical-slice checkpoint (the commit containing
  this handoff; use `git log -1 --oneline` for its immutable hash).

## Current objective

Maintain a safe Claude ↔ Codex handoff baseline and close the report-generation
blocks before connecting external services.

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

## In progress

- Comparable intelligence vertical slice is ready for a source checkpoint.

## Exact next step

Extend the canonical harvesting model to assignment conclusions and income
snapshots, then to rent rolls/expenses and reusable narrative/chart artifacts.

## Baseline checks run

- `python -m unittest discover -s tests -v`: 47 tests passed.
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

## Known limitations

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
