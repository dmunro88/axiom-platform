"""
sca_engine.py — Axiom Commercial Appraisal Platform
====================================================
Sales Comparison Approach calculation engine, ported from Excel to pure
Python per the Appraisal Institute's *General Appraiser Sales Comparison
Approach* course (PC401GCH-M) and its Solutions Booklet (PC401GSB-K), rather
than reverse-engineered from the platform's prior Excel formulas -- a
live-fire test found those formulas had real, previously undiscovered
defects (two unreconciled sales-comparison methodologies, a row-shift bug,
a reversed cap-rate formula, and a quantitative/qualitative scoring split
that never reconciled).

Ten elements of comparison, two groups, one fixed combination rule -- the
transactional group compounds sequentially in a fixed order, each step
against the *running* total left by the previous step; the property group
is summed independently, each adjustment computed against the fixed base
left by the transactional group. Summing every adjustment and applying it
once instead of compounding the transactional group gives a different,
and wrong, answer.

No function in this module selects a final concluded value -- reconciling
multiple comps' indicated values into one number is an appraiser judgment
call, not a calculation.

Pure functions, no I/O, no persistence -- this module knows nothing about
the workbook, the DB, or the delivery pipeline. See docs/-adjacent project
notes for where comp/subject data entry into this module's dataclasses is
expected to be built.
"""

import statistics
from dataclasses import dataclass, field
from typing import Optional, Sequence


# ── Elements of comparison ─────────────────────────────────────────────────

# Fixed order -- transactional adjustments compound sequentially in exactly
# this order, each step against the running total left by the previous step.
TRANSACTIONAL_ORDER = (
    "property_rights",
    "financing_terms",
    "conditions_of_sale",
    "expenditures_after_purchase",
    "market_conditions",
)

# Order among these does not matter -- each is computed independently
# against the fixed base left by the transactional group, then summed.
PROPERTY_ELEMENTS = (
    "location",
    "physical_characteristics",
    "economic_characteristics",
    "use",
    "non_realty_components",
)

STAGE_FOR_ELEMENT = {element: "transactional" for element in TRANSACTIONAL_ORDER}
STAGE_FOR_ELEMENT.update({element: "property" for element in PROPERTY_ELEMENTS})

VALID_KINDS = ("percentage", "dollar")


class SCAEngineError(Exception):
    """Raised when an Adjustment's element/stage/kind is invalid, or when a
    calculation function is handed an adjustment belonging to the wrong
    stage -- mirrors adjustment_grid.py's AdjustmentGridError: fail loudly
    rather than silently miscompute."""


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Adjustment:
    """A single adjustment for one of the ten fixed elements of comparison.

    element : one of TRANSACTIONAL_ORDER / PROPERTY_ELEMENTS
    stage   : "transactional" or "property" -- must match element's actual
              group; a location adjustment tagged stage="transactional" is
              a caller error, raised immediately, not silently coerced.
    kind    : "percentage" or "dollar"
    value   : fraction (0.05 = 5%) or dollar amount
    """

    element: str
    stage: str
    kind: str
    value: float
    note: str = ""

    def __post_init__(self):
        if self.element not in STAGE_FOR_ELEMENT:
            valid = ", ".join(STAGE_FOR_ELEMENT)
            raise SCAEngineError(
                f"unknown element {self.element!r}; must be one of: {valid}"
            )
        expected_stage = STAGE_FOR_ELEMENT[self.element]
        if self.stage != expected_stage:
            raise SCAEngineError(
                f"element {self.element!r} belongs to stage {expected_stage!r}, "
                f"got stage={self.stage!r}"
            )
        if self.kind not in VALID_KINDS:
            raise SCAEngineError(f"kind must be one of {VALID_KINDS}, got {self.kind!r}")


@dataclass(frozen=True)
class ComparableSale:
    identifier: str
    sale_price: float
    adjustments: tuple = ()
    units: dict = field(default_factory=dict)  # e.g. {"gba_sf": 24000, "acres": 1.1}


@dataclass(frozen=True)
class ComparableResult:
    identifier: str
    sale_price: float
    transactional_base: float
    net_property_adjustment: float
    indicated_value: float
    gross_adjustment_pct: float
    net_adjustment_pct: float


@dataclass(frozen=True)
class Stats:
    mean: float
    median: float
    mode: float
    range: float
    stdev: float
    cv: float


# ── Calculation ──────────────────────────────────────────────────────────────


def _transactional_steps(sale_price: float, adjustments: Sequence[Adjustment]):
    """Validate and walk the fixed transactional sequence, returning the
    per-step (element, dollar_delta) list and the final running total.
    Internal helper shared by apply_transactional and indicated_value so
    the latter can compute gross-adjustment dollars without re-deriving
    the compounding math."""
    seen = set()
    for adjustment in adjustments:
        if adjustment.stage != "transactional":
            raise SCAEngineError(
                f"expected a transactional-stage adjustment, got "
                f"stage={adjustment.stage!r} for element {adjustment.element!r}"
            )
        if adjustment.element in seen:
            raise SCAEngineError(
                f"multiple transactional adjustments given for element "
                f"{adjustment.element!r}; combine them into a single "
                "Adjustment before calling apply_transactional"
            )
        seen.add(adjustment.element)

    by_element = {adjustment.element: adjustment for adjustment in adjustments}
    running = sale_price
    steps = []
    for element in TRANSACTIONAL_ORDER:
        adjustment = by_element.get(element)
        if adjustment is None:
            continue
        previous = running
        if adjustment.kind == "percentage":
            running = running * (1 + adjustment.value)
        else:
            running = running + adjustment.value
        steps.append((element, running - previous))
    return steps, running


