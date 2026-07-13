# Adjustment Grid Design (Phase 6 — proposed, not yet built)

**Revised after a Fable-model adversarial review** (see bottom of this
document for the full findings). Two blocking gaps from that review are
folded into Scope/Pipeline below rather than left as a separate list: the
existing `land` tab / `narrative_generator.py` dependency this design didn't
originally account for, and an already-broken `cmd_dilmore` command this
redesign would otherwise silently make worse.

This design is grounded in 10 of Derek's real historical "Market Chart"
workbooks (office, apartment, general-commercial, and land sales) rather than
a generic textbook grid. Derek confirmed the following while scoping this
document (via in-chat questions, all "Recommended" options chosen):

- Size Adjustment reuses the existing `dilmore_factor(ratio, curve)` /
  `dilmore_adj_pct(ratio, curve)` in `dilmore.py` unchanged — confirmed this
  is exactly the mechanism behind the "Size Adjustment" column in every real
  file inspected.
- Quality/Condition, Utility, and any other ad hoc category (e.g. an "HVAC
  Replacement Deduction" flat-dollar line seen in one real file) are always
  manual judgment entries — never auto-derived.
- The time/market-condition adjustment auto-fills for every comp row (each
  row's own monthly rate × that comp's own months-to-effective-date), with
  manual override always possible per row. Derek was unsure whether the
  row-1-only pattern in some real files was intentional; auto-fill-every-row
  is the safer default and doesn't remove the ability to hand-edit.
- Both the quantitative ($ adjustment) grid and the qualitative
  (Superior/Similar/Inferior) grid are required — building only one is not
  acceptable.
- Qualitative factors move from text labels to a numeric **0 / 1 / -1**
  scale, with "Overall" auto-computed as sum/average of the factor scores
  against a threshold, rather than eyeballed.
- Qualitative scores stay purely descriptive/supporting — they do **not**
  feed into or weight the final value indication, matching how Derek's real
  files use them today (a cross-check, not an input).

## Scope

**Current state** (`templates/workbook.xlsx`):

- `sales` — subject property reference only. No comp rows, no adjustments.
- `size_adj` — a skeleton already exists, 7 columns: `Comp`, `Comp GBA
  (SF)`, `Ratio (Ac/As)`, `Size Factor`, `Adj %`, `Adj $ / SF` (one header,
  dollars-per-square-foot), `Notes`. This is Size-only —
  no sale price, no time adjustment, no Location/Quality/Condition/Utility
  columns, no Net Adjustment, no Indicated Value.
- `dilmore` — the full Dilmore lookup table (`A_c/A_s` → factor for each of
  the 80/82.5/85/87.5/90 curves). Already correct and complete; no changes
  needed.
- `qualitative_analysis` — lease-comp only (`Comp No. / Location / Rate
  ($/SF) / Location / Quality / Condition / Size / Lease Terms / Overall`).
  There is no sale-comp qualitative grid at all today, and no numeric scale
  anywhere — this tab is text/blank-cell driven.
- `comp_builder.py` already shows the right precedent for variable-row,
  variable-column data read directly from a workbook sheet (`COMP_COLUMNS`
  column map) and injected into the report at `[[COMP_SHEETS_BLOCK]]` — the
  adjustment grid should follow this same shape, not the fixed-scalar-key
  shape used by `structured_blocks.py`'s `OWNERSHIP_HISTORY_TABLE` (that one
  has a fixed small field list; ours has a variable number of comps *and* a
  variable number of category columns).
- **`land` tab already exists and already feeds a report block.**
  `narrative_generator.py` reads per-comp land adjustment percentages
  (Market Conditions, Location, Other, Dilmore) directly from `land` tab
  rows 5–14 / cols 4–10 to generate `[[LAND_ADJUSTMENT_NARRATIVE]]`. This
  wasn't accounted for in the original draft of this design — see the `land`
  reconciliation requirement in Pipeline step 2 below. Without it, the new
  `land_adjustment_grid` tab would become a second, unreconciled source of
  truth for the same numbers the narrative describes — the same class of
  drift bug that already hit this project once (outputs-tab key mismatch).
