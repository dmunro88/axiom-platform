# Current Handoff

- Last updated: 2026-07-13
- Current agent: Codex
- **Codex progress after the planning handoff (2026-07-13): Track 1's
  manual comp-photo foundation is built.**
  `source_artifacts` has nullable `comp_id`/`lease_comp_id` link columns and
  indexes; `db.py` has `insert_manual_comp_photo()` and
  `comp_photo_artifacts()` helpers with duplicate protection by comp id +
  image hash; `search_source_artifacts()` can filter by those new links; and
  `comp_review.py`'s Browse tab can upload a JPG/PNG, copy it into ignored
  local storage (`.local/comp_media`), link it directly to the selected sale
  or lease comp, and show thumbnails for comps with attached photos. Focused
  verification passed with bundled Python: `py_compile` for edited files,
  `unittest tests.test_artifact_harvest tests.test_comp_pipeline` (17 tests),
  and `axiom.py contract` (v1.2.0/220/24). `pytest` was not available in the
  bundled Python environment, so the affected test modules were run through
  `unittest` instead.
- **Codex next-step progress (2026-07-13): copied-archive staging was rerun
  with current code and a review packet was generated.** `axiom.py
  comp-ingest scratch\historical_ingest_test_2` completed for five copied
  archive assignments, and `axiom.py comp-ingest scratch\historical_ingest_test`
  completed for the remaining 25C008 copied assignment. Added
  `scripts/build_staged_comp_review_packet.py`, which reads `ingest/staged`,
  selects the newest staged JSON per assignment folder, and writes
  `scratch/staged_comp_review/latest_sale_lease_comp_review.csv` plus `.md`
  without confirming records, moving staged files, or writing `axiom.db`.
  The current packet has 6 latest staged batches and 95 sale/lease rows
  (57 sale, 38 lease) with zero hard comparable validation errors. Older
  duplicate staged JSON files still exist in `ingest/staged`; the packet
  names the exact latest files to use. No `review-staged`/`comp-commit` was
  run.
- **Real local database constructed schema-only (2026-07-13).** Per Derek's
  direction not to use copied/test/build data for the real database, Codex ran
  `db.py` and initialized `axiom.db` with the current schema only. Verified
  all application tables have 0 rows, `source_artifacts` includes
  `comp_id`/`lease_comp_id`, and `axiom.py comp-search --city Demo` returns
  0 reviewed sale comps. No staged archive data was committed.
- **Track 2 UI/UX consolidation started (2026-07-13).** Replaced the old
  single long `axiom_ui.py` page with a five-view Streamlit workbench:
  Dashboard, Assignment Workflow, Comp Library, Search, and System. The new
  shell keeps commands backed by `axiom.py`, adds visible access to
  `validate`, draft delivery, `contract`, dashboard generation, database
  counts, reviewed comp/financial/observation/artifact searches, and keeps
  the existing `comp_review.py` module as the Comp Library page. Also updated
  `start_axiom_ui.bat` to install from `requirements.txt` instead of an old
  partial package list. Verified with bundled Python `py_compile` for
  `axiom_ui.py`/`comp_review.py`, `axiom.py contract`, and `git diff --check`.
  Live Streamlit/browser QA is pending because the bundled Codex Python used
  in this session does not have Streamlit installed.
- **Manual sale/lease comp entry added to the UI (2026-07-13).**
  `axiom_ui.py` now exposes a top-level Manual Comp Entry sidebar view, and
  `comp_review.py` also keeps Manual Entry as the first Comp Library tab, with
  sale and lease forms for direct typed-in comps. `db.py` inserts those
  records as confirmed manual comparables after canonical normalization,
  required-field validation, identity-key generation, and duplicate detection,
  so they immediately appear in the existing reviewed comp Browse/Search
  paths. Verified with bundled Python `py_compile`, `unittest
  tests.test_comp_pipeline` (12 tests), `axiom.py contract`, and
  `git diff --check`.
- **Manual comp calculation/validation layer started (2026-07-13).**
  Added `manual_comp_model.py` with controlled property type/dropdown
  constants, expanded manual normalization, sale indicators (price/SF, price/
  acre, FAR, land-to-building ratio, PGIM/EGIM, cap rate, NOI/SF/unit, etc.),
  lease indicators (annual/monthly rent, rent/SF, term, concessions, effective
  rent), and draft/confirmed validation for hard requirements versus warnings.
  Added `tests/test_manual_comp_model.py`; verified with bundled Python
  `py_compile`, `unittest tests.test_comp_pipeline tests.test_manual_comp_model`
  (18 tests), `axiom.py contract`, and `git diff --check`. The Streamlit UI has
  not yet been redesigned to consume this layer.
- **This session (2026-07-13) found and fixed a real defect that had been
  sitting undetected in git history since 2026-07-09/07-10: `ingest.py` and
  `narrative_generator.py` (plus `.gitignore`, this file, `PROJECT_STATE.md`,
  and `docs/ADJUSTMENT_GRID_DESIGN.md`) were committed with content
  truncated mid-statement — the same known bash/OneDrive large-file-truncation
  bug documented elsewhere in this file, except this time it landed in a
  commit instead of just a working-tree edit. `ingest.py`'s committed version
  literally raised `SyntaxError` if compiled as-is (cut off mid multi-byte
  comment character); it had been broken this way across several commits
  with nobody catching it. Fixed by committing the working tree's
  already-correct content — commit `a646c51`. Also added the
  previously-untracked one-line `CLAUDE.md` (`@AGENTS.md` include, needed for
  Claude Code to load project instructions) as `e476235`, and deleted 10
  orphaned scratch/duplicate files left over from the round-4 fix session's
  OneDrive edit-verify workaround (`axiom_fixed_r4.py`, `axiom_r4b.py`,
  `adjustment_grid_fixed_r4.py`, `comp_library_fixed_r4.py`, and six
  similarly-named test files) after confirming each was byte-identical to or
  superseded by content already in the real tracked files. See "Completed
  this session (Claude, git-integrity fix — 2026-07-13)" below for full
  detail.**
