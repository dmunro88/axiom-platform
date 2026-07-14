"""
tests/test_lease_interest_engine.py — Axiom Platform

Regression coverage for lease_interest_engine.py, the lease-interest
(leased fee/leasehold/sandwich leasehold/subleasehold) engine built per
the Appraisal Institute's General Appraiser Income Approach/Part 2
course, Part 11 ("Lease Analysis") and Self-Study Practice Problems,
Sections 5 & 6.

Every test cites its source problem number and asserts against a value
independently recomputed in Python during test authoring. Includes
cross-module integration tests against tvm_engine.py/dcf_engine.py, since
this module exists specifically to feed those for valuation.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dcf_engine import internal_rate_of_return
from tvm_engine import present_value_of_annuity, present_value_with_reversion
from lease_interest_engine import (
    fee_simple_reconciliation_gap,
    lease_yield_rate_ordering_is_plausible,
    net_income_to_interest,
    overage_rent,
)


class NetIncomeToInterestTests(unittest.TestCase):
    """Part 12 Practice Test Question 4: ground lease/sandwich/
    subleasehold/fee simple, $30,000 ground rent, $65,000 sub-rent,
    $90,000 market rent."""

    def test_leased_fee(self):
        self.assertAlmostEqual(30_000, net_income_to_interest(30_000, 0))

    def test_sandwich(self):
        self.assertAlmostEqual(35_000, net_income_to_interest(65_000, 30_000))

    def test_subleasehold(self):
        self.assertAlmostEqual(25_000, net_income_to_interest(90_000, 65_000))

    def test_fee_simple(self):
        self.assertAlmostEqual(90_000, net_income_to_interest(90_000, 0))


class FourInterestSplitTests(unittest.TestCase):
    """Part 12 Practice Test Question 4: 5-year level income, $1,000,000
    reversion to the leased fee only, yields 10% (LF)/15% (sandwich)/11%
    (fee simple) given; subleasehold value found residually and its
    implied yield solved -> 20.40%. The problem explicitly states the
    interests sum to fee simple."""

    def test_full_split_and_implied_yield(self):
        v_lf = present_value_with_reversion(30_000, 0.10, 5, 1_000_000)
        self.assertAlmostEqual(734_645, v_lf, delta=1.0)

        v_fs = present_value_with_reversion(90_000, 0.11, 5, 1_000_000)
        self.assertAlmostEqual(926_082, v_fs, delta=1.0)

        v_sw = present_value_with_reversion(35_000, 0.15, 5, 0)
        self.assertAlmostEqual(117_325, v_sw, delta=1.0)

        v_slh = v_fs - v_lf - v_sw
        self.assertAlmostEqual(74_112, v_slh, delta=1.0)

        y_slh = internal_rate_of_return(v_slh, [25_000] * 5, 0)
        self.assertAlmostEqual(0.2040, y_slh, places=3)

        gap = fee_simple_reconciliation_gap(v_fs, v_lf, v_sw, v_slh)
        self.assertAlmostEqual(0, gap, delta=1.0)

        self.assertTrue(lease_yield_rate_ordering_is_plausible(
            leased_fee_rate=0.10, leasehold_rate=0.15, subleasehold_rate=y_slh,
        ))


class TwoWaySplitTests(unittest.TestCase):
    """Self-Study Sections 5 & 6 Problem 33: leased fee + undivided
    leasehold, 5-year lease, $22,000 Year-6 income capitalized at a 9%
    terminal rate -> $244,444 reversion. Leased fee discounted at 9.5%,
    fee simple at 10%; leasehold value and yield found residually."""

    def test_split_and_implied_yield(self):
        reversion = 22_000 / 0.09
        self.assertAlmostEqual(244_444, reversion, delta=1.0)

        v_lf = present_value_with_reversion(16_000, 0.095, 5, reversion)
        self.assertAlmostEqual(216_713, v_lf, delta=1.0)

        v_fs = present_value_with_reversion(20_000, 0.10, 5, reversion)
        self.assertAlmostEqual(227_597, v_fs, delta=1.0)

        v_lh = v_fs - v_lf
        self.assertAlmostEqual(10_883, v_lh, delta=1.0)

        i_lh = net_income_to_interest(20_000, 16_000)
        self.assertAlmostEqual(4_000, i_lh, delta=1.0)

        y_lh = internal_rate_of_return(v_lh, [i_lh] * 5, 0)
        self.assertAlmostEqual(0.2443, y_lh, places=3)


class ThreeWaySplitWithDisclosedCorrectionTests(unittest.TestCase):
    """Self-Study Sections 5 & 6 Problem 34: splits Problem 33's
    leasehold into sandwich (sub-rent $18,500/yr) and subleasehold.

    Disclosed discrepancy: the booklet's own component summary grid
    labels the sandwich leasehold's discount rate as "11%" (identically
    in both the "Problems" and "Solutions" printings), but the problem's
    own question text asks for the value "using a 20% discount rate,"
    and the calculator inputs that produce the grid's own printed
    $7,477 answer use i=20, not 11 (independently confirmed: PV at 20%
    is $7,476.53 -> rounds to $7,477; PV at 11% is $9,239.74, nowhere
    close). This is a reproducible booklet transcription error. This
    test uses the correct 20% rate.

    Unlike Question 4 above, this problem never claims the parts sum to
    fee simple -- sandwich and subleasehold are valued independently off
    their own contract cash flows at their own rates, not as a forced
    residual off the fee simple total. fee_simple_reconciliation_gap is
    asserted to be the genuinely nonzero ~$246 gap it is, not forced to
    zero."""

    def test_sandwich_and_subleasehold_income(self):
        i_sw = net_income_to_interest(18_500, 16_000)
        self.assertAlmostEqual(2_500, i_sw, delta=1.0)

        i_slh = net_income_to_interest(20_000, 18_500)
        self.assertAlmostEqual(1_500, i_slh, delta=1.0)

    def test_sandwich_value_uses_corrected_20_percent_rate(self):
        v_sw = present_value_of_annuity(2_500, 0.20, 5)
        self.assertAlmostEqual(7_477, v_sw, delta=1.0)

        v_sw_at_mislabeled_rate = present_value_of_annuity(2_500, 0.11, 5)
        self.assertAlmostEqual(9_240, v_sw_at_mislabeled_rate, delta=1.0)
        self.assertNotAlmostEqual(7_477, v_sw_at_mislabeled_rate, delta=100)

    def test_subleasehold_value(self):
        v_slh = present_value_of_annuity(1_500, 0.30, 5)
        self.assertAlmostEqual(3_653, v_slh, delta=1.0)

    def test_reconciliation_gap_is_genuinely_nonzero(self):
        v_lf = present_value_with_reversion(16_000, 0.095, 5, 22_000 / 0.09)
        v_fs = present_value_with_reversion(20_000, 0.10, 5, 22_000 / 0.09)
        v_sw = present_value_of_annuity(2_500, 0.20, 5)
        v_slh = present_value_of_annuity(1_500, 0.30, 5)

        gap = fee_simple_reconciliation_gap(v_fs, v_lf, v_sw, v_slh)
        self.assertAlmostEqual(-246.60, gap, delta=1.0)

    def test_yield_ordering(self):
        self.assertTrue(lease_yield_rate_ordering_is_plausible(
            leased_fee_rate=0.095, leasehold_rate=0.20, subleasehold_rate=0.30,
        ))


class OverageRentTests(unittest.TestCase):
    """Self-Study Sections 1 & 2 Problem 34 "Phone Shak": 2,000 sq. ft.,
    $15/sq. ft. base rent, breakpoint $300/sq. ft., overage rate 5%,
    sales growing 5%/yr from $300/sq. ft. -> total rent $30,000 /
    $31,500 / $33,075 / $34,728.75 (rounds to $34,729)."""

    def test_four_year_schedule(self):
        base_rent = 15 * 2_000
        breakpoint_sales = 300 * 2_000
        sales_per_sf = [300, 315, 330.75, 330.75 * 1.05]
        expected = [30_000, 31_500, 33_075, 34_728.75]

        for sf_sales, exp in zip(sales_per_sf, expected):
            actual_sales = sf_sales * 2_000
            total_rent = overage_rent(base_rent, breakpoint_sales, actual_sales, 0.05)
            self.assertAlmostEqual(exp, total_rent, delta=0.01)

    def test_no_overage_when_sales_below_breakpoint(self):
        rent = overage_rent(base_rent=30_000, breakpoint_sales=600_000,
                              actual_sales=500_000, overage_rate=0.05)
        self.assertAlmostEqual(30_000, rent, delta=0.01)


class YieldOrderingTests(unittest.TestCase):
    def test_implausible_ordering_returns_false(self):
        self.assertFalse(lease_yield_rate_ordering_is_plausible(
            leased_fee_rate=0.20, leasehold_rate=0.15, subleasehold_rate=0.25,
        ))


if __name__ == "__main__":
    unittest.main()
