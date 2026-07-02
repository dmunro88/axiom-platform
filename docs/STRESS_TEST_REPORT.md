# Stress-Test Report

- Date: 2026-07-01
- Scope: local, deterministic testing against temporary fictional assignments
- External systems: not called
- Result: 41 automated tests pass, including 21 torture cases and 2 complete
  generated-report golden checks

## What was attacked

- blank, null, zero, false, malformed JSON, and malformed XLSX inputs;
- Boolean conditional-section flags and approximately 64,000 characters of
  Unicode report text;
- placeholders split across Word runs in the body, header, contract inventory,
  and comparable-page template;
- corrupt and oversized images, plus 50-photo insertion;
- duplicate, incomplete, and 50-row comparable datasets;
- path-like file numbers, unsafe client-name characters, and file-number prefix
  collisions;
- interrupted generation and a simulated locked existing output file.
- missing engagement templates and interrupted engagement generation.

## Defects found and hardened

1. Required blank/null values could disappear without a validation blocker.
2. Optional blank assumptions were not explicitly represented in the contract.
3. Split-run placeholders could evade final DOCX and contract scanning.
4. Split-run placeholders in the comp template were not replaced.
5. Corrupt image files passed readiness checks and failed during generation.
6. Oversized image files had no preflight limit.
7. A generation exception could overwrite a previously reviewed report.
8. Malformed inputs in draft mode could escape the validation boundary.
9. Path-like file numbers and client names could create unsafe paths.
10. Prefix matching could select the wrong assignment.
11. Duplicate or incomplete comp rows could be treated as deliverable.
12. Non-string conditional flags could crash section processing.
13. Missing engagement templates could still mark an assignment engaged.
14. Engagement generation wrote directly over prior documents.
15. Cloned comp-template images retained source relationship IDs and resolved
    to `settings.xml` instead of image parts.
16. Cloned comp drawings reused duplicate Word drawing IDs.
17. All generated-report images lacked baseline alt text.

Engagement and delivery now generate in same-directory temporary files and
replace prior output only after generation steps succeed. Failures preserve
prior documents, preserve assignment stage, clean temporary files, and record
an actionable failure status.

## Current enforced limits and rules

- File numbers are 1–64 ASCII letters, numbers, dots, hyphens, or underscores;
  path-like and `..` values are rejected.
- Client names are converted to safe filename components.
- Each report image must be readable and no larger than 25 MB.
- Comparable numbers must be unique; every comp needs an address and sale
  price.
- `EXTRAORDINARY_ASSUMPTION` and `HYPOTHETICAL_CONDITION` are explicitly
  optional blank fields under contract v1.2.0.

## Not proven by this run

- Visual fidelity in desktop Microsoft Word; package structure was exercised,
  but LibreOffice/Word rendering is unavailable in this environment.
- Adobe Sign, Xero, Anthropic, network, authentication, and retry behavior.
- Semantic quality of AI narratives or appraisal conclusions.
- Freshness of valid-looking Excel formula caches without an Excel-side
  calculation stamp.
- Performance beyond 50 comps, 50 photos, and the tested long-text case.

## Follow-up generated-report QA

A complete deterministic report was assembled from `DEMO-001`, including
three comp pages, eleven fixture images, ownership history, deterministic
narratives, and safe formula overrides.

- Metadata-normalized package/text/style/media/relationship geometry is stored
  in `tests/golden/demo_report_structure.json`.
- After an intentional template/layout change, regenerate it with
  `python scripts/update_demo_report_golden.py` and review the JSON diff before
  committing.
- The golden test verifies package CRCs, normalized OOXML hashes, relationships,
  media hashes, paragraph/style counts, tables, shapes, page breaks, and
  sections.
- All 40 inline drawings now have unique IDs, valid image relationships, and
  nonblank alt text.
- Accessibility high-severity findings fell from 40 to 0.
- Sixty-five medium table-header findings remain. Many report tables are
  key-value or layout constructs rather than row/column datasets, so automatic
  first-row marking was intentionally not applied without visual Word QA.
- The style audit found extensive direct formatting inherited from the branded
  template. It was not normalized because doing so could erase intentional
  design choices without a renderer available.
