"""
dcf_engine.py — Axiom Commercial Appraisal Platform
=====================================================
Core Discounted Cash Flow (DCF) / yield capitalization calculation engine,
built per the Appraisal Institute's *General Appraiser Income Approach/
Part 2* course (PC404GCH-N), Parts 1, 2, 4-6, and its Solutions Booklet
(PC404GSB-N).

Builds directly on tvm_engine.py (Phase 3a): level-equivalent annuity
reuses installment_to_amortize_factor, split-rate/income-in-advance
handling reuses present_value_factor.

The general DCF formula:
    V = sum(CF_j / (1+Y)^j for j in 1..n) + Reversion / (1+Y)^n

The single most common DCF error the source material catalogs is putting
the reversion in its own, separate period rather than combining it with
the final period's income into one number. This module's function
signatures make that error structurally impossible -- callers pass
periodic income and reversion as separate arguments; the functions combine
them internally.

No function in this module selects a final concluded value or judges
whether a computed rate is "correct" -- matching the design principle
already established in sca_engine.py/direct_cap_engine.py.
"""

from tvm_engine import installment_to_amortize_factor, present_value_factor


class DCFEngineError(Exception):
    """Raised on invalid input or a root-finding failure -- mirrors
    tvm_engine.py's TVMEngineError: fail loudly rather than silently
    miscompute."""


def _present_value_of_series(cash_flows, rate):
    """Internal helper: PV of a plain, arrears-timed cash-flow sequence
    (periods 1..n), no reversion. Shared by every public function below so
    the summation logic exists in exactly one place."""
    return sum(
        cf * present_value_factor(rate, period)
        for period, cf in enumerate(cash_flows, start=1)
    )


def discounted_cash_flow_value(cash_flows, reversion, rate):
    """V = sum(CF_j / (1+Y)^j) + Reversion / (1+Y)^n.

    `cash_flows` is the periodic income for periods 1..n; `reversion` is
    combined into period n internally -- callers never place it in a
    separate period, which is the confirmed most common DCF error in the
    source material."""
    if not cash_flows:
        raise DCFEngineError("discounted_cash_flow_value requires at least one cash flow")
    n = len(cash_flows)
    pv_income = _present_value_of_series(cash_flows, rate)
    pv_reversion = reversion * present_value_factor(rate, n)
    return pv_income + pv_reversion


def net_present_value(capital_outlay, cash_flows, reversion, rate):
    """NPV = PV(benefits) - Capital Outlay."""
    pv_benefits = discounted_cash_flow_value(cash_flows, reversion, rate)
    return pv_benefits - capital_outlay


def internal_rate_of_return(capital_outlay, cash_flows, reversion,
                              tolerance=1e-12, max_iterations=200):
    """Solves for the yield rate Y at which NPV = 0. The textbook has no
    closed form for this -- it is always solved via calculator iteration,
    exactly like tvm_engine.solve_yield_rate for the simpler level-annuity
    case; this generalizes that same bisection approach to an irregular
    cash-flow vector.

    `tolerance` is a bisection INTERVAL-WIDTH tolerance in RATE terms, not
    an NPV/dollar tolerance -- an NPV-magnitude check fails to converge
    for institutional-scale cash flows (float precision near the root is
    far coarser in dollar terms than a fixed tolerance once outlays reach
    the millions), and can converge too early (to a materially wrong
    rate) at very small dollar magnitudes. See tvm_engine.solve_yield_rate's
    docstring for the full explanation -- this mirrors the same fix.

    Caveat, confirmed by the source material: cash-flow patterns with more
    than one sign change can have multiple mathematically valid IRRs. This
    function assumes a single sign change/root (true of every worked
    example in the source material) and does not detect or enumerate
    multiple roots.
    """
    def npv(rate):
        return net_present_value(capital_outlay, cash_flows, reversion, rate)

    low, high = -0.99, 10.0
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        raise DCFEngineError(
            "internal_rate_of_return could not bracket a root in "
            "[-99%, 1000%]; this usually indicates a cash-flow sign "
            "convention issue or multiple sign changes (multiple possible "
            "IRRs), though a genuinely extreme yield outside this range "
            "is also possible"
        )

    for _ in range(max_iterations):
        mid = (low + high) / 2
        if (high - low) < tolerance:
            return mid
        npv_mid = npv(mid)
        if npv_low * npv_mid < 0:
            high = mid
            npv_high = npv_mid
        else:
            low = mid
            npv_low = npv_mid

    raise DCFEngineError("internal_rate_of_return did not converge")


