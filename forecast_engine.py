"""
forecast_engine.py — Axiom Commercial Appraisal Platform
==========================================================
Cash-flow-pattern forecasting engine, built per the Appraisal Institute's
*General Appraiser Income Approach/Part 2* course (PC404GCH-N), Part 3
("Forecasting Cash Flows") and Part 14 ("Income Patterns").

Generates the cash-flow sequences dcf_engine.py's functions consume as
given inputs. Reuses direct_cap_engine.compute_egi/compute_noi for the
per-year NOI assembly rather than re-deriving that math.

The three named income patterns (Part 14) map onto a small, reusable set
of generators rather than three separate implementations:
  - Compound rate of change: CF_t = CF_1 * (1+CR)^(t-1) -- the SAME
    formula covers both growing an individual income/expense line item
    year over year (Part 3's forecasting technique) and the named
    "Compound Rate of Change Income Pattern" itself (Part 14).
  - Level: CF_t = constant -- trivial, but named explicitly in the source
    material.
  - Irregular: no generator needed -- dcf_engine.discounted_cash_flow_value
    already accepts an arbitrary list, which IS the irregular pattern.

Confirmed, verified cross-check ("level equivalence"): a level $50,000/yr
10-year annuity, an irregular 10-year stream, and a 10-year 2%-compound-
growth stream all produce the identical PV at the same discount rate --
the source material's own demonstration that these three patterns are
just different representations of the same underlying value when their
PVs happen to match.
"""

from direct_cap_engine import compute_egi, compute_noi


class ForecastEngineError(Exception):
    """Raised on invalid input -- mirrors dcf_engine.py's DCFEngineError:
    fail loudly rather than silently miscompute."""


def compound_growth_series(first_year_value, growth_rate, periods):
    """CF_t = CF_1 * (1+growth_rate)^(t-1) for t = 1..periods. Confirmed
    exact formula for both multi-year income/expense line-item forecasting
    (Part 3) and the named Compound Rate of Change Income Pattern (Part
    14) -- the same math either way. A negative growth_rate models a
    declining pattern (confirmed valid by the source material)."""
    if periods < 1:
        raise ForecastEngineError("compound_growth_series requires periods >= 1")
    return [first_year_value * (1 + growth_rate) ** t for t in range(periods)]


def level_series(value, periods):
    """CF_t = value for every period -- the Level Income Pattern."""
    if periods < 1:
        raise ForecastEngineError("level_series requires periods >= 1")
    return [value] * periods


def forecast_noi_series(pgi_year1, pgi_growth_rate, vacancy_collection_loss_pct,
                          fixed_expenses_year1, fixed_growth_rate,
                          variable_expenses_year1, variable_growth_rate,
                          periods,
                          other_income_year1=0.0, other_income_growth_rate=0.0,
                          reimbursements_year1=0.0, reimbursements_growth_rate=0.0):
    """Assembles a full year-by-year NOI forecast, reusing
    direct_cap_engine.compute_egi/compute_noi per year rather than
    re-deriving the PGI->EGI->NOI math. Confirmed convention: fixed and
    variable expenses conventionally grow at DIFFERENT rates than income
    (Part 3, worked example: income 4%, fixed 3%, variable 5%)."""
    pgi_series = compound_growth_series(pgi_year1, pgi_growth_rate, periods)
    fixed_series = compound_growth_series(fixed_expenses_year1, fixed_growth_rate, periods)
    variable_series = compound_growth_series(variable_expenses_year1, variable_growth_rate, periods)
    other_income_series = compound_growth_series(other_income_year1, other_income_growth_rate, periods)
    reimbursements_series = compound_growth_series(reimbursements_year1, reimbursements_growth_rate, periods)

    noi_series = []
    for pgi, fixed, variable, other_income, reimbursements in zip(
            pgi_series, fixed_series, variable_series, other_income_series, reimbursements_series):
        egi_result = compute_egi(pgi, vacancy_collection_loss_pct,
                                  reimbursements=reimbursements, other_income=other_income)
        noi_result = compute_noi(egi_result.egi, fixed, variable)
        noi_series.append(noi_result.noi)
    return noi_series


def apply_below_the_line_items(noi_series, items):
    """Deducts capital expenditures/TIs/leasing commissions in the
    SPECIFIC year(s) they occur (Part 3, p.83-85) -- DCF treats these as a
    per-year deduction, unlike Direct Capitalization's one-time
    post-processing value adjustment. `items` is a sparse {year: amount}
    mapping, 1-indexed (year 1 is noi_series[0])."""
    result = list(noi_series)
    for year, amount in items.items():
        if not isinstance(year, int):
            raise ForecastEngineError(
                f"below-the-line item year must be an int, got {year!r}"
            )
        if year < 1 or year > len(result):
            raise ForecastEngineError(
                f"below-the-line item year {year} is out of range for a "
                f"{len(result)}-period series"
            )
        result[year - 1] -= amount
    return result


def net_reversion(gross_reversion, expenses_of_sale_pct):
    """Reversion_net = Reversion_gross * (1 - expenses_of_sale_pct) --
    Part 3's confirmed refinement on top of direct_cap_engine's plain
    reversion_value. A flat-dollar (not percentage) selling cost needs no
    dedicated function -- plain subtraction suffices."""
    return gross_reversion * (1 - expenses_of_sale_pct)


def deduct_deferred_maintenance(value_as_cured, cost_to_cure):
    """Deferred maintenance is explicitly NOT a below-the-line expense
    (Part 3, p.84) -- it is deducted from the resulting VALUE, never from
    any year's cash flow. Confirmed procedure: forecast as if already
    cured, discount that stream, then deduct the cost-to-cure once here."""
    return value_as_cured - cost_to_cure


def implied_growth_rate(yield_rate, cap_rate):
    """CR = Y - R. Holds ONLY under the "frozen rate," perpetual-growth
    premise (Part 16): income and value both growing at the same constant
    rate CR forever, with a capitalization rate that never changes over
    time -- a materially stronger assumption than the finite-horizon
    compound_growth_series forecasting elsewhere in this module. Do not
    use this to cross-check a finite-holding-period DCF with a terminal
    reversion unless the terminal rate is also set to Y-CR and growth is
    assumed to continue unabated beyond the holding period."""
    return yield_rate - cap_rate


def implied_yield_rate(cap_rate, growth_rate):
    """Y = R + CR -- same frozen-rate/perpetual-growth premise as
    implied_growth_rate."""
    return cap_rate + growth_rate


def implied_cap_rate_from_growth(yield_rate, growth_rate):
    """R = Y - CR -- same frozen-rate/perpetual-growth premise as
    implied_growth_rate."""
    return yield_rate - growth_rate
