# Current Handoff

*Older dated session write-ups (everything that used to follow the
"Current objective" section below, from the 2026-07-08 through 2026-07-11
sessions) were moved verbatim to `docs/HANDOFF_ARCHIVE.md` on 2026-07-13 to
keep this file readable in one pass — it had grown to 2192 lines. Nothing
was summarized or edited, only relocated.*

- Last updated: 2026-07-13
- Current agent: Claude
- **Calculation-engine rebuild, Phase 3e (lease-interest analysis) built
  — 2026-07-13 (not yet committed).** Covers Part 11 ("Lease Analysis")
  of the Appraisal Institute's *General Appraiser Income Approach/Part 2*
  course. New `lease_interest_engine.py` (pure functions, no I/O,
  deliberately thin like `mortgage_equity_engine.py` — valuing any single
  interest's cash flows is done by the caller directly via
  `dcf_engine`/`tvm_engine`, not re-wrapped here): `net_income_to_interest`
  (the course's own "rent collected − rent paid" formula, uniform across
  leased fee/sandwich/subleasehold/fee simple), `overage_rent`
  (percentage rent), `lease_yield_rate_ordering_is_plausible` (confirmed
  `Y_LF < Y_LH < Y_SLH` — leased fee lowest-risk/senior, subleasehold
  highest-risk/residual — documented sanity check only, same pattern as
  Phase 3d's mortgage-equity ordering check), and
  `fee_simple_reconciliation_gap` (exposes, doesn't force, whether
  leased-fee + leasehold-family components sum to fee simple — the
  source material is explicit that identity only holds in a "perfect
  market"). The step-up-lease-paid-in-advance case (this course's own 6.4
  Problem) needed no new code — already implemented and tested via
  `dcf_engine.present_value_income_in_advance`.
  - **Independent-verification finding, disclosed in the test itself**:
    Self-Study Sections 5 & 6 Problem 34's own component summary grid
    mislabels the sandwich leasehold's discount rate as "11%" (identical
    in both the "Problems" and "Solutions" printings), but the problem's
    own question text asks for "a 20% discount rate," and the grid's own
    printed $7,477 answer only reproduces at i=20 (i=11 gives $9,240,
    nowhere close). Treated as a booklet transcription error; the test
    uses the correct 20% rate and discloses the mislabel.
  - Confirmed and tested: the sum-of-parts reconciliation genuinely does
    NOT hold in Problem 34 (~$246 gap) even though it holds exactly in
    Part 12 Practice Test Question 4 (~$0 gap) — `fee_simple_reconciliation_gap`
    is asserted against both outcomes rather than forcing either.
  - Explicitly out of scope, confirmed no worked numeric example exists
    anywhere in the source material: excess rent, deficit rent,
    effective-rent calculation methods. The property-model leased-fee
    formula (`R_LF = Y_LF − Δ×(1/S_n)`, seen in Self-Study Problems 13/14)
    is deferred to the already-roadmapped Ellwood-style property-model
    phase (Parts 13/15/16) rather than folded in here.
  - 14 tests in `tests/test_lease_interest_engine.py`, citing Part 12
    Practice Test Question 4, Self-Study Sections 5 & 6 Problems 33/34,
    and Self-Study Sections 1 & 2 Problem 34 ("Phone Shak," overage
    rent) — every fixture independently recomputed in Python. Full suite
    337 passed (up from 323), `axiom.py contract` clean at v1.2.0/220/24
    (no registry-facing changes this phase). Not yet wired into
    `axiom.py`/`fill_engine`/the field registry.
