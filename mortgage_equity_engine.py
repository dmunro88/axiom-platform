"""
mortgage_equity_engine.py — Axiom Commercial Appraisal Platform
=====================================================
Mortgage/equity-split (leveraged) DCF calculation engine, built per the
Appraisal Institute's *General Appraiser Income Approach/Part 2* course
(PC404GCH-N), Parts 7-10, and its Solutions Booklet (PC404GSB-N).

Builds directly on tvm_engine.py (mortgage amortization) and dcf_engine.py
(irregular-cash-flow discounting, IRR) -- the only genuinely new domain
logic here is *how to split* a property's cash flows into a mortgage piece
and an equity piece. V_E/Y_E/V_O themselves are not separate functions in
this module: callers combine equity_cash_flows()'s output directly with
dcf_engine.discounted_cash_flow_value / internal_rate_of_return, and
V_O = mortgage_value + V_E is a one-line reconciliation the caller does.

Confirmed only two measures of lender risk exist in this course (no debt
yield ratio, no break-even ratio -- exhaustively searched):
    Loan-to-Value Ratio:  M = V_M / V_O
    Debt Coverage Ratio:  DCR = I_O / I_M   (I_M = annual debt service)

Critical, textbook-explicit warning -- deliberately NOT implemented here:
a yield-rate "band of investment." Unlike the capitalization-rate version
(direct_cap_engine.band_of_investment_mortgage_equity, which correctly
holds), the yield-rate analog is explicitly invalid in general:
    M x Y_M + (1-M) x Y_E != Y_O
(valid only in the narrow case where M stays constant throughout the
hold). Confirmed directly by the source material's own Self-Study Problem
16, which computes both an unlevered property DCF and a levered equity
DCF for the same property and gets two genuinely different implied
property values -- a reasonableness check on rate selection, not an
algebraic identity. No function here computes one rate from the other
two; yield_rate_ordering_is_plausible only checks the expected ordering.

Explicitly out of scope: variable-rate mortgages. The textbook itself
states calculating them is "beyond the scope of this course" and gives no
formula or worked example anywhere in the source material.
"""

from dataclasses import dataclass

from tvm_engine import (
    loan_balance,
    mortgage_payment,
    periodic_rate,
    present_value_of_annuity,
    present_value_with_reversion,
)


class MortgageEquityEngineError(Exception):
    """Raised on invalid input -- mirrors tvm_engine.py's TVMEngineError and
    dcf_engine.py's DCFEngineError: fail loudly rather than silently
    miscompute."""


def debt_coverage_ratio(noi, annual_debt_service):
    """DCR = I_O / I_M. A DCR below 1 means debt service exceeds NOI (a
    negative before-tax equity cash flow), not an invalid input -- so this
    function does not reject it (confirmed by the source material's own
    8.4 Problem, which prints a 0.86 DCR as a normal, if risky, result)."""
    if annual_debt_service == 0:
        raise MortgageEquityEngineError("annual_debt_service cannot be zero")
    return noi / annual_debt_service


def loan_to_value_ratio(mortgage_value, property_value):
    """M = V_M / V_O."""
    if property_value == 0:
        raise MortgageEquityEngineError("property_value cannot be zero")
    return mortgage_value / property_value


def mortgage_amount_from_dcr(noi, dcr, rate, periods_per_year, term_years):
    """Derives the mortgage amount implied by a required DCR, per the
    source material's confirmed exact procedure (8.5/Self-Study #15/#16
    Problems):
        I_M = I_O / DCR
        payment = I_M / periods_per_year
        V_M = present_value_of_annuity(payment, periodic_rate, total_periods)
    """
    if dcr == 0:
        raise MortgageEquityEngineError("dcr cannot be zero")
    annual_debt_service = noi / dcr
    payment = annual_debt_service / periods_per_year
    i = periodic_rate(rate, periods_per_year)
    n = periods_per_year * term_years
    return present_value_of_annuity(payment, i, n)


