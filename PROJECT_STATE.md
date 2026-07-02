# Axiom Platform — Project State

- Last verified: 2026-07-01
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
3. Python orchestration
   - `axiom.py`: assignment commands and dashboard
   - `fill_engine.py`: Word substitution and conditional removal
   - `comp_builder.py`: comparable-sale page injection
   - `narrative_generator.py`: Anthropic-backed narrative drafting
   - `db.py`, `extractor.py`, `ingest.py`: comp extraction/review/database
   - `axiom_ui.py`, `comp_review.py`: Streamlit interfaces
4. Local integrations
   - `adobe_sign.py`: Acrobat Sign OAuth client
   - `xero_client.py`: Xero custom-connection client

## Verified commands

| Command | Current behavior |
|---|---|
| `new` | Creates an assignment folder, workbook copy, output folder, and `.axiom.json` state |
| `engage` | Locally generates engagement letter, document request, and invoice |
| `deliver` | Generates a final report only after validation passes; `--draft` generates a distinctly named draft without changing delivery stage |
| `validate` | Checks fields, block handlers, workbook formula caches, and possible JSON staleness without changing assignment files or state |
| `dilmore` | Writes size-adjustment calculations into the assignment workbook |
| `extract` | Extracts comparable and narrative data from supported source documents |
| `list` / `status` | Reads assignment metadata and files |
| `dashboard` | Regenerates a local HTML assignment dashboard |

Important: `engage` does not currently transmit documents. Adobe Sign and Xero
are separate modules and are not wired into the command workflow.

## Verified baseline

Checks were performed without regenerating or modifying assignment outputs.

- The CLI imports and displays help using Python 3.13 from the Codex bundled
  runtime.
- Five automated validation and delivery-state tests pass.
- The platform folder arrived without dedicated Git history. A dedicated
  repository is initialized and the first commit is staged.
- The live assignment directory now contains one clearly labeled fictional
  assignment: `DEMO-001_Northstar_Example_Holdings`.
- `tests/fixtures/DEMO-001` is the approved source-controlled regression
  fixture.
- Fixture validation reports 0 ordinary missing keys and 18 unresolved block
  placeholders.
- Dashboard readiness now counts ordinary missing fields and unresolved blocks.
- Final delivery now stops before generation when validation fails.
- Draft generation remains available through explicit `--draft` and does not
  change delivery stage.
- Final output is scanned after comp and narrative injection; remaining
  placeholders prevent the delivered-state transition.
- Delivery attempts record status and blocker count while preserving the
  previous assignment stage on failure.
- Narrative model routing reads the wrong configuration level. It falls back to
  `claude-sonnet-4-6` rather than honoring `models.per_command`.
- Cached Excel formula values are loaded with `openpyxl(data_only=True)`.
  Validation warns when the JSON predates the workbook, but that file-level
  heuristic cannot distinguish Intake edits from normal calculation work.
- Blank workbook templates contain expected formula errors until required
  inputs are populated; these are existing model behaviors, not introduced by
  fictionalization.
- `README.txt` now reflects the current workbook name, invoice stage,
  validation command, comp marker, and draft-delivery behavior.

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
4. **Completed for validation/placeholder failures:** record attempt status and
   blocker count without overwriting delivered state. Exception-path hardening
   remains future work.

### P0 — Safe repository baseline

1. **Completed:** create a dedicated Git repository in this code root.
2. **Completed:** privacy scan and fictionalization of source Office artifacts.
3. Create the staged initial source commit.

### P1 — Repeatable testing

1. **Completed:** build a genuinely fictional fixture under `tests/fixtures/`.
2. Add tests for placeholder coverage, section removal, comp insertion,
   formatting, state transitions, and failure behavior.
3. Add a golden-output or structural DOCX comparison that ignores unstable
   package metadata.

### P1 — Data contract

1. Introduce a versioned field registry/schema independent of Word templates.
2. Derive presentation variants rather than entering duplicate facts.
3. Detect stale JSON and stale Excel calculation caches.
4. Record template, schema, and application versions per assignment.

### P2 — Integrations

Live-test Adobe Sign and Xero only after the core workflow has delivery
integrity. External actions must be idempotent and retain provider IDs,
timestamps, and failure states.

## Known external blockers

- Adobe Sign requires a usable API application and local credentials.
- Xero requires a configured custom connection and local credentials.
- AI narrative generation requires the Anthropic package, network access, and
  `ANTHROPIC_API_KEY`.