- **Calculation-engine rebuild, Phase 3d (mortgage/equity-split DCF) built
  — 2026-07-13 (not yet committed).** Building on `tvm_engine.py` (Phase
  3a) and `dcf_engine.py` (Phase 3b), added full leveraged (mortgage-
  equity split) DCF analysis, grounded in the Appraisal Institute's
  *General Appraiser Income Approach/Part 2* course (PC404GCH-N), Parts
  7-10, and its solutions booklet. New `mortgage_equity_engine.py` (pure
  functions, no I/O; reuses `tvm_engine`'s amortization functions and
  `dcf_engine`'s `discounted_cash_flow_value`/`internal_rate_of_return`
  directly rather than re-deriving discounting math):
  `debt_coverage_ratio`/`loan_to_value_ratio` (confirmed only these two
  lender-risk measures exist in this course — no debt yield ratio, no
  break-even ratio, exhaustively searched), `mortgage_amount_from_dcr`
  (derives a loan amount from a required DCR), `cash_equivalent_price`
  (the confirmed 3-step procedure: amortize at the *contract* rate,
  discount those contract cash flows at the *market* rate, add the cash
  down payment), and `equity_cash_flows` (splits a property's cash flows
  into the equity piece via the source material's "four relationships" —
  `V_O = V_M + V_E`, equity income = NOI − annual debt service, equity
  reversion = property reversion − mortgage balance at reversion — and
  returns a dataclass exposing every intermediate value the worked
  examples print, not just the final split). `V_E`/`Y_E`/`V_O` are
  deliberately not separate functions: callers feed `equity_cash_flows`'s
  output straight into `dcf_engine`.
  - **Confirmed and deliberately NOT implemented**: a yield-rate "band of
    investment." Unlike the cap-rate version (`direct_cap_engine.
    band_of_investment_mortgage_equity`, already correct), the source
    material is explicit that `M × Y_M + (1−M) × Y_E ≠ Y_O` in general —
    building a function that computes one rate from the other two would
    invite a confirmed textbook error. Only a documented sanity check,
    `yield_rate_ordering_is_plausible` (checks `Y_E > Y_O > Y_M`), was
    added instead.
  - **Confirmed, tested, and NOT forced to reconcile**: independent
    unlevered-property and levered-equity DCF value conclusions for the
    same property can legitimately differ (Self-Study Problem 16: $4.376M
    vs. $4.712M) — the source material's own reasonableness-check
    teaching point, not an algebraic identity.
  - **Independent-verification finding, disclosed in the test itself**:
    Part 12 Practice Test Question 5's solutions-booklet answer key
    ($522,588.96) does not check out against its own printed cash-flow
    table (which discounts to $520,369.24 at 12.5% — reaching the
    booklet's stated answer requires a reversion $4,000 higher than the
    table states). Treated as a transcription error in that self-study
    problem's answer key ; the test asserts the internally-consistent,
    independently-recomputed value instead.
  - Explicitly out of scope, confirmed absent from ~500 pages of source
    material with no formula or worked example anywhere: variable-rate
    mortgages.
  - 21 tests in `tests/test_mortgage_equity_engine.py`, citing 8.1, 8.2,
    8.4, 8.5, 21.2, Self-Study Practice Problems Sections 3 & 4 (#4, #5,
    #8, #9 cross-checks, #12, #13, #15, #16), and Part 12 Practice Test
    Questions 1 and 5 — every numeric fixture independently recomputed in
    Python and, where practical, cross-checked directly against the
    source PDF's own printed intermediate values (not just its final
    answers). Full suite 323 passed (up from 302), `axiom.py contract`
    clean at v1.2.0/220/24 (no registry-facing changes this phase).
    Deferred: lease-interest analysis (Part 11), Ellwood-style property-
    model shortcuts (Parts 13/15/16), Phase 4 (Advanced Income
    Capitalization). Not yet wired into `axiom.py`/`fill_engine`/the
    field registry.
- **Fable adversarial review of the calc-engine rebuild (Phases 1-3c),
  findings fixed — 2026-07-13 (not yet committed).** Per Derek's request
  (usage now available in his upgraded plan), spawned a `model: "fable"`
  agent to independently re-derive the math in all five calc-engine
  modules (brute-force amortization simulation, manual NPV checks, full
  grid recomputation) and adversarially probe ~40 edge cases against the
  live code. **No reversed formulas, off-by-one indexing, or silent
  wrong-answer bugs found** in the core appraisal math — the rebuild's
  actual premise held up. Real findings, all fixed:
  - **High severity, real bug**: `tvm_engine.solve_yield_rate` and
    `dcf_engine.internal_rate_of_return`'s bisection used an absolute
    NPV-in-dollars tolerance (`1e-9`) to judge convergence — fails to
    converge at routine institutional scale (a $5M+ property genuinely
    raised "did not converge"), and converges too early to a materially
    wrong rate at very small dollar magnitudes. Fixed by switching to a
    bisection interval-width tolerance in RATE terms (scale-invariant),
    dropping the NPV-magnitude check entirely rather than just adding to
    it (an OR of the two didn't fix the small-scale case — verified this
    directly before finalizing). Confirmed fixed at both the original
    failing $5M/$25M scale and a 1e-9-scaled tiny case, both now landing
    on the exact expected rate.
  - `sca_engine.unit_price_stats`/`select_unit_of_comparison`: a
    negative-mean candidate produced a negative CV that silently won
    `min()`; now rejected with `SCAEngineError`. `Stats.mode` also no
    longer fabricates a value when nothing actually repeats (a
    `statistics.mode()` 3.8+ quirk) — returns `None` instead.
  - `tvm_engine`: `rate <= -1` (meaningless for compounding) now raises
    instead of producing a raw `ZeroDivisionError` or sign-nonsense
    result; `periods == 0` now raises regardless of `rate` (previously
    only guarded inside the `rate == 0` branch).
  - `direct_cap_engine.compute_egi`: `total_pgi` previously meant
    different things (with/without `other_income` folded in) depending on
    `other_income_subject_to_vacancy` — now always consistently means
    PGI + reimbursements only, matching the textbook's own "Total PGI"
    line item, in both branches. Also added `vacancy_collection_loss_pct`
    range validation (0-1).
  - `direct_cap_engine.py`: added `extract_building_rate_via_residual`
    (the 16.5 Problem's actual calculation — the existing
    `test_16_5_problem_building_rate_extraction` test didn't call any
    engine function at all, it verified the booklet's number against
    itself; now rewritten to exercise the real function).
  - `forecast_engine.apply_below_the_line_items`: a non-int year key
    (e.g. `3.0`) now raises `ForecastEngineError` instead of a raw
    `TypeError`.
  - `dcf_engine.dcf_periodic_yield_rate`'s docstring wording was checked
    against the actual source material and tightened — the formula
    itself was already correct (independently confirmed by both the
    review and a direct re-check of the PC404 research notes); the
    "overstates" claim was ambiguous about which comparison it meant.
  - 12 new regression tests added across the five test files covering
    every fix above, including both ends of the convergence-scale bug.
  Full suite 302 passed (up from 290), contract clean at v1.2.0/220/24.
  Deferred/not changed: the sign-convention asymmetry between
  `dcf.internal_rate_of_return` (positive capital outlay) and
  `tvm.solve_yield_rate` (signed PV) — both already documented, judged
  low-risk to leave as-is rather than force a matching convention across
  modules with different natural call patterns.
- **Calculation-engine rebuild, Phase 3c (cash-flow-pattern forecasting)
  built — 2026-07-13 (not yet committed).** Building on
  `direct_cap_engine.py` (Phase 2) and `dcf_engine.py` (Phase 3b), added
  the functions that *generate* the cash-flow sequences `dcf_engine.py`
  consumes as given inputs — grounded in the Appraisal Institute's
  *General Appraiser Income Approach/Part 2* course, Part 3 ("Forecasting
  Cash Flows") and Part 14 ("Income Patterns"). New `forecast_engine.py`
  (pure functions, no I/O, reuses `direct_cap_engine.compute_egi`/
  `compute_noi` per year rather than re-deriving that math):
  `compound_growth_series`/`level_series` (confirmed the SAME compound-
  growth formula covers both multi-year income/expense forecasting and
  the named "Compound Rate of Change Income Pattern" — not separate
  implementations), `forecast_noi_series` (full multi-year PGI→EGI→NOI
  assembly, confirmed fixed/variable expenses conventionally grow at
  *different* rates than income), `apply_below_the_line_items` (capex/TI/
  leasing commissions deducted only in their specific forecast year, per
  DCF convention — contrast with Direct Capitalization's one-time
  post-processing treatment), `deduct_deferred_maintenance` (confirmed
  NOT a below-the-line expense — comes out of value, never a year's cash
  flow), `net_reversion` (expenses-of-sale refinement on Phase 2's
  `reversion_value`), and the `R = Y − CR` relationship (confirmed valid
  only under a "frozen rate," perpetual-growth premise — explicitly NOT
  the same condition as a finite-horizon compound-growth series, a
  distinction the code's docstrings call out so the two aren't confused).
  18 tests in `tests/test_forecast_engine.py`, including a genuine
  integration test spanning this module and `dcf_engine.py`: a level
  $50,000/yr stream, an irregular stream, and a 2%-compound-growth
  stream all independently verified to produce the identical PV — the
  source material's own "level equivalence" demonstration. Full suite 290
  passed, `axiom.py contract` clean at v1.2.0/220/24. Deferred:
  tenant-by-tenant lease-schedule-driven forecasting (no closed form
  exists per the source material — it's hand-assembled and fed through
  the existing irregular-DCF path), mortgage/equity-split DCF, lease
  analysis, and the general Ellwood property-model form
  (`R = Y − Δ×(1/S_n)`) beyond the simple compound-growth case. Not yet
  wired into `axiom.py`/`fill_engine`/the field registry.
- **Calculation-engine rebuild, Phase 3b (core DCF) built — 2026-07-13 (not
  yet committed).** Building on Phase 3a's `tvm_engine.py`, added the core
  discounted-cash-flow valuation mechanics, grounded in the Appraisal
  Institute's *General Appraiser Income Approach/Part 2* course
  (PC404GCH-N, Parts 1/2/4-6 only — cash-flow-pattern forecasting,
  mortgage/equity-split DCF, lease analysis, and Ellwood-style property
  models are separate, later sub-phases) and its solutions booklet
  (PC404GSB-N). New `dcf_engine.py` (pure functions, no I/O, imports
  `tvm_engine`'s factor functions rather than re-deriving them): the
  general DCF formula (with reversion combined into the final period
  automatically — the single most common DCF error the source material
  catalogs is putting it in its own extra period), NPV, IRR (bisection,
  generalizing `tvm_engine.solve_yield_rate` to irregular cash flows),
  level-equivalent annuity, split-rate discounting, income-in-advance
  handling (confirmed only the income component gets the (1+Y) advance
  multiplier, never a reversion — verified this holds for any cash-flow
  shape via direct derivation, not just level annuities), a DCF-specific
  periodic-yield-rate conversion (confirmed **not** the same as
  `tvm_engine.periodic_rate`'s nominal/z convention — naively dividing a
  market yield rate by 12 is a confirmed, named improper practice that
  overstates value), and the course's own explicit reasonableness-check
  step (implied overall rate vs. terminal cap rate). 19 tests in
  `tests/test_dcf_engine.py`, citing specific solutions-booklet problems,
  including the intricate step-up-ground-lease income-in-advance case
  independently re-derived and verified before being hardcoded. Full suite
  272 passed, `axiom.py contract` clean at v1.2.0/220/24. Deferred within
  DCF/yield-cap: cash-flow-pattern forecasting (Part 3/14),
  mortgage/equity-split DCF (Parts 7-10), lease-interest analysis (Part
  11), Ellwood-style property-model shortcuts (Parts 13/15/16) — each a
  separate future sub-phase. Not yet wired into
  `axiom.py`/`fill_engine`/the field registry, same as every prior phase.
- **Calculation-engine rebuild, Phase 3a (Time Value of Money) built —
  2026-07-13 (not yet committed).** Following Phase 2 (Direct
  Capitalization), Phase 2's own plan had explicitly deferred all TVM/
  annuity math as "a separate foundational module... build later if/when
  DCF (Phase 3) needs it." Derek confirmed: build that foundation first
  (Phase 3a) before the actual DCF/yield-capitalization content (Phase 3b,
  *Income Approach/Part 2*, PC404GCH-N, not yet started). Source: the same
  *General Appraiser Income Approach/Part 1* course used for Phase 2, but
  its Parts 2-4 ("Time Value of Money and Related Concepts", "Tables,
  Six-Function Summary") instead of Parts 6-21. New `tvm_engine.py` (pure
  functions, no I/O): the Six Functions of a Dollar (future/present value
  of 1, future/present value of an annuity of 1, sinking fund factor,
  installment to amortize 1), applied convenience wrappers (mortgage
  payment, loan balance, annuity-due conversion, nominal/effective rate
  conversion, combination level-annuity+reversion, mortgage capitalization
  rate), and a bisection-based yield-rate solver (the textbook has no
  closed form for this, confirmed). **Closes a real gap Phase 2 left
  open**: `mortgage_capitalization_rate` derives the band-of-investment
  mortgage rate directly from loan terms, rather than requiring it as a
  raw input — not yet wired into `direct_cap_engine.py`, a deliberate
  separate decision. 28 tests in `tests/test_tvm_engine.py`, including a
  fully parametrized test against the textbook's own complete printed
  6%/n=1-30 factor table (30 rows × 6 factors, all independently
  recomputed). One fixture (mortgage cap rate, 4.6 Problem) is explicitly
  disclosed as reverse-engineered — the solutions booklet states only the
  final R_M/Y_M answer, not the underlying loan term, so the term was found
  by numeric match rather than transcribed. Full suite 253 passed,
  `axiom.py contract` clean at v1.2.0/220/24. Solving for an unknown term
  (n) is explicitly deferred — no verified worked example was found to
  test it against. Next: Phase 3b, the actual DCF/yield-capitalization
  content, built on top of this foundation.
- **Calculation-engine rebuild, Phase 2 (Direct Capitalization) built —
  2026-07-13 (not yet committed).** Following Phase 1 (SCA), planned and
  built the Direct Capitalization piece of the Income Approach, grounded in
  the Appraisal Institute's *General Appraiser Income Approach/Part 1*
  course (PC403GCH-M) and its solutions booklet (PC403GSB-M) — Derek's own
  materials. Scope decisions made with Derek before planning: cover both
  Direct Cap (this phase) and DCF/yield capitalization (Part 2, next
  phase) eventually, sequenced Direct Cap first; also roadmap *Advanced
  Income Capitalization* (PC501GDCHI) as a further future phase, not
  started. New `direct_cap_engine.py` (pure functions, no I/O, same
  pattern as `sca_engine.py`/`dilmore.py`): PGI→EGI→NOI reconstruction,
  overall-cap-rate/multiplier extraction-and-application, band of
  investment (mortgage-equity and land-building, both directions),
  underwriter's method, land/building and mortgage/equity residual
  techniques, reversion via terminal cap rate, and the platform's
  previously-orphaned `noi_adj` comp-adjustment formula (confirmed correct
  with Derek — not a page-cited textbook technique, a derived extension of
  the textbook's own rate-extraction principle). 26 tests in
  `tests/test_direct_cap_engine.py`, all citing specific solutions-booklet
  problems with values independently recomputed in Python before being
  hardcoded (matching Phase 1's fixture standard) — including a 4-scenario
  highest-and-best-use land-residual test where one scenario correctly
  resolves to a negative value (infeasible use), not an error. Full suite
  225 passed, `axiom.py contract` clean at v1.2.0/220/24. Explicitly
  deferred within this phase: leasehold/leased-fee residual (belongs with
  DCF, Phase 3, per the textbook's own guidance), property-tax cap-rate
  "loading" (no verified worked example found), and any time-value-of-money/
  loan-amortization math (a separate foundational module neither this nor
  the future DCF phase has built yet — mortgage-equity functions take
  mortgage value as a given input, not derived from loan terms). Not yet
  wired into `axiom.py`/`fill_engine`/the field registry — same integration
  deferral as Phase 1. See the plan file for full detail.
- **Calculation-engine rebuild, Phase 1 (SCA) merged to `main` — 2026-07-13.**
  Following the decision above to replace Excel as the calculation engine,
  the Sales Comparison Approach plan was refined via a remote Ultraplan
  session and delivered as a git bundle (`sca_engine.py` + initial
  `tests/test_sca_engine.py`, 22 tests, self-disclosed as hand-constructed
  fixtures since that environment had no access to the source textbook
  PDFs). Reviewed in an isolated worktree (all 22 passed; math hand-verified
  against the plan's sequence-of-adjustments rule) before touching `main`.
  Added 13 more tests transcribed from and verified against the actual
  Appraisal Institute textbook/solutions booklet (3.2 Example, the Part 16
  apartment and Part 17 office/retail case studies, two Part 2 statistics
  problems, Diagnostic Quiz Q8, Part 11.1's inbreeding citation) — every
  expected value independently recomputed in Python before being hardcoded,
  not transcribed by eye. Merged as `1b5ea55` (`--no-ff`, 35 tests total).
  Full suite 199 passed, `axiom.py contract` clean at v1.2.0/220/24.
  **Not yet wired into `axiom.py`/`fill_engine`/the field registry, and does
  not retire Excel's staleness-tracking machinery** — `sca_engine.py` is
  pure functions, no I/O, decoupled from the workbook/DB/pipeline by design;
  that integration is explicitly deferred to a later phase (see the plan
  file referenced above, "Deferred to a later phase" section). Not yet
  pushed to `origin` — ask Derek before pushing.
- **Claude, live-fire test + Excel-COM findings — 2026-07-13.** Derek asked
  for the quickest path to a genuinely operational platform; agreed plan was
  a full live-fire pipeline test against a new, conspicuously fictional
  assignment (not `tests/fixtures/DEMO-001`, not the existing
  `assignments/DEMO-001_Northstar_Example_Holdings`). Along the way this
  surfaced enough about Excel's role in the platform that Derek made a
  bigger call — see the last bullet below.
  - **Fixed a real bug**: `templates/workbook.xlsx`'s `outputs`/`cost`
    sheets had 14 formulas referencing the `land` sheet Phase 6 deleted
    (replaced by `land_adjustment_grid`, `9b832a7`) but never repointed —
    every fresh workbook cached `#NAME?` for those cells. Never surfaced
    because `CA_DEVELOPED="No"` (as DEMO-001 always sets) strips the entire
    Cost-Approach section — where every one of those keys lives — before
    substitution. Repointed all 14 to `land_adjustment_grid`'s real cells
    (confirmed via `git show 9b832a7^:templates/workbook.xlsx` to see the
    deleted tab's original layout). Full suite + contract green after.
  - **Found and fixed a second, independent bug in the same template**:
    `outputs!E112` (a "Notes" column entry) was typed with a leading `=`,
    so Excel parses a plain-English note as a broken formula referencing an
    invalid `"c above"` cell reference. Interactive Excel silently
    auto-repairs this on open; Excel COM automation (`Workbooks.Open`)
    refuses the file outright with an opaque generic error (`0x800A03EC`).
    Found by bisecting (by sheet, then by row) why the new recalc script
    couldn't open *any* Axiom workbook. Fixed in `templates/workbook.xlsx`
    only — the same bug also exists in the committed
    `tests/fixtures/DEMO-001/workbook.xlsx` and the local (never-committed)
    `assignments/DEMO-001_Northstar_Example_Holdings/workbook.xlsx`, but
    fixing the fixture wiped all its cached formula values (a plain
    `openpyxl.save()` side effect, same class of issue documented elsewhere
    in this file) and broke `test_docx_golden.py`'s structural fingerprint
    test — reverted that one to keep the fixture's golden-tested state
    stable, per Derek's explicit call. Only the master template carries
    this fix, so every future `new` assignment gets it; the fixture and the
    stale live DEMO-001 folder do not.
  - **Built `scripts/recalc_workbook.py`** (`pywin32`/COM,
    `requirements.txt` now pins `pywin32==312`) to force a real Excel
    recalculation programmatically — openpyxl cannot compute formulas, and
    manual F9+save was the only prior path (no COM automation existed
    anywhere in this repo before today). Verified working once the two bugs
    above were fixed.
  - **Surfaced, concretely, the "sales tab vs sca_adjustment_grid not
    reconciled" gap**: the legacy `sales` tab (which `outputs!SCA_VALUE` and
    its supporting stats actually depend on, not the newer grid) had never
    had its 7 comp rows filled in, even in the reference fixture — a real
    recalculation produced genuine `#DIV/0!` cascading into `outputs`. Not
    fixed platform-wide (out of scope today) — only worked around in the
    new test assignment by filling `sales!C9:F15` and `sales!B56/C56` with
    values consistent with `sca_adjustment_grid`'s 3 real comps.
  - Created `assignments/LFT-001_Fictional_Testbed_Holdings_LLC`
    (gitignored, never committed), populated from
    `tests/fixtures/DEMO-001`'s already-consistent data with identity
    fields overridden (`FILE_NO`, `CLIENT_NAME`, `INVOICE_NO`).
    `python axiom.py validate LFT-001` now reports **completely clean**
    except the one gap unavoidable in this session: all 8 narrative blocks
    unresolved because `ANTHROPIC_API_KEY` isn't set here. Every other
    check (Intake/JSON freshness, formula-cache errors, comp/media/
    ownership-history blocks) passes. Real (non-draft) `deliver` needs Derek
    to supply the key himself (a secret, never set by the agent) — see
    "Current objective" below.
  - Full suite (164 tests, up from 155) and `axiom.py contract`
    (v1.2.0/220/24) both green after all fixes, with the fixture reverted.
  - **Derek's explicit call, prompted by the E112 find and the
    already-known reconciliation gap**: Excel as the platform's calculation
    engine is now considered the wrong long-term foundation, not just a
    rough edge. Comps/financials/observations already run on
    SQLite + Python + Streamlit; the sales-comparison/income/cost-approach
    math is the one piece still 100% trapped in Excel's own formula engine.
    Next step — its own dedicated, thorough planning session, not folded
    into this one: **plan the calculation-engine rebuild** — port the
    adjustment-grid, income-approach, cost-approach, and reconciliation math
    into tested Python (matching how `dilmore.py` already ported just the
    size-adjustment piece), decide what (if anything) survives as an
    Excel-based data-entry surface, and decide how correctness gets verified
    against the existing Excel model before anything real depends on it.
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
  (18 tests), `axiom.py contract`, and `git diff --check`. Follow-up UI wiring
  now has Manual Comp Entry call this layer for controlled dropdowns,
  calculated summaries, warning display, and disabled confirmed-save until hard
  blockers are fixed. Full browse/edit/detail redesign and draft persistence
  remain future slices.
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
  superseded by content already in the real tracked files. See
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, git-integrity
  fix — 2026-07-13)" section for full detail.**