def cash_equivalent_price(loan_amount, contract_rate, market_rate,
                            periods_per_year, term_years, due_years,
                            down_payment):
    """Confirmed exact 3-step cash equivalence procedure (8.1/8.2 and five
    Self-Study variants):
        Step 1: payment = mortgage_payment(loan_amount, CONTRACT rate, term)
                balance_at_due = loan_balance(loan_amount, CONTRACT rate,
                                               term, due_period)
        Step 2: PV = present_value_with_reversion(payment, MARKET rate,
                                                    due_period, balance_at_due)
        Step 3: cash_equivalent_price = down_payment + PV

    `market_rate` must be the rate in effect when the property sold, not
    the appraisal's effective date -- a source-material-confirmed
    distinction this function's caller is responsible for supplying
    correctly; this function does not know the difference.

    A discouraged alternative method (discounting only the payment/balance
    *difference* between contract and market terms) is explicitly flagged
    by the source material as unnecessarily complex and is not implemented
    here.
    """
    i_contract = periodic_rate(contract_rate, periods_per_year)
    n_total = periods_per_year * term_years
    n_due = periods_per_year * due_years
    payment = mortgage_payment(loan_amount, i_contract, n_total)
    balance_at_due = loan_balance(loan_amount, i_contract, n_total, n_due)
    i_market = periodic_rate(market_rate, periods_per_year)
    pv = present_value_with_reversion(payment, i_market, n_due, balance_at_due)
    return down_payment + pv


@dataclass
class EquityCashFlows:
    """The equity side of a mortgage-equity DCF split. Exposes every
    intermediate value the source material's own worked examples print
    (annual_debt_service, mortgage_balance_at_sale), not just the final
    income/reversion split, so callers and tests can cross-check each step
    independently rather than trusting only the end result."""

    income: list
    reversion: float
    annual_debt_service: float
    mortgage_balance_at_sale: float


def equity_cash_flows(noi_series, mortgage_value, mortgage_rate,
                        periods_per_year, mortgage_term_years, reversion):
    """Splits a property's cash flows into the equity piece, per the
    source material's confirmed "four relationships":
        V_O = V_M + V_E                 (value identity, always exact)
        I_O = I_M + I_E                 (income identity, always exact)
        I_E,t = I_O,t - I_M,t           (constant annual debt service for a
                                         fixed-rate loan)
        Equity_Reversion = Property_Reversion - Mortgage_Balance_at_reversion

    `noi_series` is the property-level NOI for each year of the hold
    (also the hold period, via its length). The mortgage's own
    amortization term (`mortgage_term_years`) may run longer than the hold
    -- the loan need not mature at the reversion date, which is why the
    remaining balance is subtracted from the property reversion rather
    than assumed to be zero.

    V_E/Y_E are deliberately not computed here -- feed this function's
    `income`/`reversion` directly into dcf_engine.discounted_cash_flow_value
    (given Y_E) or dcf_engine.internal_rate_of_return (given V_O - V_M as
    the capital outlay, to solve for Y_E instead)."""
    if not noi_series:
        raise MortgageEquityEngineError("equity_cash_flows requires at least one year of NOI")
    hold_years = len(noi_series)
    i = periodic_rate(mortgage_rate, periods_per_year)
    n_total = periods_per_year * mortgage_term_years
    n_elapsed = periods_per_year * hold_years
    if n_elapsed > n_total:
        raise MortgageEquityEngineError(
            "hold period cannot exceed the mortgage's own amortization term"
        )
    payment = mortgage_payment(mortgage_value, i, n_total)
    annual_debt_service = payment * periods_per_year
    balance_at_sale = loan_balance(mortgage_value, i, n_total, n_elapsed)

    income = [noi - annual_debt_service for noi in noi_series]
    equity_reversion = reversion - balance_at_sale

    return EquityCashFlows(
        income=income,
        reversion=equity_reversion,
        annual_debt_service=annual_debt_service,
        mortgage_balance_at_sale=balance_at_sale,
    )


def yield_rate_ordering_is_plausible(mortgage_rate, overall_yield_rate, equity_yield_rate):
    """Sanity check only -- per this module's documented warning that
    M x Y_M + (1-M) x Y_E != Y_O in general (unlike the cap-rate band of
    investment, which IS valid), this does NOT compute Y_O from Y_M/Y_E.
    It only checks the ordering Y_E > Y_O > Y_M that holds in every worked
    example in the source material. A False result doesn't necessarily
    mean an error in the inputs -- just something worth a second look."""
    return equity_yield_rate > overall_yield_rate > mortgage_rate
