# Current Handoff

- Last updated: 2026-07-01
- Current agent: Codex
- Last commit: `b8a309d` — Establish safe Axiom platform baseline.

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

## In progress

- Media and structured-block handlers are ready for a source checkpoint.

## Exact next step

Fix narrative model routing, then define the versioned field/data contract.
Fixture media and comp rows should be added when representative fictional
assets are available.

## Baseline checks run

- `python -m unittest discover -s tests -v`: 7 tests passed.
- `axiom.py --help`: passed with the warning corrected.
- `DEMO-001` fixture validation: 0 ordinary missing fields and 17 unresolved
  blocks (eight missing media inputs, eight AI narratives, and comp data).
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
- The existing parent-folder `PROJECT_STATE.md` is historical and contains
  stale claims. This file and the project-root `PROJECT_STATE.md` are the
  canonical handoff documents going forward.