- Earlier the same day (2026-07-13), Phase 6 hardening round-4 findings
  (Q1-Q9) were fixed and committed as `8f08aa6` — see
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, Phase 6
  hardening rounds 1-4 — 2026-07-11)" section, specifically its "Round 4
  fixes — completed 2026-07-13" note. No round-5 Fable review has been
  spawned — don't spawn one without checking with Derek first
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
  (round 3, findings P1-P4). Full details in `docs/HANDOFF_ARCHIVE.md`'s
  "Completed this session (Claude, Phase 6 hardening rounds 1-4 —
  2026-07-11)" section.
- Commits from the prior (2026-07-10) session: `2e124a1` — Phase 6 Adjustment Grid steps 5-6
  (`adjustment_grid.py` injector module, `field_registry.py` wiring, the 4
  new template markers, `axiom.py` deliver-stage wiring, and the unrelated
  `REPORT_TYPE` Intake-row template fix found along the way), plus a
  follow-up docs commit `6df37ef`. See `docs/HANDOFF_ARCHIVE.md`'s
  "Completed this session (Claude, Phase 6 completion — 2026-07-10)"
  section. This closes out Phase 6 entirely — steps 1-2 and step 4 were
  completed and committed in an earlier 2026-07-10 session as `84fb3e5`
  and prior commits. Older commits: `e05721b` — see
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, stress-test
  hardening — 2026-07-09)" section for the adversarial stress-test pass
  and its four auto-fixed, low-risk hardening changes. A same-day
  follow-up commit `8400e01` resolves two of that pass's flagged
  judgment-call items per Derek's explicit direction: rent-roll identity
  now includes the rent amount (matching expense identity), and an
  unconfirmed comp/lease_comp inside a confirmed batch now raises instead
  of silently skipping (matching every other harvest record type) — see
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, stress-test
  follow-up — 2026-07-09)" section. Prior commit `6ad25af` — see
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, hardening
  pass — 2026-07-08)" section. Prior to that, `dde13b8` covered Codex's
  2026-07-09 work plus the review-pass fixes described under
  `docs/HANDOFF_ARCHIVE.md`'s "Completed this session (Claude, review pass
  — 2026-07-08)" section. Not pushed to any remote.
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

