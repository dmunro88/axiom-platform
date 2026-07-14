"""
tvm_engine.py — Axiom Commercial Appraisal Platform
=====================================================
Time Value of Money / Six Functions of a Dollar calculation engine, built
per the Appraisal Institute's *General Appraiser Income Approach/Part 1*
course (PC403GCH-M), Parts 2-4, and its Solutions Booklet (PC403GSB-M).

This is the shared foundation that Phase 3b (DCF/yield capitalization,
*Income Approach/Part 2*) will build on, and it closes a gap left open by
`direct_cap_engine.py` (Phase 2): `mortgage_capitalization_rate` derives
the band-of-investment mortgage rate directly from loan terms, rather than
requiring it as a raw given input.

Every factor formula below is independently verified against the
textbook's own printed 6%, n=1-30 factor table (all 30 rows, all 6
factors) and cross-checked against solutions-booklet worked problems.

Sign convention — a deliberate departure from the textbook's own HP-12C
convention (money out negative, money in positive, because that's how a
financial calculator's registers work). This module instead uses plain
positive magnitudes for every factor-based function -- direction is
implied by which function you call, not a sign flip, matching how
sca_engine.py/direct_cap_engine.py already handle directional quantities.
The one exception is solve_yield_rate, which genuinely solves an
NPV-style equation with mixed-direction cash flows and must accept signed
values to be meaningful.

Ordinary annuity (payment at END of period, "in arrears") is the default
throughout, per the course's own explicit convention ("cash flows are
always in arrears unless the problem specifies otherwise").

Explicitly out of scope (see project plan/HANDOFF.md): solving for an
unknown term (n) -- no verified worked example was found to test it
against.
"""


class TVMEngineError(Exception):
    """Raised on invalid input (e.g. a zero rate where none is meaningful,
    or a root-finding failure) -- mirrors sca_engine.py's SCAEngineError
    and direct_cap_engine.py's DirectCapEngineError: fail loudly rather
    than silently miscompute."""


# ── Six Functions of a Dollar — factors ─────────────────────────────────────


def future_value_factor(rate, periods):
    """(1+i)^n -- Future Value of 1."""
    return (1 + rate) ** periods


def present_value_factor(rate, periods):
    """1/(1+i)^n -- Present Value of 1. Reciprocal of future_value_factor."""
    return 1 / (1 + rate) ** periods


def future_value_annuity_factor(rate, periods):
    """[(1+i)^n - 1] / i -- Future Value of an Annuity of 1 (ordinary/arrears)."""
    if rate == 0:
        return float(periods)
    return ((1 + rate) ** periods - 1) / rate


def sinking_fund_factor(rate, periods):
    """i / [(1+i)^n - 1] -- Sinking Fund Factor. Reciprocal of
    future_value_annuity_factor."""
    if rate == 0:
        if periods == 0:
            raise TVMEngineError("sinking_fund_factor requires periods > 0")
        return 1.0 / periods
    return rate / ((1 + rate) ** periods - 1)


def present_value_annuity_factor(rate, periods):
    """[1 - 1/(1+i)^n] / i -- Present Value of an Annuity of 1 (ordinary/arrears)."""
    if rate == 0:
        return float(periods)
    return (1 - 1 / (1 + rate) ** periods) / rate


def installment_to_amortize_factor(rate, periods):
    """i / [1 - 1/(1+i)^n] -- Installment to Amortize 1 (mortgage constant /
    partial payment factor). Reciprocal of present_value_annuity_factor.
    Confirmed identity: sinking_fund_factor(rate, periods) + rate ==
    installment_to_amortize_factor(rate, periods)."""
    if rate == 0:
        if periods == 0:
            raise TVMEngineError("installment_to_amortize_factor requires periods > 0")
        return 1.0 / periods
    return rate / (1 - 1 / (1 + rate) ** periods)


# ── Applied convenience functions ────────────────────────────────────────────


def future_value(present_value_amount, rate, periods):
    """FV = PV x (1+i)^n."""
    return present_value_amount * future_value_factor(rate, periods)


def present_value(future_value_amount, rate, periods):
    """PV = FV / (1+i)^n."""
    return future_value_amount * present_value_factor(rate, periods)