- **`axiom.py`'s `cmd_dilmore` command is already broken today**, independent
  of this design: it calls `dilmore_factor(subject_gba, comp_gba, curve)`
  (3 args) against `dilmore.py`'s real signature `dilmore_factor(ratio,
  curve=85)` (2 args) — confirmed by reading both call site and definition.
  No test currently covers this path; it's reachable via `axiom_ui.py`'s
  "Run Dilmore" button. This redesign's tab restructure (moving Comp GBA off
  its current column) would silently corrupt other cells if `cmd_dilmore`'s
  hardcoded coordinates are left as-is and it's ever run again. Fixing or
  retiring this command must be in scope — see Pipeline step 0.

**This document scopes:**

1. Extending `size_adj` into a full sales-comparison net-adjustment grid
   (sale price → time adjustment → adjusted price → size adjustment →
   configurable category adjustments → net adjustment → indicated value),
   for improved-property comps.
2. A parallel land-sales version (per-acre basis, topography/surrounding-
   land-uses instead of quality/condition).
3. A new sale-comp qualitative grid (numeric 0/1/-1), separate from the
   existing lease-only `qualitative_analysis` tab, with property-type-
   specific factor presets (office/retail/industrial, apartment, land — the
   three variants actually observed across the real files).
4. Report injection: two new docx blocks per property type (quantitative +
   qualitative), wired into `axiom.py`'s `deliver` step the same way
   `inject_comp_section` / `inject_ownership_history` already are.

**Out of scope for v1:**

- Qualitative scores influencing the value conclusion — they remain
  descriptive only, per Derek's decision above.
- A dedicated Streamlit review UI for entering adjustments (see "Open
  questions" — recommended default is Excel-only entry for v1).
- Any property type beyond the three factor presets actually observed
  (office/retail/industrial, apartment, land). Adding a fourth later is a
  config change, not new code, if the mechanism below is built as proposed.

## Why the category/factor lists must be configurable, not hardcoded

Across the 10 real files, the adjustment categories and qualitative factors
were **not** a fixed schema:

- Every file had Size + Location. Most (7 of 10) also had Quality/Condition
  and Utility. One file added a one-off flat-dollar "HVAC Replacement
  Deduction" line that doesn't fit any recurring category.
- The qualitative factor list changed by property type: office used
  traffic/MHI/population/access/visibility/quality/condition/flood-zone/
  LTB/utility; apartment swapped in amenities and dropped traffic; land
  swapped in topography/surrounding-land-uses and dropped quality/condition/
  LTB entirely.

Hardcoding a fixed column set would work for the next assignment right up
until it doesn't — the same failure mode this platform has already hit once
with the outputs-tab key mismatch documented in `PROJECT_STATE.md`'s
history. The category/factor list must be **data**, not code: a per-
property-type preset that determines which columns appear, with every
category column always available for manual entry regardless of preset
(an appraiser can always add a one-off category by hand, matching the HVAC
deduction precedent).

## Dependencies

No new pip packages. This reuses:

- `openpyxl` (already a dependency) to read the new/extended workbook
  sheets, following `comp_builder.py`'s existing column-map pattern.
- `python-docx` (already a dependency) to build and inject the report
  tables, following `structured_blocks.py`'s existing table-injection
  pattern.
- `dilmore.py`'s `dilmore_factor` / `dilmore_adj_pct` unchanged — confirmed
  correct against real data, no changes proposed.

The only new artifact is a small property-type → factor-list preset,
proposed as a new `adjustment_factors.json` (or a new section in
`config.json` — open question below) rather than embedding the lists in
Python, so a new preset or a one-off category doesn't require a code change.

## Pipeline

0. **Fix or retire `cmd_dilmore` first.** It's broken today (3-arg call
   against a 2-arg function) and this design's tab restructure would make a
   latent bug into an active data-corruption risk if it's ever run against a
   restructured workbook. Decide: repair the call (fix arg count, fix the
   inverted ratio, fix the hardcoded write coordinates to track the new
   column layout) or remove the command if `size_adj`/the new grids make it
   redundant. Either way this needs a regression test — it has none today.
1. **Extend `size_adj` into `sca_adjustment_grid`** (quantitative grid,
   improved property). Proposed columns: `Comp No, Sale Price, Sale Date,
   Months to Effective Date, Monthly Market Rate, Time Adj %, Time Adj $,
   Adjusted Price, Comp GBA (SF), Ratio (Ac/As), Size Factor, Size Adj %,
   Size Adj $, [preset category columns...], Net Adjustment, Indicated
   Value ($/SF)`. Time adjustment auto-fills per row from a single
   monthly-rate input × that row's own sale-date-to-effective-date gap;
   every cell remains hand-editable.
2. **Add `land_adjustment_grid`** — same shape, per-acre basis
   (`Indicated Value / Acre`), topography/surrounding-land-uses in place of
   quality/condition, matching the real `2016 land adj charts` /
   `AS COMPLETE Market Chart` files. **Reconciliation with the existing
   `land` tab is required, not optional**: `narrative_generator.py` already
   reads Market Conditions / Location / Other / Dilmore adjustment
   percentages from `land` tab rows 5–14 to build
   `[[LAND_ADJUSTMENT_NARRATIVE]]`. Two acceptable resolutions — pick one
   before implementation, don't leave both tabs live and unreconciled:
   (a) retire the standalone `land` tab and point
   `narrative_generator.py` at the new `land_adjustment_grid` tab instead
   (same rows/columns it reads today, just relocated/renamed), or
   (b) keep `land` as the input tab `narrative_generator.py` already knows
   and make `land_adjustment_grid` a generated/derived view built from it
   rather than a second manually-entered tab. (a) is recommended — a single
   input tab per property type is simpler to keep in sync than a
   source-plus-derived-view pair.
3. **Add the property-type factor preset file** (`adjustment_factors.json`)
   listing, per property type, which quantitative category columns and
   which qualitative factors apply by default. Loaded once at grid-build
   time; every column stays overridable/addable by hand in the workbook
   regardless of preset.
4. **Add `sca_qualitative` and `land_qualitative` tabs** (numeric grid,
   parallel to the existing lease-only `qualitative_analysis` tab, not a
   modification of it — lease qualitative stays text-based since Derek
   didn't ask to change that one). Each factor cell takes 0/1/-1; `Overall`
   is a formula: sum or average of the row's factor scores compared against
   a threshold (exact sum-vs-average choice and threshold value are open
   questions below), plus a derived `#Superior / #Similar / #Inferior`
   tally per comp for narrative language that still reads the way Derek's
   reports read today.