**Refreshed 2026-07-13.** The calc-engine rebuild (see the entries above)
is the active thread: Phases 1-3e are done (Sales Comparison Approach,
Direct Capitalization, Time Value of Money, core DCF, cash-flow
forecasting, mortgage/equity-split DCF, lease-interest analysis), plus one
completed Fable adversarial review round covering Phases 1-3c. None of it
is wired into `axiom.py`/`fill_engine`/the field registry yet — every
module is standalone and only reachable via `pytest`.

**Candidate next pieces of the rebuild, not yet started, awaiting Derek's
direction on priority:**
- Ellwood-style property-model shortcuts (`R = Y − Δ×(1/S_n)`, Parts
  13/15/16 of `income_2.pdf`) — two clean worked fixtures for this (Self-
  Study Problems 13/14) were already found during Phase 3e's research and
  deliberately held back for this phase instead.
- Phase 4, Advanced Income Capitalization (`advanced_income.pdf`/
  `advanced_income_solutions.pdf`), not started.
- Wiring any of the built engines into `axiom.py`/`fill_engine`/the field
  registry — the platform cannot yet actually use any of this math
  end-to-end in a real assignment, only verify it via tests.

**Track 1 (comp database: real data + visual reference) and Track 2
(UI/UX consolidation)** were the agreed next-in-line work before the
Excel-to-Python rebuild decision superseded them (see the entries list
above for what Codex already built: manual comp-photo linking, a
schema-only real `axiom.db`, the five-view Streamlit workbench, manual
sale/lease comp entry, and the manual comp calculation/validation layer).
Both tracks are parked, not abandoned — pick back up whenever Derek wants
to prioritize them over more calc-engine phases. Immediate next steps
there, if resumed: run the real Streamlit workbench for a browser QA pass;
review the staged comp batches in
`scratch/staged_comp_review/latest_sale_lease_comp_review.csv` before any
real `comp-commit` (older duplicate staged files still sit in
`ingest/staged` — use the packet's named latest files, don't run plain
`review-staged` blindly); then do an interactive attach/thumbnail smoke
test once a real comp exists in `axiom.db`.

