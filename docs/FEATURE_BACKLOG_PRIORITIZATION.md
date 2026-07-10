# Feature Backlog — Prioritization (2026-07-10)

Source: Derek's brainstormed feature list from a prior conversation (28
numbered ideas plus 9 earlier bullet-point ideas). Cross-checked against
`axiom_platform_roadmap_status.html`'s 17-phase roadmap plus the business-tier
and vision entries, as of the 2026-07-10 Fable-reviewed correction pass.

Method: every idea below is mapped to a roadmap phase (exact match, subset of
a partial phase, or "not on the roadmap at all"), then ranked by effort vs.
value given what's *already built* — several ideas turn out to be free
(already done) or cheap (a thin layer over existing infrastructure) because
of how far Phase 3.5/5.5/9/12/14 (comp/financial harvesting) already reach.

## Already done — drop from backlog, don't re-scope

These three are full duplicates of shipped work; re-scoping them would be
redoing something that already exists.

- **Rent roll analyzer** — Phase 9's rent-roll analyzer is done, including
  specialty layouts (mini-storage, mobile-home, apartment, RV/site) with
  dedupe and review.
- **Extract data from old firm reports** — Phase 5.5 massively exceeded this;
  it's now the whole comp/financial/observation/artifact harvest pipeline.
- **Comp database integration** — Phase 12's SQLite comp database (6+ record
  types, stable identity, transactional commit) is done.

## Tier A — quick wins (low effort, build directly on shipped infrastructure)

Ranked highest first. All of these either extend code that already exists or
are narrow, well-bounded features with no external dependency.