def apply_transactional(sale_price: float, adjustments: Sequence[Adjustment]) -> float:
    """Compound the fixed-order transactional adjustments sequentially,
    each step against the running total left by the previous step."""
    _, running = _transactional_steps(sale_price, adjustments)
    return running


def apply_property(base: float, adjustments: Sequence[Adjustment]):
    """Sum the property adjustments independently against the fixed base
    (they do not compound against each other or against base). Returns
    (net_adjustment_dollars, indicated_value)."""
    net = 0.0
    for adjustment in adjustments:
        if adjustment.stage != "property":
            raise SCAEngineError(
                f"expected a property-stage adjustment, got "
                f"stage={adjustment.stage!r} for element {adjustment.element!r}"
            )
        if adjustment.kind == "percentage":
            net += base * adjustment.value
        else:
            net += adjustment.value
    return net, base + net


def indicated_value(comp: ComparableSale) -> ComparableResult:
    """Run both stages for one comparable sale and return the full result,
    including the gross/net adjustment percentages the reconciliation case
    studies rank comps by (gross = sum of absolute adjustment dollars,
    across both stages, divided by the original sale price)."""
    transactional = [a for a in comp.adjustments if a.stage == "transactional"]
    property_adjustments = [a for a in comp.adjustments if a.stage == "property"]

    steps, base = _transactional_steps(comp.sale_price, transactional)
    net_property, final_value = apply_property(base, property_adjustments)

    transactional_dollars = sum(abs(delta) for _, delta in steps)
    property_dollars = sum(
        abs(base * a.value) if a.kind == "percentage" else abs(a.value)
        for a in property_adjustments
    )
    gross_dollars = transactional_dollars + property_dollars
    net_dollars = final_value - comp.sale_price

    return ComparableResult(
        identifier=comp.identifier,
        sale_price=comp.sale_price,
        transactional_base=base,
        net_property_adjustment=net_property,
        indicated_value=final_value,
        gross_adjustment_pct=gross_dollars / comp.sale_price,
        net_adjustment_pct=net_dollars / comp.sale_price,
    )


# ── Statistics and unit-of-comparison selection ─────────────────────────────


def unit_price_stats(values: Sequence[float]) -> Stats:
    """Mean, median, mode, range, sample standard deviation, and CV for a
    set of unit-price observations. Sample stdev (n-1), not population --
    the textbook is explicit on this point."""
    values = list(values)
    if len(values) < 2:
        raise SCAEngineError(
            "unit_price_stats requires at least 2 values to compute sample "
            "standard deviation"
        )
    mean_value = statistics.mean(values)
    stdev_value = statistics.stdev(values)
    return Stats(
        mean=mean_value,
        median=statistics.median(values),
        mode=statistics.mode(values),
        range=max(values) - min(values),
        stdev=stdev_value,
        cv=stdev_value / mean_value,
    )


def select_unit_of_comparison(candidates: dict) -> str:
    """Pick the unit of comparison "the market is using": the candidate
    with the lowest coefficient of variation across the comp set."""
    if not candidates:
        raise SCAEngineError("select_unit_of_comparison requires at least one candidate unit")
    cv_by_unit = {
        unit: unit_price_stats(values).cv for unit, values in candidates.items()
    }
    return min(cv_by_unit, key=cv_by_unit.get)


def rank_by_gross_adjustment(results: Sequence[ComparableResult]) -> list:
    """Rank comps ascending by gross adjustment % -- the reconciliation-
    support ordering used by the textbook's case studies (weight most
    heavily toward the comp(s) needing the smallest adjustment). This
    orders data for the appraiser; it does not select a final value."""
    return sorted(results, key=lambda result: result.gross_adjustment_pct)


def inbreeding_warning(num_comps: int, num_solved_adjustments: int) -> Optional[str]:
    """Warn when the number of adjustments being solved for approaches or
    equals (num_comps - 1) drawn entirely from that same closed set -- the
    textbook's "inbreeding of data" caution: this produces a mathematically
    consistent answer that is actually just algebra, not resilient to a
    single bad input price."""
    if num_comps <= 1:
        raise SCAEngineError("inbreeding_warning requires at least 2 comps in the set")
    threshold = num_comps - 1
    if num_solved_adjustments >= threshold:
        return (
            f"Inbreeding of data: solving for {num_solved_adjustments} "
            f"adjustment(s) from a closed set of {num_comps} comps (threshold "
            f"{threshold}) yields a mathematically consistent answer that is "
            "not resilient to a single bad input price."
        )
    return None