def level_equivalent_annuity(cash_flows, reversion, rate):
    """A level annuity with the same present value and number of periods
    as the given irregular cash-flow stream, at the given rate. NOT the
    same as a simple average -- a naive average ignores the time value of
    money (a confirmed, named common error in the source material).

    Step 1: PV of the irregular stream (income + reversion).
    Step 2: solve for the level payment with that same PV over the same n
    periods -- the same math as computing a loan's level payment from its
    present value, reusing tvm_engine.installment_to_amortize_factor.
    """
    n = len(cash_flows)
    pv = discounted_cash_flow_value(cash_flows, reversion, rate)
    return pv * installment_to_amortize_factor(rate, n)


def split_rate_value(cash_flows, income_rate, reversion, reversion_rate):
    """PV_O = PV_Income(at income_rate) + PV_Reversion(at reversion_rate)
    -- used when the income stream and the reversion genuinely warrant
    different discount rates (e.g. income backed by strong credit, but a
    reversion reflecting ordinary re-let market risk). Confirmed
    sanity-check property (not enforced by this function): the resulting
    IRR of the combined cash flows normally falls strictly between
    income_rate and reversion_rate."""
    n = len(cash_flows)
    pv_income = _present_value_of_series(cash_flows, income_rate)
    pv_reversion = reversion * present_value_factor(reversion_rate, n)
    return pv_income + pv_reversion


def present_value_income_in_advance(cash_flows, rate, reversion=0.0):
    """PV where each cash flow in `cash_flows` occurs at the START of its
    period (period 1's payment at time 0, period 2's at time 1, etc.)
    rather than the end -- and, if a reversion is given, it stays
    undisturbed at the END of period n.

    Confirmed common error in the source material: multiplying the WHOLE
    value (income + reversion) by (1+rate) to "shift to advance" is wrong
    -- the reversion's timing never moves. This function only ever
    shifts the income component.

    Mathematically, shifting any cash-flow sequence forward by exactly one
    period is a uniform (1+rate) multiplication of that sequence's own
    arrears-timed present value, regardless of the cash-flow shape (not
    just for level annuities) -- verified against the source material's
    own worked step-up-lease example.
    """
    pv_income_arrears = _present_value_of_series(cash_flows, rate)
    pv_income_advance = pv_income_arrears * (1 + rate)
    n = len(cash_flows)
    pv_reversion = reversion * present_value_factor(rate, n)
    return pv_income_advance + pv_reversion


def dcf_periodic_yield_rate(annual_yield_rate, periods_per_year):
    """Converts an ANNUAL DCF yield rate to its periodic-equivalent rate
    for more-frequent-than-annual discounting.

    NOT the same as tvm_engine.periodic_rate (nominal annual rate divided
    by periods_per_year) -- that conversion is only valid for
    contractually-stated mortgage/loan rates. The source material is
    explicit that switching a DCF to monthly cash flows while naively
    dividing the annual yield rate by 12 overstates value relative to
    proper annual discounting of the same property -- primarily because
    monthly-received income is earned earlier within the year, not
    because Y/12 itself is "too low" (in fact Y/12 is a slightly HIGHER
    periodic rate than this function's correct conversion, since
    compounding more frequently at the same nominal rate always increases
    the effective annual rate -- confirm this yourself: for Y=10%,
    Y/12=0.8333% > dcf_periodic_yield_rate(0.10, 12)=0.7974%). The
    "overstatement" the source material warns about is specifically
    switching cash-flow timing to monthly WITHOUT correctly re-deriving
    the periodic rate this function computes -- it is not a claim that
    Y/12 exceeds the correct rate on the same monthly cash flows (it's the
    reverse: Y/12 is higher, and a higher rate means LOWER present value
    for the same flows). The correct conversion preserves present-value
    equivalence with annual discounting:

        periodic_yield_rate = (1 + annual_yield_rate) ** (1/periods_per_year) - 1

    No worked numeric example exists in the source material for this
    specific conversion -- verified here only by construction (the
    round-trip identity (1+periodic)^periods_per_year == 1+annual holds by
    definition), not against an independent textbook fixture.
    """
    return (1 + annual_yield_rate) ** (1 / periods_per_year) - 1


def implied_overall_rate(first_year_income, value):
    """R_O(implied) = first year's income / value -- the reasonableness
    check the course's own DCF procedure calls for as its final step:
    compare this against whatever terminal capitalization rate was used
    for the reversion. This function only computes the number; it does
    not judge whether the comparison looks reasonable."""
    if value == 0:
        raise DCFEngineError("implied_overall_rate requires a nonzero value")
    return first_year_income / value