5. **Register new field_registry blocks — this is a code change, not just a
   JSON edit.** `field_registry.v1.json`'s `"blocks"` section documents each
   injectable block's `handler` type (`media`, `narrative`, `comparables`,
   `structured`) and `used_in` stage — this is contract/audit metadata, not
   a runtime dispatch table; `axiom.py` explicitly imports and calls each
   injector function directly (`inject_comp_section`, `inject_media_blocks`,
   `inject_ownership_history`), confirmed by reading the actual call sites.
   Propose four new block entries — `SCA_ADJUSTMENT_GRID_BLOCK`,
   `SCA_QUALITATIVE_GRID_BLOCK`, `LAND_ADJUSTMENT_GRID_BLOCK`,
   `LAND_QUALITATIVE_GRID_BLOCK` — each `handler: "comparables"` (matching
   `COMP_SHEETS_BLOCK`'s shape: variable rows read from a workbook sheet,
   not a fixed field list like `OWNERSHIP_HISTORY_TABLE`), `used_in:
   ["deliver"]`. **`field_registry.py`'s `_block_handler` function hardcodes
   `"comparables"` for `COMP_SHEETS_BLOCK` by name** — it does not read the
   `handler` value out of the JSON generically. The four new block names
   must be added to that function explicitly, or they resolve to
   `"unregistered"` and `audit_assignment_contract` reports them as
   contract errors even after the JSON is updated. This edit also needs to
   survive a `scripts/build_field_registry.py` rebuild without being
   clobbered, if that script regenerates the `"blocks"` section from a
   different source of truth — confirm this before assuming a one-time
   JSON edit is sufficient.
   **Drift protection is currently one-directional and this design
   shouldn't ship without closing the other direction**: `axiom.py
   contract` verifies every template marker exists in the registry, but
   nothing today verifies the reverse — a registered `deliver`-stage block
   whose marker is missing or typo'd in the actual template still passes
   `contract` clean, and the section silently doesn't appear in the
   delivered report (the exact failure mode of the historical outputs-tab
   bug). Extend the contract check to also fail when a `used_in: ["deliver"]`
   block's marker isn't found in the template, and add a matching loud
   failure (not a silent skip) in `adjustment_grid.py` itself if a workbook
   sheet's header row doesn't match any column the injector expects.
6. **New injector module `adjustment_grid.py`**, mirroring
   `comp_builder.py`'s structure, with one correction: `comp_builder.py`'s
   fixed letter-based `COMP_COLUMNS` map (`"COMP_NO": "A"`, etc.) works
   because that sheet's column set never changes. Ours can't use a fixed
   letter map, because the whole point of the preset system in step 3 is
   that the category columns present are variable per assignment — a static
   letter map and a variable column set directly contradict each other.
   Instead, read each new sheet's **header row** at runtime and build the
   column map from header text → column index (skip a column if its header
   is blank), so a hand-added one-off category (the HVAC-deduction
   precedent) or a preset with fewer columns both just work without a code
   change. `Net Adjustment` and `Indicated Value` stay fixed, well-known
   trailing columns regardless of how many category columns precede them.
   **Computation home**: category adjustments and qualitative scores stay
   manual-entry cells (no formula) per Derek's decision above; Size
   Adjustment, Time Adjustment, Net Adjustment, and Indicated Value should
   be **Excel formulas** in the sheet (matching how `size_adj`/`dilmore`
   work today), not Python-computed — `adjustment_grid.py` reads the
   already-computed formula results the same way `comp_builder.py` reads
   `comp_data` today. This means the injector must open the workbook with
   `data_only=True` (computed values) rather than `data_only=False` (formula
   text), and any Excel-based test fixture must be built with a real
   calculation pass (e.g. via LibreOffice headless recalculation, matching
   how this project already handles other formula-driven fixtures) so
   `openpyxl` doesn't just return `None` for uncalculated formula cells.
   The module itself provides functions to read rows and build docx tables,
   one function per block to find its `[[...]]` marker and inject. Wired
   into `axiom.py`'s `deliver` step alongside the existing
   `inject_comp_section` / `inject_ownership_history` calls.
7. **Add the four new markers to the report template.** This is a template
   change, not just a code change — needs Derek's review before or as part
   of implementation, since the master template is his and past experience
   on this platform (outputs-tab key mismatches) shows template/schema
   drift is exactly where things have broken before.

## Report injection changes

- Same mechanism as existing blocks: `[[SCA_ADJUSTMENT_GRID_BLOCK]]` /
  `[[SCA_QUALITATIVE_GRID_BLOCK]]` (and the land equivalents) as literal
  markers in the Word template, replaced with generated tables during
  `deliver`, exactly like `[[OWNERSHIP_HISTORY_TABLE]]` and
  `[[COMP_SHEETS_BLOCK]]` today.
- No new Streamlit UI is proposed for v1 (see open questions) — entry stays
  in Excel, since every non-Size/Location value here is a manual judgment
  call, not extracted data, so there's no obvious win yet from a review
  screen the way there was for OCR/comp extraction (which needed a
  keep/skip/edit gate over *extracted* data).
- Existing report injections (`inject_comp_section`, `inject_media_blocks`,
  `inject_ownership_history`) all run conditionally behind
  `doc_cfg.get("inject_comps")` in `axiom.py`'s `deliver` loop. The new
  `adjustment_grid.py` injectors need the same gating decision made
  explicitly (reuse `inject_comps`, or a new `doc_cfg` flag) rather than
  defaulting to always-on and finding out later it should have been
  conditional.

## Testing plan

Mirror the existing deterministic-fixture approach:

- Unit tests for the time-adjustment auto-fill helper (given a monthly rate
  and two dates, assert the correct $ and % for a known case).
- Unit tests confirming `dilmore_factor` reuse reproduces the worked
  examples already spot-checked against the real market-chart files (a real
  office comp/subject GBA pair from one of the inspected files), so the
  size-adjustment column in the new grid matches the real files exactly,
  not just the function's own docstring example.
- A synthetic-workbook fixture (`sca_adjustment_grid` + `sca_qualitative`
  sheets populated with known values) run through `adjustment_grid.py`'s
  injector → assert the generated docx table's cell text matches the
  expected computed values, including Net Adjustment and Indicated Value.
  Since Size/Time/Net Adjustment/Indicated Value are Excel formulas (see
  Pipeline step 6), the fixture must go through a real calculation pass
  (e.g. headless LibreOffice recalculation before the injector reads it
  with `data_only=True`) — writing raw values directly via openpyxl would
  test the injector's table-building logic but not the formula chain it
  actually depends on in production.
- A land-sales equivalent fixture and injector test, including a case that
  exercises the reconciled `land`/`land_adjustment_grid` relationship
  chosen in Pipeline step 2 (confirm `LAND_ADJUSTMENT_NARRATIVE` and the
  new grid agree on the same comp's numbers).
- A regression test for `cmd_dilmore` (Pipeline step 0) — none exists today;
  add one before or alongside whichever fix/retire decision is made, so this
  path can't silently break again.
- Header-mismatch test: a fixture sheet with a header the injector doesn't
  recognize should raise a loud, specific error, not silently skip the
  column (per the drift-protection note in Pipeline step 5).
- Regression: all existing tests (84/84 as of the last stress-test-follow-up
  commit) and `python axiom.py contract` must stay green; the four new block
  registrations and any new field_registry fields must pass the same
  contract-drift check everything else does, including the new
  registry→template direction of that check.

## Open questions

a. **Qualitative Overall threshold.** Sum or average of factor scores, and
   what cutoff maps to Superior/Similar/Inferior (e.g. average > +0.3 →
   Superior, < -0.3 → Inferior, else Similar)? Derek confirmed
   sum/average as the mechanism but hasn't picked the exact threshold yet.
b. **Streamlit UI scope for v1.** Recommend Excel-only manual entry for v1
   (no new review screen) since every new value here is judgment-entry, not
   extracted data needing a keep/skip gate — open to revisiting if Derek
   wants a grid-entry screen instead of raw Excel.
c. **Who edits the master template's new markers.** Recommend Claude adds
   the four `[[...]]` markers to the template with Derek reviewing the diff
   before delivery-testing, rather than Derek hand-editing the template —
   but this is Derek's call given how central that template is.
d. **Rollout order.** Recommend office/retail/industrial first (matches the
   majority — 7 of 10 — of the real files inspected), land second, with
   apartment's minor variant (adds Price Per Unit / Amenities, drops
   Traffic) picked up as part of whichever of the first two slices lands
   first, since apartment reuses the same shape with a smaller diff than
   land does.
e. **Back-compat for in-flight assignments.** Assignment workbooks already
   engaged before this ships won't have the new tabs. Does `deliver` need to
   detect a missing `sca_adjustment_grid`/`land_adjustment_grid` tab and
   skip the new blocks gracefully (matching how `LAND_ADJUSTMENT_NARRATIVE`
   already skips with a warning when its input tab is empty), or is a
   one-time migration step needed to add the new tabs to already-engaged
   workbooks? Recommend the graceful-skip approach, consistent with
   existing patterns elsewhere in the platform.
   **Resolved (implemented):** the graceful-skip approach was taken.
   `axiom.py`'s `_DILMORE_TAB_LAYOUTS` detects whichever of
   `sca_adjustment_grid` (current) or `size_adj` (pre-Phase-6) tab a given
   workbook actually has and uses the matching column layout; no forced
   migration exists. Confirmed still correct through the 2026-07-11
   hardening rounds (see `HANDOFF.md`) — `size_adj` intentionally keeps its
   original unconditional row-7-16 scan since it predates the "Sale No."
   anchor convention `sca_adjustment_grid` uses.
f. **Two qualitative-grid conventions living side by side.** After this
   ships, the platform will have the existing text-based lease-comp
   `qualitative_analysis` tab (Superior/Similar/Inferior as labels) *and*
   the new numeric 0/1/-1 sale/land qualitative tabs — two different
   conventions for conceptually the same kind of grid. Worth flagging
   explicitly rather than letting it happen implicitly: should the lease
   grid eventually move to the same numeric scale for consistency (future
   slice, not this one), or is keeping lease qualitative purely
   text/narrative-driven an intentional, permanent difference? No action
   needed for v1 either way, but this shouldn't be an accidental
   inconsistency Derek discovers later.
g. **Excel-formula vs. Python-computed grids — confirm the recommended
   default.** Pipeline step 6 recommends keeping Size/Time/Net
   Adjustment/Indicated Value as Excel formulas (matching `size_adj`/
   `dilmore` today) with `adjustment_grid.py` reading computed results via
   `data_only=True`, rather than moving that math into Python. This affects
   how test fixtures must be built (a real calculation pass is required,
   not just cell values written via openpyxl) — flagging so this default
   gets explicit sign-off rather than being assumed.
   **Resolved, partially against the recommendation:** per Derek's explicit
   choice (2026-07-10), Dilmore's Size Factor/Adj % specifically stay a
   *tested Python calculation* (`_run_dilmore_calc` in `axiom.py`), not a
   live Excel formula — Time Adj %/Net Adjustment/Indicated Value remain
   Excel formulas as originally recommended. The tradeoff this creates
   (openpyxl's `wb.save()` after any real Python write silently discards
   every OTHER cached formula result workbook-wide, requiring Derek to
   manually recalculate/save in Excel before the next delivery) was the
   subject of round-3 hardening finding P1 — see `HANDOFF.md`, "Completed
   this session (Claude, Phase 6 hardening rounds 1-4 — 2026-07-11)" — and
   is a direct, foreseeable consequence of this choice, not a separate bug.