- Earlier the same day (2026-07-13), Phase 6 hardening round-4 findings
  (Q1-Q9) were fixed and committed as `8f08aa6` — see "Completed this session
  (Claude, Phase 6 hardening rounds 1-4 — 2026-07-11)" below, specifically
  its "Round 4 fixes — completed 2026-07-13" note. No round-5 Fable review
  has been spawned — don't spawn one without checking with Derek first
  (usage-consumption concern he's raised previously).
- **This session also ran the full test suite live to confirm none of the
  above broke anything, on a genuinely different environment than prior
  sessions: Derek's own real Windows machine (`python` from a system
  install), not the prior cloud sandbox.** That surfaced two environment
  gaps, both now closed:
  - This repo had zero dependency manifest of any kind. `pdfplumber`
    (a hard, unguarded import in `pdf_financial_extractor.py`) and
    `reportlab` (used only to build test PDF fixtures) weren't installed
    and had to be `pip install`ed before tests could even collect.
  - Once collecting, 148 passed / 1 failed / 6 skipped. The 1 failure
    (`test_narrative_data_guard.py::test_broken_sca_conclusion_data_skips_api_call`,
    pre-existing since commit `dce5d9d`, 2026-07-10 — not something this
    session's other changes touched) hardcoded a POSIX `Path("/tmp/...")`
    for a scratch file, which isn't a real writable path on Windows. Fixed
    with `tempfile.gettempdir()` instead — commit `2623a2a`.
  - The 6 skips were the real-Tesseract OCR tests in
    `test_financial_harvest.py`, needing `PyMuPDF`/`pytesseract` (not yet
    installed on this machine) plus a working local Tesseract — which,
    handily, was already installed from an earlier session on this same
    machine, English tessdata included (`.local/tessdata/eng.traineddata`).
    Installed the two missing pip packages and all 6 now pass against the
    real local Tesseract 5.5.0 install.
  - Wrote `requirements.txt` (commit `30469b6`) pinning all 10 actual
    third-party dependencies (core runtime, the optional OCR lane, and
    test-only fixture generation) to the versions just verified working,
    so the next fresh environment doesn't have to rediscover any of this
    by trial and error.
  - **Final state: 155 passed, 0 skipped, 16 subtests passed**, plus
    `python axiom.py contract` clean at v1.2.0/220/24.
- **This repo now has a GitHub remote.** Derek created
  `https://github.com/dmunro88/axiom-platform` (private) and had it added as
  `origin`; pushed through `7053cac` with his explicit go-ahead. This was
  the first push ever for this repo (previously local-only).
- **Separately, normalized 15 Office template/workbook files to real Git LFS
  pointers** (commit `b63d4f5`, **not yet pushed**). `.gitattributes` has
  routed `*.docx`/`*.xlsx` through the LFS clean filter since the baseline
  commit, but these 15 files had been committed as full binary blobs
  directly in git history instead — the exact mismatch Codex flagged
  2026-07-09 as needing a deliberate decision (`git lfs ls-files` showed
  zero real LFS pointers in `HEAD` before this fix). Working tree content
  is byte-identical before/after; only what git stores changed. Does not
  rewrite prior commits — old history still carries the full binaries, so
  this only stops the mismatch recurring going forward. Re-verified full
  suite (155 passed) and `python axiom.py contract` green after.
- **Planning-only discussion, no code written:** talked through the
  broader roadmap with Derek (he supplied the actual master roadmap file,
  `axiom_platform_roadmap_status.html`, which lives outside this repo and
  is stale — it still badges Phases 5.5/6/7 as "next" when they're
  actually done) and agreed a concrete two-track plan for next session.
  **See "Current objective" below for the full plan** — do not re-derive
  it from scratch, it's already scoped.
- Commits this session (2026-07-13): `8f08aa6` (round-4 Q1-Q9 fixes),
  `a646c51` (git-integrity/truncation fix), `e476235` (add `CLAUDE.md`),
  `e6d41e4` (HANDOFF.md update), `d9e9b07` (PROJECT_STATE.md update),
  `2623a2a` (fix `/tmp` test portability bug), `30469b6` (add
  `requirements.txt`), `7053cac` (PROJECT_STATE.md update, pushed),
  `b63d4f5` (LFS normalization, **not yet pushed** — ask Derek before
  pushing, don't assume standing approval from the earlier push).
- Commits from the 2026-07-11 session: `9d198a5` (round 1, findings A1-A5),
  `9026f2e` (round 2, findings N1 + residuals of A1/A3/A5), `4db2456`
  (round 3, findings P1-P4). Full details in "Completed this session
  (Claude, Phase 6 hardening rounds 1-4 — 2026-07-11)" below.
- Commits from the prior (2026-07-10) session: `2e124a1` — Phase 6 Adjustment Grid steps 5-6
  (`adjustment_grid.py` injector module, `field_registry.py` wiring, the 4
  new template markers, `axiom.py` deliver-stage wiring, and the unrelated
  `REPORT_TYPE` Intake-row template fix found along the way), plus a
  follow-up docs commit `6df37ef`. See "Completed this session (Claude,
  Phase 6 completion — 2026-07-10)" below. This closes out Phase 6 entirely
  — steps 1-2 and step 4 were completed and committed in an earlier
  2026-07-10 session as `84fb3e5` and prior commits. Older commits: `e05721b`
  — see "Completed this session (Claude, stress-test hardening —
  2026-07-09)" below for the adversarial stress-test pass and its four
  auto-fixed, low-risk hardening changes. A same-day follow-up commit
  `8400e01` resolves two of that pass's flagged judgment-call items per
  Derek's explicit direction: rent-roll identity now includes the rent
  amount (matching expense identity), and an unconfirmed comp/lease_comp
  inside a confirmed batch now raises instead of silently skipping (matching
  every other harvest record type) — see "Completed this session (Claude,
  stress-test follow-up — 2026-07-09)" below. Prior commit `6ad25af` — see
  "Completed this session (Claude, hardening pass — 2026-07-08)". Prior to
  that, `dde13b8` covered Codex's 2026-07-09 work plus the review-pass fixes
  described under "Completed this session (Claude, review pass —
  2026-07-08)". Not pushed to any remote.
- `docs/ADJUSTMENT_GRID_DESIGN.md` (2026-07-09/10): scoped Phase 6 design,
  adversarially reviewed via Fable (found and fixed two blocking gaps — the
  existing `land` tab's dependency in `narrative_generator.py`, and the
  then-broken `cmd_dilmore` command). **All 6 pipeline steps in this design
  doc are now built and committed as of 2026-07-10 — Phase 6 is complete,**
  not just scoped.