def future_value_of_annuity(payment, rate, periods):
    """FV of a level ordinary annuity of `payment` per period."""
    return payment * future_value_annuity_factor(rate, periods)


def sinking_fund_payment(future_value_target, rate, periods):
    """Level end-of-period deposit required to accumulate to
    `future_value_target` by the end of `periods`."""
    return future_value_target * sinking_fund_factor(rate, periods)


def present_value_of_annuity(payment, rate, periods):
    """PV of a level ordinary annuity of `payment` per period."""
    return payment * present_value_annuity_factor(rate, periods)


def mortgage_payment(loan_amount, rate, periods):
    """Level end-of-period payment that fully amortizes `loan_amount`
    over `periods` at periodic rate `rate`."""
    return loan_amount * installment_to_amortize_factor(rate, periods)


def loan_balance(loan_amount, rate, total_periods, elapsed_periods):
    """Outstanding principal after `elapsed_periods` of `total_periods`
    have been paid -- the present value of the remaining payments."""
    if elapsed_periods < 0 or elapsed_periods > total_periods:
        raise TVMEngineError("elapsed_periods must be between 0 and total_periods")
    payment = mortgage_payment(loan_amount, rate, total_periods)
    remaining = total_periods - elapsed_periods
    return present_value_of_annuity(payment, rate, remaining)


def present_value_annuity_due(pv_ordinary, rate):
    """Converts a present value computed as an ordinary annuity (payments
    in arrears) to its annuity-due (payments in advance) equivalent --
    valid for level annuities only."""
    return pv_ordinary * (1 + rate)


def periodic_rate(nominal_annual_rate, periods_per_year):
    """A nominal annual rate divided by compounding periods per year --
    NOT an effective-rate conversion (confirmed textbook convention)."""
    return nominal_annual_rate / periods_per_year


def effective_annual_rate(nominal_annual_rate, periods_per_year):
    """EAR = (1 + periodic_rate)^periods_per_year - 1."""
    i = periodic_rate(nominal_annual_rate, periods_per_year)
    return (1 + i) ** periods_per_year - 1


def present_value_with_reversion(payment, rate, periods, reversion):
    """PV of a level ordinary annuity plus a lump-sum reversion at the end
    of the same period range -- simply the sum of the two component
    present values."""
    return (present_value_of_annuity(payment, rate, periods)
            + present_value(reversion, rate, periods))


def mortgage_capitalization_rate(nominal_annual_rate, periods_per_year, amortization_years):
    """R_M = ITAO(periodic_rate, total_periods) x periods_per_year --
    derives the mortgage capitalization rate (annual loan constant)
    directly from loan terms, with no principal or payment needed first.
    Closes the gap direct_cap_engine.py's band_of_investment_mortgage_equity
    left open (it currently takes R_M as a raw given input)."""
    i = periodic_rate(nominal_annual_rate, periods_per_year)
    n = periods_per_year * amortization_years
    return installment_to_amortize_factor(i, n) * periods_per_year


def solve_yield_rate(present_value_amount, payment, future_value_amount, periods,
                       tolerance=1e-9, max_iterations=200):
    """Solves for the periodic yield rate `i` satisfying:
        present_value_amount + payment x PVA_factor(i, periods)
            + future_value_amount x PV_factor(i, periods) = 0

    Unlike every other function in this module, this uses SIGNED cash
    flows (the textbook's own calculator convention) because it is
    genuinely solving an equation with mixed-direction cash flows, not
    just applying a formula -- the textbook itself has no closed form for
    this and teaches it as a black-box financial-calculator solve. Uses
    bisection (no new dependency) since no closed form exists.
    """
    def npv(rate):
        return (present_value_amount
                + payment * present_value_annuity_factor(rate, periods)
                + future_value_amount * present_value_factor(rate, periods))

    low, high = -0.99, 10.0
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        raise TVMEngineError(
            "solve_yield_rate could not bracket a root in [-99%, 1000%]; "
            "check the sign convention of present_value_amount/payment/"
            "future_value_amount"
        )

    for _ in range(max_iterations):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if abs(npv_mid) < tolerance:
            return mid
        if npv_low * npv_mid < 0:
            high = mid
            npv_high = npv_mid
        else:
            low = mid
            npv_low = npv_mid

    raise TVMEngineError("solve_yield_rate did not converge")