**Three Tier-A backlog items from `docs/FEATURE_BACKLOG_PRIORITIZATION.md`
need more thought before scoping** (each has an open question): automatic
fee suggestions (is the fee schedule simple enough for rules, or
judgment-heavy?), bid-log integration (what does the bid log actually
consist of today?), and the subject property one-pager (is county tax/
parcel data already Intake-entered, or does it need a live external
lookup?). Four other Tier A items have no open questions and are ready to
start whenever Track 1/2 or the calc-engine rebuild pause for them:
reconciliation cross-check (highest-value/lowest-risk — both values it
diffs already live in the same JSON export `fill_engine.py` reads),
exhibit TOC/auto-numbering, comp-aging alert, and an HBU narrative
drafting assistant.

**Still Derek's call, not to start proactively:**
- A round-5 Fable review of Phase 6 hardening (usage-cost concern) — see
  [[feedback-fable-review-gating]] in Claude's memory.
- The live-fire test on a **real** client assignment. The 2026-07-13
  live-fire test used `LFT-001_Fictional_Testbed_Holdings_LLC`, a
  conspicuously fictional testbed — a real-assignment live-fire test is a
  separate, still-unscheduled step.

Keep treating this repo's git history as something to verify, not trust —
the git-integrity fix in `docs/HANDOFF_ARCHIVE.md` shows the known
OneDrive/bash file-truncation bug can land inside an actual commit, not
just a working-tree edit.

## Do not touch

- Use only `tests/fixtures/DEMO-001` for repeatable assignment testing
  (or a disposable copy outside `assignments/` for new engine work).
- Never push without Derek's explicit approval, every time — a prior
  push being approved doesn't carry forward to the next one (matches
  `AGENTS.md`'s git discipline section).
- Do not live-test Adobe Sign, Xero, or Anthropic without explicit approval
  and local credentials.

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