- **Phase 7 (AI narrative drafting) live-tested end to end (2026-07-10), per
  Derek's explicit go-ahead — confirmed working.** This sandbox has no
  `ANTHROPIC_API_KEY` and its own network intercepts calls to
  `api.anthropic.com` through a MITM proxy (`O=GoProxy untrusted MITM proxy
  Inc`) that returns a generic "Unauthorized" regardless of key validity —
  wasted real time chasing that as a bad-key problem before the TLS
  certificate subject line gave it away. The real test had to run on
  Derek's own machine instead, where `python axiom.py deliver DEMO-001
  --draft` generated real prose for all 6 narrative blocks.
  `MARKET_AREA_OVERVIEW` and `CAP_RATE_NARRATIVE` came back polished and
  submarket-specific. The other three (`SCA_ADJUSTMENT_NARRATIVE`,
  `SCA_CONCLUSION_NARRATIVE`, `RECONCILIATION_NARRATIVE`) correctly refused
  to fabricate numbers, because DEMO-001's pre-Phase-6 adjustment/valuation
  data has real unresolved Excel errors (`#DIV/0!`, `#VALUE!`) and a $0
  concluded value — the same already-documented gap this fixture shows
  elsewhere (see Phase 3.5/Phase 6 roadmap notes), not a new bug. That
  refusal is the *correct* behavior for a signed deliverable, but the raw
  refusal text ("I must flag a data issue before providing the
  narrative...") was getting injected into the document verbatim, reading
  like a chatbot transcript rather than a draft placeholder. Fixed:
  `narrative_generator.py` now pre-checks each data-dependent narrative's
  key inputs for Excel error tokens or a zero/negative currency value
  *before* calling the API (`_has_error_token`, `_parse_money`,
  `_fields_data_issue`, `_reconciliation_data_issue` — the last one mirrors
  `_prompt_reconciliation`'s own developed/not-developed logic so it only
  checks values for approaches actually marked developed). When bad data is
  detected, the API call is skipped entirely (saves cost too) and a clean
  `[Pending — <reason>. ...]` placeholder is injected instead. 16 new tests
  in `tests/test_narrative_data_guard.py`, including an end-to-end case that
  mocks `_call_claude` and asserts it's never invoked when the guard fires.
  Re-verified live against the real DEMO-001 assignment in this sandbox
  (without a key, which only proves the *guard* path — the other 3 blocks
  still correctly error on the missing key as before): all three broken-data
  blocks now show the clean placeholder text instead of a raw refusal.
- **`cmd_dilmore` fixed (2026-07-10), per Derek's explicit go-ahead.** It
  used to call `dilmore_factor`/`dilmore_adj_pct` with 3 positional args
  (`subject_gba, comp_gba, curve`) against their real 2-arg `(ratio,
  curve)` signature — `TypeError` on every real run — and had the ratio
  backwards. Now calls the existing `dilmore_summary(subject_gba,
  comp_gbas, curve)` helper directly instead of re-deriving the same math
  inline. An invalid `size_adj!B3` curve now fails loudly with no partial
  write, instead of a raw traceback. Two new regression tests in
  `tests/test_torture.py` (this command had zero coverage before):
  `test_dilmore_uses_correct_ratio_direction_and_signature` (a comp 2x
  subject size gets a positive adjustment, a comp half subject size gets
  a negative one, matching `dilmore_factor`/`dilmore_adj_pct` computed
  directly) and `test_dilmore_invalid_curve_fails_loudly_without_writing`.
  Verified: `tests/test_torture.py` 23/23 (32 incl. subtests), plus
  `test_comp_pipeline.py`/`test_docx_golden.py`/`test_historical_harvest.py`/
  `test_observation_harvest.py`/`test_validation.py`/`test_artifact_harvest.py`
  (40/40) and `test_financial_harvest.py`'s non-OCR tests (14/14) all green;
  `python axiom.py contract` clean at v1.2.0/220/20. OCR-specific tests in
  `test_financial_harvest.py` weren't touched by this change and were only
  partially re-run (they're slow with a real Tesseract install and hit this
  environment's command time cap) — no failures observed in the portion
  that did run.

- **Follow-up self-correction to the `cmd_dilmore` fix above, same day
  (2026-07-10), found while grounding Phase 6 work in the real template.**
  Direct openpyxl inspection of the real `templates/workbook.xlsx` `size_adj`
  tab's header row (A=Comp, B=Comp GBA, C=Ratio (Ac/As) — a pre-existing
  per-row formula, D=Size Factor, E=Adj %, F=Adj $/SF, G=Notes) showed the
  fix above wrote Size Factor/Adj % to columns 3/4 (C/D) instead of the real
  4/5 (D/E) — silently overwriting column C's live Ratio formula on any real
  run. It passed the original tests only because those tests' fixture
  invented its own (wrong) column layout instead of mirroring the real
  template. Fixed in `axiom.py` (now writes columns 4/5) and
  `tests/test_torture.py` (fixture now mirrors the real header row and a
  real Ratio formula, and asserts column C survives untouched — the actual
  regression-catching mechanism for this bug class). Committed as `746a172`.
  Also found and worked around a real sandbox gotcha along the way: pytest
  keeps its own separate assertion-rewrite bytecode cache
  (`__pycache__/*-pytest-*.pyc`), distinct from the plain `.pyc` cache —
  neither `-B`, `PYTHONDONTWRITEBYTECODE=1`, nor `-p no:cacheprovider`
  touch it, so a stale one can make pytest silently keep testing an old
  version of a file's assertions even though the source on disk is current
  and `py_compile` is clean. `rm -rf __pycache__` fails on this OneDrive
  mount ("Operation not permitted", same unlink restriction as git
  internals) but `mv __pycache__ __pycache__.stale.<ts>` succeeds and fixes
  it — same workaround pattern documented for git's own lock/temp files.
  Separately, `git diff`/`git status` initially reported zero difference
  for `axiom.py`/`test_torture.py` despite the working tree genuinely
  differing from HEAD (confirmed via `git hash-object` vs `git rev-parse
  HEAD:<path>`) — a poisoned stat-cache on this same mount (see
  `feedback_onedrive_bash_sync_lag` in Claude's memory); `touch <file> &&
  git update-index --refresh` forced git to recheck actual content and
  fixed it.

## Current objective

Update from Codex, 2026-07-13: Track 1 items 2-4 below are now built, and the
real local `axiom.db` now exists as a schema-only database with zero rows. Per
Derek's direction, copied/test/build data was not committed to it. The copied
archive staged queue has also been refreshed with current code and summarized
in `scratch/staged_comp_review/latest_sale_lease_comp_review.csv`; this is
review prep only, not a database commit.

The OCR lane, Phase 6 (Adjustment Grid, all four hardening rounds), and
Phase 7 (AI narrative drafting) are all complete and live-tested. Two new
tracks were scoped with Derek on 2026-07-13 (planning only, nothing built
yet — picking this up after a usage-limit reset) and are the next work,
in this order:

**Track 1 — Comp database: real data + visual reference (agreed priority,
start here).**
Current status: the database file has now been constructed empty; copied
archive data remains staged/review-packet-only and has not been committed.
1. The real local comp database (`axiom.db`) now exists as an empty
   schema-only database. Every comp-ingest run so far has either gone into
   temporary databases or stopped at staged review files; zero real comp rows
   have been committed locally. The next data step is selective review and
   commit of actual historical records. Suggest starting with the highest-
   value subset (sale/lease comps) rather than reviewing everything
   (rent-roll/expense volume is large — one 5-folder batch alone produced
   962 rent-roll rows).
2. Add nullable `comp_id`/`lease_comp_id` link columns to the existing
   `source_artifacts` table (small additive migration, same pattern as
   `MIGRATION_COLUMNS` elsewhere in `db.py`). Confirmed by reading
   `ingest.py`'s `commit_extraction_result`: today, every artifact
   (photo/map/exhibit) gets tagged with the *subject* property's
   `property_id` only — never a specific comp's — so there is currently no
   way to link a comp to its own photo at all, automated or manual.
3. Add a manual "attach photo" action to `comp_review.py`'s Browse tab —
   upload an image, copy it into a local media folder, link it to that
   specific comp via the new columns, no staging/review step needed since
   Derek is asserting it himself. **Derek confirmed manual attach is fine
   as the first pass** — no need to solve automated photo extraction to
   get value here.
4. Show a thumbnail per comp with an attached photo in the Browse tab.
   (Also note for later: even artifact *metadata* review today never
   renders the image itself — `comp_review.py`'s `_render_artifact` shows
   title/kind/dimensions only, no `st.image()` call.)

Automated photo-to-comp extraction is explicitly deferred, not abandoned:
inspected one of Derek's real historical comp-sheet files (outside this
repo) as a concrete example. It uses a column-per-comp table grid (each
comp is one column, its photo sits in a fixed row of that same column) —
genuinely a different, *easier* layout to parse reliably (same table, same
column) than a page-proximity guess would have been. But it's also a
**different layout than `extractor.py`'s existing "Axiom-format" comp
parser** (`_is_axiom_comp_table`/`_is_axiom_cont_table`, ~line 799-905,
which expects a 2-table-per-comp layout: 3-col left + 2-col right,
"Improved Sale No. X" / "...(Cont.)"). Neither parser captures photos at
all today, text fields only. Derek says he has many archive files "like
this that can isolate sales comps" — before building a parser for the
column-grid layout, worth scanning a batch of his archive to see how much
layout variety actually exists (dominant vs. legacy format) — offered to
do this read-only, not yet done.

**Track 2 — UI/UX consolidation (agreed direction, sequenced after Track 1
has something real to show).**
Codex has started this: `axiom_ui.py` is now a multipage Streamlit workbench
instead of a single assignment list with the comp library appended below it.
Still pending: live browser QA, interaction pass, and any visual polish after
seeing it run with real Streamlit.
Two Streamlit apps already exist and shouldn't be rebuilt from scratch:
`axiom_ui.py` ("Command Center" — wraps `cmd_new`/`cmd_engage`/
`cmd_deliver`/`cmd_dilmore`) and `comp_review.py` (staged review + comp
library extract/review/browse). The real gap is they're separate apps, and
neither surfaces `validate`, `contract`, or the `*-search` commands
(`comp-search`, `financial-search`, `observation-search`,
`artifact-search`) at all. Plan is to consolidate into one multipage
Streamlit app covering the full lifecycle, not build a new framework —
Phase 17's "Web Platform" is the bigger, explicitly long-term version of
this and shouldn't be pulled forward.

**Parked, not forgotten — Derek wants to think these through more before
scoping:** three items from `docs/FEATURE_BACKLOG_PRIORITIZATION.md`'s
Tier A list each have an open question attached: automatic fee suggestions
(is the fee schedule simple enough for rules, or judgment-heavy?), bid-log
integration (what does the bid log actually consist of today?), and the
subject property one-pager (is county tax/parcel data already
Intake-entered, or does it need a live external lookup?). The other four
Tier A items — reconciliation cross-check, exhibit TOC/auto-numbering,
comp-aging alert, HBU narrative drafting assistant — have no open
questions and are ready to start whenever Track 1/2 wrap. Reconciliation
cross-check is the highest-value/lowest-risk one to start with (both
values it diffs already live in the same JSON export `fill_engine.py`
reads).

**Also still outstanding from before this session, both Derek's call:**
whether to spawn a round-5 Fable review of Phase 6 hardening (usage-cost
concern), and when to run the live-fire test on a real assignment.

Separately: keep treating this repo's git history as something to verify,
not trust — this session's truncated-commit finding (see "Completed this
session (Claude, git-integrity fix — 2026-07-13)" below) shows the known
OneDrive/bash file-truncation bug can land inside an actual commit, not
just a working-tree edit.

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

## Completed this session (Claude, Phase 6 hardening rounds 1-4 — 2026-07-11)

Phase 6 (the Adjustment Grid feature — `sca_adjustment_grid`/
`land_adjustment_grid`/`sca_qualitative`/`land_qualitative` tabs, read by
`adjustment_grid.py`, written by Dilmore's size-adjustment calc in
`axiom.py`) shipped complete on 2026-07-10 (see "Completed this session
(Claude, Phase 6 completion — 2026-07-10)" below). This session ran an
iterative adversarial-review cycle against it: spawn a Fable-model
(`model: "fable"`) agent to stress-test the real feature via synthetic
openpyxl-workbook repros, triage and fix what it finds, re-spawn to verify,
repeat. Four rounds ran; three produced real fixes now committed, the
fourth found more issues Derek has not yet triaged.

**Round 1 → commit `9d198a5`** ("Fix Fable adversarial review findings
(A1-A5) in Phase 6 Adjustment Grid"). Findings A1-A5 — see the commit for
exact details; broadly: gaps in how `adjustment_grid.py`'s row scan and
`axiom.py`'s Dilmore write/staleness-check paths handled edge cases in the
grid tabs (blank/malformed cells, the qualitative tabs' rating logic, and
similar). Full suite + `axiom.py contract` green before commit.

**Round 2 → commit `9026f2e`** ("Fix round-2 Fable adversarial review
findings (N1, A1/A3/A5 residuals)"). A follow-up review of round 1's fixes
found one new issue (N1) and residual gaps in three of round 1's fixes
(A1/A3/A5 — round 1 narrowed but didn't fully close them). Fixed and
re-verified.

**Round 3 → commit `4db2456`** ("Fix round-3 Fable findings: stale-cache
deadlock, orphan-anchor gap, scan disagreement, draft-mode side effect").
Four findings, all fixed:
- **P1 (highest severity):** `validation.py`'s stale-Dilmore-formula-cache
  check used to guess by looking for blank grid cells, which
  false-positived on legitimately-blank `IF()` formula results and
  permanently blocked delivery with no escape. Replaced with an explicit
  marker: `axiom.py`'s `_run_dilmore_calc`, right after a real write's
  `wb.save()`, now writes `formula_cache_stale: true` and
  `formula_cache_stale_mtime: <workbook mtime at that moment>` into
  `.axiom.json`. `validation.py`'s new `_dilmore_cache_still_stale()`
  compares that recorded mtime to the workbook file's *current* mtime —
  equal means still-stale (block), different means presumably
  resaved/recalculated since (let through). Read-only, matches
  `validate_assignment`'s non-mutating contract.
- **P2:** `adjustment_grid.py`'s `read_grid_rows` orphan-scan (which walks
  past the last detected comp row looking for a corrupted/cleared "Sale
  No." anchor) missed the case where the corrupted anchor belongs to the
  *last* comp's own row — nothing intact survives below it to trigger
  detection, silently dropping that comp from delivered reports. Now also
  raises when a row past the break has a blank anchor but non-blank data
  in any other tracked column.
- **P3 (same root cause as P2):** `axiom.py`'s `_run_dilmore_calc` and
  `_dilmore_staleness_warnings` used to scan `sca_adjustment_grid` rows
  7-16 unconditionally with no "Sale No." anchor check — unlike
  `read_grid_rows`, which always required one — so Dilmore could
  write/warn about a row the report generator would silently skip,
  producing a console/report disagreement about which comps were actually
  processed. Both now use the identical anchor-checked scan
  `read_grid_rows` uses (the older, pre-Phase-6 `size_adj` tab predates
  the anchor convention and correctly keeps its original unconditional
  7-16 window).
- **P4:** `cmd_deliver`'s `--draft` mode prints "Assignment delivery state
  will not be changed," but the Dilmore auto-run used to execute
  unconditionally regardless of `draft_mode` — a real write there mutates
  `workbook.xlsx` (wipes every other cached formula result) and, via P1's
  new state write, `.axiom.json` — contradicting that promise. Fixed by
  skipping the Dilmore auto-run entirely in draft mode.

Updated `tests/test_adjustment_grid.py`, `tests/test_validation.py`, and
`tests/test_torture.py` accordingly, including anchor labels added to four
existing `test_torture.py` fixtures that predated the P3 anchor-checked
scan (`test_dilmore_prefers_sca_adjustment_grid_over_size_adj`,
`test_dilmore_writes_comps_hand_expanded_past_row_16`,
`test_dilmore_staleness_warning_is_read_only`,
`test_deliver_auto_runs_dilmore_but_hard_stops_when_it_writes`,
`test_deliver_proceeds_when_dilmore_values_already_current` — the last two
also had their `--draft` flag removed since P4 made draft mode skip
Dilmore entirely, which would have silently defeated what those tests were
checking), plus one new regression test locking in P4's draft-mode
behavior (`test_draft_mode_never_runs_dilmore_or_mutates_anything`). Full
suite — 108 tests total this round (`test_adjustment_grid.py` +
`test_land_adjustment_grid.py` + `test_validation.py` + `test_torture.py`
= 85; the remaining ~23 across `test_artifact_harvest.py`,
`test_comp_pipeline.py`, `test_docx_golden.py`,
`test_financial_harvest.py`, `test_historical_harvest.py`,
`test_narrative_data_guard.py`, `test_observation_harvest.py`, run in
smaller batches/with `-k` filters to fit this sandbox's per-command time
limit, especially `test_financial_harvest.py`'s real-Tesseract OCR tests)
— plus `python axiom.py contract` (v1.2.0, 220 fields, 24 blocks) both
green before commit.

**Round 4 (Fable review only — NOT YET ACTED ON).** Spawned a fourth
Fable review against commit `4db2456` to verify rounds 1-3's fixes hold
and look for anything new. It independently re-verified all four P1-P4
fixes via its own repro scripts (not just reading the diff) and confirmed
they work as intended — nothing found that silently corrupts a *delivered*
report under default, unmodified-template use. It did find nine further
issues (Q1-Q9), none urgent:
- **Q2 (medium):** the P1 stale-cache marker tracks "the file was saved,"
  not "Excel recalculated," and is platform-defeatable: `comp_review.py`'s
  own workbook export (`comp_library.export_sale_comps_to_workbook`)
  resaves the assignment workbook — wiping the formula cache exactly like
  a real Dilmore write does — but doesn't set the new stale flag, since
  only `_run_dilmore_calc`'s save does. That path silently clears (never
  even sets) staleness detection.
- **Q6 (medium):** Dilmore writes to hardcoded columns (3/11/12 on
  `sca_adjustment_grid`), but `read_grid_rows` is header-driven and
  adapts to hand-inserted columns by design (per `adjustment_grid.py`'s
  own docstring). Insert one column before "Size Factor" and Dilmore
  silently writes adjustment numbers into whatever now occupies those
  column indices, reporting success with no error, and the delivered
  report renders the garbage.
- **Q7 (medium-low):** a comp GBA entered as an Excel formula reads
  differently in Dilmore's calc (raw formula string, silently skipped,
  loaded without `data_only`) vs. the staleness check/report reader
  (cached value, `data_only=True`) — produces a permanent "runs
  automatically on delivery" warning while the report ships with that
  comp's Size Factor/Adj % blank or stale.
- **Q1 (low-medium):** P2's fix only catches a *blank* corrupted anchor
  on the last comp; a typo (`"Sale No 2"`) or stray whitespace (`" "`)
  still silently drops that comp. Whitespace-only is the cheapest partial
  fix (`str.strip()` before the blank check).
- **Q3 (low-medium, environment-specific):** given the documented
  OneDrive-mount stale-stat-cache issue (see "Known limitations" below),
  running `validate`/`deliver` from a different environment than the one
  that recalculated/saved could reintroduce P1's exact symptom via a
  stale-cached mtime reading as still-equal.
- **Q4 (low):** draft mode still overwrites `last_delivery_error`,
  erasing a prior real delivery's "press F9 and recalculate" guidance
  message (P1's primary user-facing instruction) even though it correctly
  leaves `formula_cache_stale` itself untouched.
- **Q5 (low-medium, product call):** draft mode silently skips Dilmore
  with no document-visible warning when a real adjustment is actually
  pending — only a generic console line that prints on every draft
  regardless of whether anything is actually stale.
- **Q8 (low):** the stale flag is never cleared after a successful
  recalc+deliver (harmless to the mtime guard itself, but could mislead a
  future feature reading that key naively); `.axiom.json` writes are
  non-atomic, so a hand-edit interrupted mid-write silently fail-opens the
  guard.
- **Q9:** several checked-and-fine edge cases, not issues — see the full
  agent report in this session's transcript if needed.

Derek's call after seeing this list: **"stop here for now while we wait
for a usage reset."** Q1-Q9 were backlog at that point, not scheduled.

**Round 4 fixes — completed 2026-07-13.** Derek's later instruction was to
"do the round 4 fixes and we'll use whatever assignment is around when the
live test comes" — the live-fire test on a real assignment is a separate,
still-unscheduled step. All of Q1-Q9 were addressed:
- **Q1:** whitespace-only corrupted anchors on the last comp row are now
  caught by a `str.strip()` before the blank check (the cheap partial fix
  the round-4 review suggested; typo'd anchors like `"Sale No 2"` are a
  separate, unaddressed case).
- **Q2:** `comp_library.export_sale_comps_to_workbook` now sets the same
  `formula_cache_stale` (+ `formula_cache_stale_mtime`) marker a real
  Dilmore write sets, since it resaves the workbook the same way. Only
  exports that overwrite the actual live `workbook.xlsx` mark stale —
  exporting to some other filename in the assignment folder does not.
- **Q3:** documented-limitation only, no code fix (environment-specific
  OneDrive stale-stat-cache risk — see "Known limitations").
- **Q4:** draft mode no longer overwrites `last_delivery_error` on its own
  success path, so a prior real delivery's "press F9 and recalculate"
  guidance survives until an actual real delivery resolves it.
- **Q5:** draft mode's Dilmore-skip console message is now specific
  ("N pending size adjustment(s) were NOT calculated," naming which comps)
  when adjustments are actually outstanding, vs. the generic "nothing
  pending" message when there's nothing for Dilmore to ever compute.
- **Q6:** `_run_dilmore_calc` and `_dilmore_staleness_warnings` both now
  resolve their target columns by reading the tab's own header row
  (`_DILMORE_TAB_LAYOUTS`) instead of assuming fixed column indices, so a
  hand-inserted column no longer causes Dilmore to silently write
  adjustment numbers into the wrong column.
- **Q7:** Dilmore's calc now reads a comp GBA cell via a dual
  `data_only=True`/`data_only=False` workbook handle, so a GBA entered as
  a live Excel formula is read from its cached computed value instead of
  the raw formula text (which used to silently fail `float()` and skip the
  row).
- **Q8:** `formula_cache_stale`/`formula_cache_stale_mtime` are now popped
  from state after a successful (non-draft) delivery, and `_save_state`
  writes atomically (temp file + `replace()`) so an interrupted write can't
  leave `.axiom.json` half-written.
- **Q9:** confirmed non-issues, no action taken.

**Bonus hardening found this round (not part of Q1-Q9):** while testing the
Q8 atomic-write fix, found that `_save_state`'s `tmp_file.replace(state_file)`
itself wasn't resilient to a failed rename (locked file, antivirus, sync-client
lock — directly relevant given this repo lives on a OneDrive mount that has
repeatedly shown exactly this kind of lock behavior during development). Now
falls back to a direct non-atomic write if the atomic rename raises `OSError`,
so a state-write failure can't crash the very error-handling path
(`cmd_deliver`'s failure branch) that was trying to record why something else
just failed.

Regression tests added: two in `tests/test_comp_pipeline.py` (Q2:
`test_export_to_live_workbook_marks_formula_cache_stale`,
`test_export_to_non_workbook_filename_does_not_mark_stale`) and five in
`tests/test_torture.py` (Q4: `test_draft_mode_preserves_prior_real_delivery_error`;
Q5: `test_draft_mode_skip_message_is_specific_when_size_adjustments_pending`,
`test_draft_mode_skip_message_is_generic_when_nothing_pending`; Q7:
`test_dilmore_reads_comp_gba_from_live_formula_cached_value`, using a new
`_inject_cached_formula_value` XML-injection test helper since openpyxl has
no formula engine; Q8: `test_successful_delivery_clears_stale_formula_cache_flag`).
Full suite (139 tests total across all files, run in batches to fit this
sandbox's per-command time limit) plus `python axiom.py contract` (v1.2.0,
220 fields, 24 blocks, no drift) both green. No round-5 Fable review has
been spawned — per Derek's earlier note about Fable-review usage
consumption, that won't happen without checking with him first.

## Completed this session (Claude, git-integrity fix — 2026-07-13)

Asked to check current status against `HANDOFF.md`/`PROJECT_STATE.md` per the
start-of-session protocol. `git status`/`git log` initially failed with a
"dubious ownership" error (the repo's `.git` was owned by a different local
Windows account, `CodexSandboxOffline`, than the current session's `derek`
account) — Derek ran `git config --global --add safe.directory` himself
after I explained I won't touch git config directly.

With git working, `git status` showed a large amount of uncommitted work the
docs never mentioned — a direct violation of this file's own handoff
discipline. Investigated rather than assuming either the docs or the working
tree were right, per `AGENTS.md`'s "if documentation and code disagree,
trust neither automatically" rule:

- **All `.docx`/`.xlsx` template files showed as modified with sizes
  collapsing to ~130 bytes in `git diff --stat`.** Verified this was NOT
  data loss: the real on-disk files are intact, genuine ZIP/Office binaries
  (confirmed via direct byte inspection). The 130-byte figure is just how
  `git diff` renders these files now that `.gitattributes` routes
  `*.docx`/`*.xlsx` through the Git LFS clean filter while the actually
  committed blobs are full binaries — the exact mismatch Codex flagged on
  2026-07-09 ("do not stage these Office artifacts until the LFS
  normalization decision is made deliberately"). Left untouched, as before.
- **Real finding: six files were committed with content truncated
  mid-statement.** `git diff` against `HEAD` showed `ingest.py`,
  `narrative_generator.py`, `.gitignore`, this file, `PROJECT_STATE.md`, and
  `docs/ADJUSTMENT_GRID_DESIGN.md` all had their *committed* version cut off
  mid-sentence/mid-statement, with the complete, correct version already
  sitting in the working tree. Confirmed via `git show HEAD:ingest.py` piped
  through `py_compile`: the committed `ingest.py` (unchanged since `8400e01`,
  2026-07-09 — broken across several subsequent commits with nobody
  catching it) raised a real `SyntaxError`, cut off mid multi-byte
  box-drawing comment character. `narrative_generator.py`'s committed
  version (unchanged since `9b832a7`, 2026-07-10) happened to still parse
  but was missing its actual CLI entry-point body. This is the same known
  bash/OneDrive large-file-truncation bug documented multiple times
  elsewhere in this file — except this time it made it into `git commit`
  instead of just a working-tree edit that got caught before committing.
  Fixed by staging and committing the working tree's already-correct
  content for all six files as `a646c51`, then re-verified `git show
  HEAD:ingest.py` now compiles cleanly.
- Hit the documented stale-lock issue twice while doing this
  (`.git/index.lock` then `.git/HEAD.lock`, both "File exists" on a lock
  git itself couldn't clean up after a prior command on this mount) — used
  the already-documented `mv <lock> <lock>.stale.<ts>` workaround both
  times, ran the git-modifying command as its own isolated call afterward
  each time, and verified the result with `git cat-file -p HEAD` before
  trusting it, per this file's own prior "moral for next time" note.
- **Also found 10 untracked, orphaned scratch/duplicate files**:
  `axiom_fixed_r4.py`, `axiom_r4b.py`, `adjustment_grid_fixed_r4.py`,
  `comp_library_fixed_r4.py`, `tests/test_adj_grid_fixed_r4.py`,
  `tests/test_comp_pipeline_r4.py`, `tests/test_torture_fixed_r4.py`,
  `tests/test_torture_r4b.py`, `tests/test_torture_r4c.py`,
  `tests/test_torture_r4d.py`. These are leftover intermediate snapshots
  from the round-4 fix session's OneDrive edit-verify workaround technique
  (write to a duplicate filename, verify, then sync into the real file).
  Confirmed each was either byte-identical to (`axiom_r4b.py` vs. `axiom.py`;
  `adjustment_grid_fixed_r4.py` vs. `adjustment_grid.py`;
  `comp_library_fixed_r4.py` vs. `comp_library.py`; `test_torture_r4c.py`/
  `test_torture_r4d.py` vs. `tests/test_torture.py`) or a superseded earlier
  draft of (`axiom_fixed_r4.py`, `test_torture_fixed_r4.py`,
  `test_torture_r4b.py`) content already correctly in the real tracked
  files, then deleted all 10 — nothing was lost.
- Found one more untracked, harmless file: `CLAUDE.md` (one line,
  `@AGENTS.md`) — the include Claude Code reads for project instructions.
  Never committed. Added it as `e476235`.
- Working tree is now clean except for the known, deliberately-untouched
  LFS/binary mismatch on `.docx`/`.xlsx` files described above.

No test suite changes were needed for the fix above (it restores content,
not new behavior), but `HANDOFF.md`/`PROJECT_STATE.md` were updated to
record it (`e6d41e4`, `d9e9b07`) and `python axiom.py contract` stayed green
throughout.

**Follow-on same session: ran the full test suite live to prove it, since
Derek asked directly rather than taking the contract/compile checks as
sufficient.** This was also the first time this codebase's test suite ran
on Derek's own real Windows machine rather than the prior cloud sandbox,
which surfaced environment gaps neither prior HANDOFF entry mentioned:

- **No dependency manifest existed anywhere in this repo.** `pytest
  --collect-only` failed outright: `pdfplumber` (a hard, module-level import
  in `pdf_financial_extractor.py`) and `reportlab` (used only to build test
  PDF fixtures) weren't installed. Installed both via `pip install` to get
  collection working (155 tests collected).
- **Result with those two installed: 148 passed, 1 failed, 6 skipped.**
  Confirmed neither was caused by anything in this session before touching
  either:
  - The failure,
    `test_narrative_data_guard.py::InjectAllNarrativesSkipsApiOnBadDataTests::test_broken_sca_conclusion_data_skips_api_call`,
    hardcoded `Path("/tmp/_test_narrative_guard.docx")` — a POSIX path with
    no real writable meaning on Windows, so the `.docx` save inside the test
    raised `FileNotFoundError`. Pre-existing since commit `dce5d9d`
    (2026-07-10); unrelated to anything touched today. Fixed with
    `tempfile.gettempdir()` — commit `2623a2a`. Full suite re-run confirmed
    green with this fix alone before moving on.
  - The 6 skips were `test_financial_harvest.py`'s real-Tesseract OCR tests,
    gated on `PyMuPDF`/`Pillow`/a working local Tesseract per their existing
    `unittest.skipUnless` guards. This machine already had Tesseract 5.5.0
    and English tessdata (`.local/tessdata/eng.traineddata`) installed from
    an earlier session — only `PyMuPDF` and `pytesseract` themselves were
    missing from this machine's Python environment. Installed both;
    `_ocr_available()` now returns `True` and all 6 pass against the real
    OCR engine, no code changes needed.
- **Wrote `requirements.txt`** (commit `30469b6`), pinning all 10 actual
  third-party runtime/OCR/test-fixture dependencies to the exact versions
  just verified working (`pip install -r requirements.txt` confirmed
  resolves cleanly against this environment with zero conflicts) — this
  repo had never had one, so every dependency until now had been discovered
  ad hoc, session by session, exactly like the two gaps above.
- **Final verified state: 155 passed, 0 skipped, 16 subtests passed**, plus
  `python axiom.py contract` clean at v1.2.0/220/24, confirmed live.

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

## Completed this session (Claude, Phase 6 completion — 2026-07-10)

Continuation of the same-day Phase 6 work (steps 1-2 and step 4 were already
committed as `84fb3e5` and prior commits before this session began). Finished
the remaining pipeline steps from `docs/ADJUSTMENT_GRID_DESIGN.md`:

- **`field_registry.py`:** registered the 4 new `*_GRID_BLOCK` markers
  (`SCA_ADJUSTMENT_GRID_BLOCK`, `SCA_QUALITATIVE_GRID_BLOCK`,
  `LAND_ADJUSTMENT_GRID_BLOCK`, `LAND_QUALITATIVE_GRID_BLOCK`) under the
  `comparables` handler. Added a reverse-direction contract-drift check to
  `audit_assignment_contract` — every registered block with a non-empty
  `used_in` must have its marker actually present in the audited templates,
  not just the existing template -> registry direction. Without this, a
  registered block whose marker is missing/typo'd in the template would pass
  contract clean while silently never rendering — the same failure mode a
  historical outputs-tab key mismatch already hit once.
- **`adjustment_grid.py` (new):** reads `sca_adjustment_grid`,
  `land_adjustment_grid`, `sca_qualitative`, and `land_qualitative` and
  injects each as a Word table at its `[[..._GRID_BLOCK]]` marker. Column
  layout is discovered from each sheet's header row at runtime (not a fixed
  letter map like `comp_builder.py`'s `COMP_COLUMNS`), since category
  columns vary by `adjustment_factors.json`'s per-property-type preset.
- **`axiom.py`:** wired `inject_all_adjustment_grids` into `cmd_deliver`'s
  per-document loop, gated by the same `inject_comps` flag as the other
  comp/media injectors.
- **`templates/appraisal_template_styled_clean.docx`:** added the 4 new
  markers at the appropriate points in the Cost Approach (land) and Sales
  Comparison Approach (SCA) sections.
- **Real bug found and fixed:** `adjustment_grid.py`'s row scan initially
  collected any row with a non-blank value in a header column as a "comp
  row." This worked fine for `sca_adjustment_grid` (no summary rows below
  its comps) but misread `land_adjustment_grid`'s MEAN row and 4-row "LAND
  VALUE CONCLUSION" section as 5 extra phantom comps, because those rows
  happen to have non-blank values in the same header columns by coincidence
  of position (e.g. the conclusion section's own labels/values sitting in
  what's normally the `Location` column). Fixed by anchoring on the
  "Sale No. N" label every real comp row is written with, and stopping the
  scan at the first row whose Comp cell doesn't match. Regression test:
  `test_adjustment_grid.py`'s `test_stops_at_mean_and_summary_rows_below_comps`.
- **`tests/test_adjustment_grid.py` (new, 16 tests):** covers
  `read_grid_rows` (populated rows, blank-row skip, the MEAN/summary-row
  regression above, missing sheet, missing anchor header raising
  `AdjustmentGridError`), `_format_value` (percentage/currency/plain/date/
  blank formatting), and both injector entry points (table injection +
  marker removal, marker-not-found no-op, no-populated-rows no-op,
  independent per-block handling in `inject_all_adjustment_grids`).
- **`tests/demo_report_builder.py` + `tests/golden/demo_report_structure.json`:**
  DEMO-001's fixture has `CA_DEVELOPED = "No"` (this fixture models an
  assignment where the Cost Approach wasn't developed due to
  age/depreciation reliability concerns), and the land value sub-section —
  including the two LAND grid markers — sits inside the Cost Approach
  section in the template, which `fill_document`'s
  `_remove_conditional_sections` correctly strips for that reason. This
  initially looked like a second bug (LAND grids reporting 0 rows injected)
  until traced to body-index ranges confirming the LAND markers really do
  live inside the removed Cost Approach section (body indices 194-196 vs.
  the section's 153-252 range), while the SCA markers live in the separate,
  developed Sales Comparison Approach section. Fixed the test's expectation
  instead of the fixture: only the two SCA grid blocks are required to
  inject for DEMO-001; land-side injection correctness is covered
  independently by `test_adjustment_grid.py`. Golden snapshot regenerated to
  reflect the two new SCA grid tables now present in the generated report
  (paragraph count 1695 -> 1827, table count 65 -> 67).
- **Unrelated pre-existing defect found and fixed:** while running the full
  suite, `test_validation.py::test_sanitized_fixture_is_readable` flagged
  `REPORT_TYPE` as a stale Intake field. Root cause: the Intake sheet's
  `REPORT_TYPE` row (row 28) was merged across all 4 columns like a section
  header (matching the genuine section-header row directly below it,
  "PHYSICAL CHARACTERISTICS"), so there was no actual cell to type a value
  into — `REPORT_TYPE` could never be filled in from the Intake tab in any
  real assignment, even though `field_registry.py` lists its
  `source_of_truth` as `intake`. Confirmed this same defect exists in the
  real production `templates/workbook.xlsx`, not just the DEMO-001 fixture.
  Unmerged the row and gave it the normal key/value/description/checkmark
  structure every sibling row uses, in both files.
- **OneDrive-mount gotchas hit and worked around this session** (same
  categories as prior sessions, worth restating since they got unusually
  bad this time): a stale/torn bash view of `adjustment_grid.py` kept
  showing an old pre-fix version of `read_grid_rows` even after `__pycache__`
  was cleared and `dis.dis()` confirmed the loaded bytecode lacked the fix —
  resolved via the established `/tmp`-staged reconstruction + cross-mount
  `cp` pattern. Separately, `git status`/`git diff` reported "clean" for a
  `PROJECT_STATE.md` edit that `git hash-object` proved was genuinely
  different from HEAD — the poisoned-stat-cache issue, this time affecting
  `git add` itself (it left the index pointing at the old blob despite
  reporting success) until the same `/tmp`-staged rewrite was applied. Also:
  `openpyxl.Workbook.save()` after a normal (non-`data_only`) load silently
  drops cached formula *values* for cells the code never touched (confirmed
  on both `templates/workbook.xlsx` and the DEMO-001 fixture after the
  `REPORT_TYPE` unmerge fix) — recovered both files with a headless
  `soffice --headless --convert-to xlsx` recalculation pass. Worth
  remembering for any future direct-openpyxl edit to either workbook: always
  recalculate afterward if the workbook has formulas anywhere, even if the
  edit itself only touched non-formula cells.
- Full non-OCR suite grew from 103 to 119 tests (16 new in
  `test_adjustment_grid.py`); OCR suite (9 tests, run separately per this
  sandbox's time limits) unaffected and still green. `python axiom.py
  contract` clean at v1.2.0, 220 fields, 24 blocks (up from 20).
- Changed files: `adjustment_grid.py` (new), `field_registry.py`,
  `schemas/field_registry.v1.json`,
  `templates/appraisal_template_styled_clean.docx`, `templates/workbook.xlsx`,
  `axiom.py`, `tests/demo_report_builder.py`,
  `tests/fixtures/DEMO-001/workbook.xlsx`,
  `tests/golden/demo_report_structure.json`, `tests/test_adjustment_grid.py`
  (new), `PROJECT_STATE.md`, `HANDOFF.md`.

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
     `commit_extraction_result()`.** A staged batch with a wrong-typed list
     field (e.g. `"comps": "not a list"`, from hand-edited or corrupted JSON)
     used to crash with a confusing `'str' object has no attribute 'get'`
     deep inside `canonicalize_extraction_result()`. Added an explicit
     type check *before* that call, so the error is now a clear
     `ValueError: 'comps' must be a list of records, got str.`
- **Positive/reassuring findings** (no fix needed): all database writes use
  parameterized queries — repeated SQL-injection attempts
  (`Robert'); DROP TABLE...`-style payloads) found no vector anywhere in the
  tested insert paths. SQLite's `with conn:` transaction context also
  correctly leaves the database in a consistent, zero-partial-rows state even
  under a hard `os._exit(137)` mid-transaction kill.
- **Flagged for Derek's review — not auto-fixed, because each touches data
  correctness, schema, or a business-logic judgment call:**
  - A NaN/Infinity field can still reach the JSON-variable-export path into
    Word reports (a second, architecturally separate code path from the two
    `_number()` helpers fixed above) — needs a decision on where in the
    field-registry/validation chain to add the same guard.
  - `rent_roll_identity()` excludes dollar amounts from its identity key, so
    two records for the same unit/tenant/dates but a different rent amount
    silently collide and only one survives dedupe. `expense_identity()`, by
    contrast, includes the amount and correctly keeps both. This is a real
    design asymmetry worth a deliberate decision, not a silent patch.
  - Small-angle scan skew (5°–15°, short of a full 90° rotation) completely
    defeats OCR header recognition; a native text watermark on an otherwise
    scanned page routes the whole file to native-text extraction, silently
    skipping OCR and losing recoverable data.
  - Assignment-folder scanning (both media/photo discovery and financial-PDF
    folder scanning) follows symlinks pointing outside the assignment
    folder and treats the target as legitimate in-folder content — a
    folder-boundary gap on two independent code paths.
  - `init_db()`'s raw schema script and `_apply_migrations()` crash with an
    uncaught `OperationalError` on a synthetic minimal legacy `properties`
    table missing recently-added columns — not an active bug today (no real
    `axiom.db` exists yet) but a real risk the next time the schema evolves
    after real data exists.
  - `ingest.py`'s `commit_confirmed()` unconditionally marks a batch
    `.committed` even when every comp/lease_comp record in it was
    individually unconfirmed (silently skipped) — so a batch can be marked
    "fully committed" while contributing zero database rows, with no
    warning. This contradicts the documented "unreviewed/invalid batches
    roll back" invariant, which does hold for every other record type
    (rent_roll/expense/observation/artifact/assignment/income all raise on
    an unconfirmed record; only comps/lease_comps silently skip).
  - Unbounded field length has no sanity ceiling; hidden Excel rows and
    stale/uncalculated worksheets are still extracted as if current; a
    non-Latin tenant name can collapse identity in some cases; a read-only
    DB directory surfaces a raw low-level error instead of a clear message;
    homoglyph filenames aren't specially classified.
- Ran the full 82-test suite (per-file/per-batch this session, same net
  coverage, due to sandbox time limits) plus `python axiom.py contract`
  live in this checkout after porting all four fixes — zero regressions,
  v1.2.0/220 fields/20 blocks unchanged.

## Completed this session (Claude, stress-test follow-up — 2026-07-09)

Immediately after the stress-test pass above, asked Derek which way to
resolve two of the flagged (not auto-fixed) items, since both are judgment
calls about business logic rather than obvious bugs. His answers:

- **Rent-roll dedupe should include the amount, matching expense dedupe.**
  `rent_roll_identity()` in `harvest_contract.py` now includes
  `monthly_rent`/`annual_rent` in its identity key alongside
  unit/suite/tenant/dates/sf_leased, so two rows for the same unit/tenant/
  dates but a different rent amount are correctly treated as distinct
  records instead of one silently overwriting the other during dedupe. Added
  `test_rent_roll_identity_distinguishes_same_unit_different_rent` to
  `tests/test_financial_harvest.py`.
- **A batch with zero confirmed comps/lease_comps should raise, matching
  every other harvest record type.** `commit_extraction_result()` in
  `ingest.py`'s comps/lease_comps loop previously did `continue` past any
  record whose `review.status != "confirmed"` — silently skipping it. It now
  raises `ValueError` naming the record, exactly like the existing
  rent_roll/expense/observation/artifact loop already does. Under the normal
  `review_staged()` -> `confirm_extraction_result()` flow this never
  actually fires (every surviving comp is marked confirmed before staging),
  so it's a defensive fix for a hand-edited or otherwise non-standard
  confirmed file, not a change to ordinary review behavior. Added
  `test_unconfirmed_comp_in_confirmed_batch_raises_instead_of_silent_skip` to
  `tests/test_comp_pipeline.py`.
- Ran the full suite (84 tests, up from 82 — the two new regression tests)
  plus `python axiom.py contract` live in this checkout — zero regressions,
  v1.2.0/220 fields/20 blocks unchanged.
- Changed files: `harvest_contract.py`, `ingest.py`,
  `tests/test_financial_harvest.py`, `tests/test_comp_pipeline.py`,
  `HANDOFF.md`, `PROJECT_STATE.md`.

## In progress

- **Phase 6 hardening round 4's findings (Q1-Q9) are fixed as of
  2026-07-13** (see "Round 4 fixes — completed 2026-07-13" above). Nothing
  left in-progress from round 4 itself; the live-fire test on a real
  assignment (Derek's phrase: "we'll use whatever assignment is around
  when the live test comes") is a separate, still-unscheduled step, not
  something to start proactively.
- The stress-test pass on the OCR/ingest side (2026-07-09) and its
  immediate follow-up are complete. The remaining flagged findings from
  that pass (OCR skew/watermark routing, symlink folder-boundary escape,
  legacy-schema migration crash risk, and the rest) are backlog, not
  in-progress work, same as before.

## Exact next step

Current next step after Codex's manual-photo and schema-only DB construction:
run the Streamlit workbench with the real Python environment (`start_axiom_ui.bat`)
and do a browser QA pass through Dashboard, Assignment Workflow, Comp Library,
Search, and System. After that, review the latest sale/lease rows in
`scratch/staged_comp_review/latest_sale_lease_comp_review.csv`. After review,
either use the Streamlit Review tab or selectively move/confirm only the
latest staged JSON files named in the packet summary before running
`comp-commit`; do not run plain `review-staged` blindly while older duplicate
staged files remain in `ingest/staged`. Once at least one comp exists in the
real local `axiom.db`, open the Comp Library Browse tab and do a quick
interactive attach/thumbnail smoke test with a real local JPG/PNG.

1. Round 4 is done — no round-5 Fable review has been spawned yet. Don't
   spawn one without checking with Derek first (he's previously flagged
   that Fable reviews consume a lot of usage). If/when he gives the
   go-ahead, spawn one against the current commit to verify Q1-Q9's fixes
   hold, same cycle rounds 1-4 followed.
2. Review the latest five staged copied-archive batches before any real
   database commit (unchanged from before — still Derek's own task, not
   something delegated to an agent). They include OCR-derived operating
   expenses and OCR page-limit warnings, so confirm whether the first 6
   pages are enough for each long statement or whether a deeper manual
   rerun is needed. Note: these five batches were staged before the
   rent-roll identity fix (2026-07-09), so their baked-in identity keys use
   the old (amount-excluding) formula — harmless for a first commit, but a
   re-extraction would be needed to get the new formula's protection for
   any of those specific rows.
3. If Derek wants to keep hardening the OCR lane further: terminal
   `review_staged` still lacks true per-record keep/skip for rent-roll/
   expense rows (native or OCR) — a pre-existing gap noted since the OCR
   lane first shipped, not newly introduced, and still not fixed. The OCR
   skew/watermark routing gaps and the symlink folder-boundary escape from
   the stress test are also still open, lower-priority backlog items.
4. Otherwise, the next real milestone is importing Derek's actual historical
   comp archive now that the identity-backfill migration is in place —
   `axiom.py comp-ingest` against the real archive root, review, then
   `comp-commit` into the real `axiom.db` (not a temporary one).

## Baseline checks run

- Full suite (via `pytest`, run per-file/per-batch this session due to
  sandbox time limits, not as one combined invocation; same net coverage):
  84 tests pass, confirmed live in this checkout with real OCR enabled and
  zero skips (82 from the prior hardening pass plus 2 new regression tests
  from this session's stress-test follow-up).
- Six direct OCR tests pass against the installed local Tesseract engine.
- One OCR orientation-scoring regression test passes without requiring
  Tesseract.
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

## Changed files this session (Claude, Phase 6 hardening rounds 1-4 — 2026-07-11)

Across `9d198a5`, `9026f2e`, and `4db2456` combined:

- `adjustment_grid.py` — round 1/2/3 fixes to `read_grid_rows`'s orphan-scan
  (culminating in P2's last-comp-own-anchor fix).
- `axiom.py` — round 1/2/3 fixes across `_run_dilmore_calc`,
  `_dilmore_staleness_warnings`, and `cmd_deliver` (culminating in P1's
  state-write, P3's anchor-checked scan, and P4's draft-mode guard).
- `validation.py` — round 3's `_dilmore_cache_still_stale()` replacing the
  round-1/2 blank-cell heuristic entirely (P1).
- `tests/test_adjustment_grid.py`, `tests/test_validation.py`,
  `tests/test_torture.py` — regression tests for every round's fixes.
- `HANDOFF.md`, `PROJECT_STATE.md` — this update.

Round 4 started as review-only (a spawned Fable agent, no repo changes) —
see "Completed this session (Claude, Phase 6 hardening rounds 1-4 —
2026-07-11)" above for its Q1-Q9 findings. Those findings were fixed in a
later session (2026-07-13); see "Round 4 fixes — completed 2026-07-13"
in that same section for what changed and which files.

## Changed files this session (Claude, 2026-07-08)

Both commits described above (`af29fb2` and the same-day follow-up) together
touch:

- `pdf_financial_extractor.py` — OCR lane implementation, plus the
  follow-up's arithmetic/total-reconciliation checks and missing-header
  warning.
- `ingest.py` — OCR-aware terminal review markers (`_is_ocr_record`,
  `_ocr_flag`); no logic changes to extraction/commit.
- `comp_review.py` — OCR warning banner + inline rendered-page-image display
  in `_render_record`.
- `tests/test_financial_harvest.py` — 6 OCR tests total (the original 4 plus
  2 follow-up regression tests) + fixture-building helpers.
- `docs/OCR_LANE_DESIGN.md` — new design doc (approved and implemented).
- `PROJECT_STATE.md`, `HANDOFF.md` — updated both times.

## Changed files this session (Codex, 2026-07-09)

- `pdf_financial_extractor.py` — Tesseract executable and tessdata
  auto-detection for local Windows installs, plus financial-structure-aware
  OCR orientation scoring.
- `extractor.py` — `scan_assignment_folder` now recursively routes strictly
  named financial PDFs found in subfolders (e.g. "Information Provided") into
  the financial parser instead of only indexing them as artifacts. This file
  was omitted from this list in an earlier draft of this handoff; caught
  during a same-day review pass.
- `.gitignore` — ignores `.local/` for local OCR model data, plus `*.bak` and
  a bare `node_modules` line added in this same review pass (see "Known
  limitations").
- `docs/OCR_LANE_DESIGN.md` — documents the auto-detection paths.
- `PROJECT_STATE.md`, `HANDOFF.md` — updated verified OCR install/test state.
- `tests/test_financial_harvest.py` — adds OCR orientation-scoring coverage,
  nested-financial-PDF-routing coverage, and statement-expense-fallback
  coverage.
- `comparable_contract.py` — normalizes placeholder date values to blank.
- `tests/test_comp_pipeline.py` — adds placeholder lease-expiration coverage.

## Changed files this session (Claude, hardening pass — 2026-07-08)

- `harvest_contract.py` — new `enforce_ocr_low_confidence()`.
- `pdf_financial_extractor.py` — `_ocr_pages_dir()` env-var override,
  `prune_ocr_pages()`, `_finalize_rent_roll_row()` (shared native/OCR
  rent-roll row logic), `_financial_structure_signals()`/
  `_page_has_financial_structure()`, orientation re-detect trigger fix, and
  centralized-confidence call sites replacing three ad hoc `force_low`
  checks.
- `extractor.py` — `_nested_financial_pdf_warnings()`, wired into
  `scan_assignment_folder`/`extract_assignment`.
- `db.py` — `backfill_legacy_identities()`, wired into `init_db()`.
- `axiom.py` — new `ocr-cleanup` command.
- `tests/test_financial_harvest.py` — 4 new tests (nested-PDF duplicate
  warning, no-warning-for-single-PDF, OCR-pages-dir env override, OCR page
  pruning).
- `tests/test_comp_pipeline.py` — 1 new test (legacy comp-row identity
  backfill matches a fresh import's identity).

## Changed files this session (Claude, stress-test hardening — 2026-07-09)

- `fill_engine.py` — `_XML_ILLEGAL_CHARS` regex and
  `_reject_illegal_xml_value()`, wired into `_replace_in_paragraph`.
- `financial_extractor.py` — `_number()` rejects non-finite
  (`nan`/`inf`/`Infinity`) results via `math.isfinite()`.
- `harvest_contract.py` — same `_number()` non-finite rejection.
- `ingest.py` — `review_staged()` and `commit_confirmed()` catch and skip
  unreadable/non-object JSON files instead of crashing the whole run;
  `commit_extraction_result()` validates list-shaped fields before
  `canonicalize_extraction_result()` touches them.
- `HANDOFF.md` — this session's summary and escalation list.

## Known limitations

- Two stray files at the platform root — `zzz_discard_me.bak` (a stale
  truncated copy of `pdf_financial_extractor.py`, harmless) and
  `node_modules` (a broken/dangling symlink) — could not be deleted from
  this sandbox: both `rm` and `mv` fail with "Operation not permitted" (the
  same unlink restriction documented elsewhere for `.git` lock files, just
  worse here since it blocks deletion entirely, not just lock cleanup).
  Added `*.bak` and a bare `node_modules` line to `.gitignore` so neither can
  be accidentally committed via `git add -A` in the meantime, but someone
  with normal OS-level file access (not this sandbox) should delete both by
  hand when convenient.
- **New this session, same root cause:** running the live-Tesseract OCR
  tests in this sandbox to verify the hardening pass wrote 31 synthetic
  fixture page images (fictional test PDFs, not real assignment data) into
  the real `ingest/staged/ocr_pages/` folder, because those tests use the
  default `OCR_PAGES_DIR` rather than a redirected test tempdir. They could
  not be deleted from this sandbox for the same "Operation not permitted"
  reason as the two files above — confirmed the restriction applies to
  arbitrary files on this mount, not just git-internal ones. They're
  harmless (gitignored, no real data, don't affect any staged batch's
  correctness) but add clutter; delete manually from
  `ingest/staged/ocr_pages/` when convenient, or run `python axiom.py
  ocr-cleanup` (added this session) from Derek's own machine where file
  deletion isn't restricted, which will safely remove them along with any
  other genuinely orphaned page images.

- **This sandbox's bash tool mounts this OneDrive-synced folder in a way
  that can lag behind edits made through the file-editing tool** — it can
  take a snapshot-like view rather than a live sync within a session. This
  was worked around successfully both times this session (once for the
  original OCR-lane commit, once for the follow-up): after editing via the
  file-editing tool and confirming correctness by re-reading, the same
  content was pushed into bash's view via bash-native writes (`cp` from a
  verified copy, or a heredoc write) before running tests — bash-native
  writes to this mount are immediately self-consistent, unlike edits made
  through the file-editing tool. Both times, the full suite was then run
  live in this checkout and confirmed passing (71/71, then 73/73) before
  committing — this is no longer an open verification gap, just a technique
  worth knowing about for the next session's own edit/test cycles.
- This same mount also does not let git commands unlink their own lock/temp
  files after normal use (`.git/index.lock`, `.git/HEAD.lock`,
  `.git/objects/**/tmp_obj_*` all warn "Operation not permitted" on cleanup,
  even on a successful command). `mv` (not `rm`) clears a stale lock before
  the next git command; the warnings themselves don't indicate corruption.
  **This got worse, not just noisier, while committing `6ad25af`:** the same
  restriction let a stale `.git/index.lock` get renamed over the real
  `.git/index` on write, corrupting it (`bad signature 0x00000000`), and
  separately left `HEAD` unmoved after a real commit object was already
  created. Both were recoverable without touching any working-tree file —
  `git read-tree HEAD` rebuilds a valid index from the last good commit
  (safe: it only touches the index, never the working tree), and a commit
  that exists as an object but didn't move `HEAD` can be recovered with
  `git update-ref refs/heads/main <hash>` after confirming via `git cat-file
  -p <hash>` that its tree/parent/message are the intended ones. This
  produced one confirmed-harmless duplicate dangling commit (identical tree
  to `dde13b8`, an earlier failed attempt at the same commit, 17 seconds
  older) sitting in the object database; `git gc` will eventually reap it.
  Moral for next time: do every index-modifying git command in its own bash
  call (not chained with others) and verify `git cat-file -p HEAD` names the
  right commit before trusting a "success" exit code on this mount.
- Plain `python` is not on PATH in the current Codex environment. The bundled
  Python runtime was used for checks.
- Tesseract is installed and synthetic OCR tests now run. Live archive
  extraction has been tested against an image-only rendering of Derek's
  supplied rent roll and proforma, but a naturally image-only scanned rent
  roll or P&L has not yet produced staged financial rows through full
  staging/review in this checkout. The naturally image-only JeffCo income
  statement OCRed clearly enough but did not match current expense-section
  parsing rules.
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