1. **Reconciliation cross-check script** *(idea #1; Phase 11 subset)* —
   diffs the Excel reconciliation sheet's final value against the Word
   narrative's stated value. Both values already live in the same JSON
   variable export `fill_engine.py` already reads — this is close to a
   single-function comparison, not a new extraction problem. Catches a
   real ship-blocking error class before delivery.
2. **Exhibit TOC/numbering auto-builder** *(idea #23; Phase 5 subset)* —
   pure Word document mechanics (`python-docx` TOC field + exhibit
   auto-numbering), no new data or external service needed.
3. **Comp-aging alert** *(idea #16; Phase 13 subset)* — Phase 12's comp DB
   already stores effective dates and identity keys for every comp; this is
   a staleness-threshold query plus a dashboard/CLI surface, not new
   ingestion work.
4. **Subject property one-pager** *(idea #15; Phase 5 subset)* — assembles
   data that's largely already in the 220-field registry (zoning, FEMA
   panel, parcel info) into one reference sheet. Effort scales with whether
   county tax/parcel data needs a live external lookup or is already
   intake-entered; worth scoping that specific question before starting.
5. **HBU narrative drafting assistant** *(idea #3; Phase 7 extension)* —
   `narrative_generator.py`'s per-command model routing already supports
   adding a new structured-intake-to-narrative-block command. Directly
   blocked on task 54 (live-testing Phase 7 end to end) landing first, since
   there's no point adding a second narrative command before confirming the
   first one works against a real API key.
6. **Automatic fee suggestions** *(bullet-list idea; Phase 5 subset)* —
   likely a rule-based lookup off property type/size/complexity fields
   already in the registry. Low effort if the fee schedule is simple
   enough to encode as rules rather than a model.
7. **Integration with appraisal/bid log** *(bullet-list idea; Phase 5
   subset)* — effort depends entirely on what the bid log actually is
   today (spreadsheet vs. something else); worth a 5-minute question to
   Derek before scoping further.

## Tier B — medium effort/value (real new work, but foundation exists)

8. **Lease abstraction tool** *(idea #5; Phase 9 subset)* — new PDF
   extraction logic (escalations, expense reimbursement type, term/options)
   distinct from rent-roll fields, but reuses the PDF-extraction plumbing
   (native + OCR) already built for rent rolls and financial statements.
9. **Adjustment confidence scorer** *(idea #14; Phase 11 subset)* — tags
   grid adjustments by support type (paired sale/regression/bracketing/
   judgment). Conceptually simple, but genuinely blocked until Phase 6's
   adjustment grid exists — there's no grid to tag yet.
10. **Multi-family unit-mix income analyzer** *(idea #26; Phase 9 subset)* —
    builds on the already-done rent-roll analyzer, adds unit-mix-to-comp
    matching logic.
11. **Insurable value calculator** *(idea #27; Phase 9 subset)* — mostly a
    derivation off cost-approach data already in the registry; low-medium
    effort, no new data source needed.
12. **Report-exhibit map generator** *(idea #17; Phase 11 subset)* — needs a
    mapping API/service integration (external dependency), otherwise
    straightforward given comp addresses are already geocoded-adjacent data.
13. **Narrative voice-consistency checker** *(idea #18; Phase 7 extension)* —
    needs a style-profile corpus built from past reports first; real value
    for future staff onboarding, not just Derek's own use.
14. **Workfile auto-assembler** *(idea #19; Phase 10)* — file-organization
    automation; assignment folder conventions already exist, so this is
    mostly "copy the right things to the right USPAP-required structure,"
    not new extraction.
15. **Quality/condition from inspection photos** and **Construction type
    from photos** *(bullet-list ideas; Phase 8)* — Phase 8's own roadmap
    note already anticipates Claude vision on subject photos; medium effort
    since it's a new command but reuses the vision-model pattern rather
    than inventing one.
16. **Cap rate / market extraction tracker** *(idea #2; Phase 13 subset)*
    and **Market narrative updater** *(idea #4; Phase 13 subset)* — both
    build on Phase 13's already-seeded market-observation harvesting, but
    need an ongoing document-intake stream to stay useful over time, which
    is a process commitment as much as a coding one.
17. **Construction cost index tracker** *(idea #22; Phase 13 subset)* —
    needs an external cost-index data source (e.g., RSMeans-like); ongoing
    maintenance burden similar to #16 above.

## Tier C — bigger bets (high effort, and/or depends on data volume or external commitments not yet in place)

18. **Internal adjustment-justification engine** *(idea #7; Phase 13/6)* —
    mines the comp DB into a paired-sales-backed adjustment database;
    needs both Phase 6 (grid) built and enough comp volume to be
    statistically meaningful.
19. **Paired-sales matcher** *(idea #11; Phase 15)* — the roadmap's own
    note under Phase 15 says the Tier 2 data foundation (full-provenance
    comp DB) makes this "more feasible than originally scoped," but it's
    still unbuilt matching logic.
20. **Regression adjustment calculator** *(idea #12; Phase 15)* — same
    foundation-is-ready caveat as #19; needs enough data plus real
    statistical validation before it's trustworthy in a signed report.
21. **Bracketing visualizer** *(idea #13; Phase 15)* — exhibit-quality
    chart generation once comp/adjustment data exists to visualize.
22. **Comp-similarity geospatial engine** *(idea #10; Phase 15)* — needs
    GIS layers (zoning, flood, transit) as external data dependencies;
    higher effort than the other Phase 15 items.
23. **Sketch (CAD) from measurements** *(bullet-list idea; Phase 11.5)* —
    geometry/SVG generation from structured measurements; no work started
    on the roadmap, meaningfully more effort than the photo-based ideas.
24. **Scenario stress-testing deliverable** *(idea #9; new premium
    add-on)* — needs a working income-approach model with rate/vacancy/
    absorption sensitivity; a niche/premium product, not core workflow.
25. **Eminent domain / partial-taking module** *(idea #21; not on
    roadmap)* — specialized before-and-after valuation workflow; value
    depends on how often Axiom actually takes these assignments.
26. **Subdivision/development residual land analyzer** *(idea #24; not on
    roadmap)* — absorption-based DCF; niche, high effort.
27. **Tax-appeal support package generator** *(idea #25; not on roadmap)* —
    a new deliverable type needing its own comparable-assessment data
    sourcing.
28. **Inspection mobile app** *(bullet-list idea; not on roadmap)* — a
    genuinely separate infrastructure investment (mobile dev), unclear
    near-term value versus the existing desktop-based workflow.

## Business-tier ideas (not core-workflow features — separate track)

These four map directly onto roadmap business-tier entries and should be
evaluated on business terms (market size, licensing, marketing) rather than
ranked alongside engineering effort:

- **Birmingham submarket intelligence product** *(idea #8)* — exact match
  to the roadmap's "Birmingham Submarket Intelligence" entry: data
  foundation seeded (Phase 13), no product/reporting layer built.
- **Birmingham/Alabama CRE market data/news scraper** *(bullet-list idea)*
  — feeds directly into the item above; scope creep risk if pursued as
  its own thing rather than as Phase 13's data-collection layer.
- **Client-facing status portal** *(idea #20)* — exact match to the
  roadmap's business-tier entry; no work started.
- **Appraisal review marketplace angle** *(idea #28)* — exact match; the
  roadmap explicitly notes it depends on Phase 11 (QC & Compliance), which
  is only partial today — several Tier A/B items above (reconciliation
  cross-check, adjustment confidence scorer, exhibit map generator) are
  literally the missing pieces of that dependency.

## Cross-cutting note

A lot of these ideas are not new roadmap phases — they're already-named
open bullets *inside* existing partial phases (5, 9, 11, 13). Treating them
as 28 independent backlog items risks fragmenting the roadmap; recommend
folding each Tier A/B item into its matching phase's "still open" list in
`axiom_platform_roadmap_status.html` as it gets scheduled, rather than
tracking a second, parallel list.
