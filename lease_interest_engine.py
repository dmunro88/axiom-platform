"""
lease_interest_engine.py — Axiom Commercial Appraisal Platform
=====================================================
Lease-interest (leased fee / leasehold / sandwich leasehold / subleasehold)
calculation engine, built per the Appraisal Institute's *General Appraiser
Income Approach/Part 2* course (PC404GCH-M), Part 11 ("Lease Analysis"),
and its Solutions Booklet (PC404GSB-N).

Deliberately thin, matching mortgage_equity_engine.py's "reuse, don't
re-derive" design: valuing any single interest's income+reversion stream
is done by the caller directly via dcf_engine.discounted_cash_flow_value
or tvm_engine.present_value_with_reversion -- this module does not wrap
that math again. The only genuinely new domain logic is how each
interest's net income is derived from gross rent collected/paid, and
percentage/overage rent.

The step-up-lease-paid-in-advance case (this course's 6.4 Problem) needs
no new code here -- it is already implemented and tested via
dcf_engine.present_value_income_in_advance.

Confirmed, explicit common errors from the source material (Part 11
terminology section, Thought Questions 11.2/11.3):
  - V_O = V_LF + V_LH (fee simple = leased fee + leasehold) holds only in
    a "perfect market" -- real appraisals usually do NOT satisfy this
    exactly. fee_simple_reconciliation_gap exposes this gap rather than
    asserting or forcing it to be zero.
  - Yield-rate ordering Y_LF < Y_LH < Y_SLH (leased fee lowest-risk/
    contractually senior, subleasehold highest-risk/residual) --
    lease_yield_rate_ordering_is_plausible is a documented sanity check
    only, mirroring mortgage_equity_engine.yield_rate_ordering_is_plausible:
    it does not compute one rate from the others.
  - When a split-rate approach is used, only the income stream gets the
    different (often lower) rate -- the reversion is discounted at the
    property's own risk. This is exactly what dcf_engine.split_rate_value
    already does; no new function needed here.

Explicitly out of scope: excess rent, deficit rent, and effective-rent
calculation methods (defined in the source material but no worked
numeric example exists anywhere in the chapter), and the property-model
leased-fee formula R_LF = Y_LF - Delta*(1/S_n) (deferred to the
already-roadmapped Ellwood-style property-model phase).
"""


class LeaseInterestEngineError(Exception):
    """Raised on invalid input -- mirrors the other calc-engine modules'
    fail-loudly exception classes."""


def net_income_to_interest(rent_collected, rent_paid):
    """The literal "Net Income to Property Interest" column of the
    course's own component summary grid -- the single formula that
    uniformly produces the net income for every interest type:
      - Leased fee: rent collected (contract rent), nothing paid out.
      - Sandwich leasehold: sub-rent collected minus ground rent paid.
      - Subleasehold: market-rent value "collected" minus actual rent
        paid -- i.e. the below-market savings the sublessee enjoys, not
        cash actually received.
      - Fee simple: market rent, nothing paid out.
    """
    return rent_collected - rent_paid


def overage_rent(base_rent, breakpoint_sales, actual_sales, overage_rate):
    """Percentage/overage rent: base_rent + overage_rate x max(0,
    actual_sales - breakpoint_sales). All figures in TOTAL dollars --
    if working from per-area figures (e.g. sales per square foot),
    the caller multiplies by area first, matching the course's own
    worked approach."""
    excess_sales = max(0.0, actual_sales - breakpoint_sales)
    return base_rent + overage_rate * excess_sales


def lease_yield_rate_ordering_is_plausible(leased_fee_rate, leasehold_rate, subleasehold_rate):
    """Sanity check only -- per this module's documented warning that a
    "perfect market" sum-of-parts identity is a pedagogical convenience,
    not a guarantee, this does NOT compute one rate from the others. It
    only checks the ordering Y_LF < Y_LH < Y_SLH confirmed by every
    worked example in the source material. A False result doesn't
    necessarily mean an error -- just something worth a second look."""
    return leased_fee_rate < leasehold_rate < subleasehold_rate


def fee_simple_reconciliation_gap(fee_simple_value, *component_values):
    """fee_simple_value - sum(component_values). Returns the numeric gap
    rather than a boolean/forced-equal assertion -- the source material
    is explicit that V_O = V_LF + V_LH (or the finer leased fee/sandwich/
    subleasehold split) only holds in a "perfect market." A nonzero gap
    is expected and is not itself evidence of an error; a caller judges
    whether the size of the gap looks reasonable for the property and
    market in question."""
    return fee_simple_value - sum(component_values)
