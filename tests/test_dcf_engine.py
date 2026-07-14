"""
tests/test_dcf_engine.py — Axiom Platform

Regression coverage for dcf_engine.py, the core Discounted Cash Flow
calculation engine built per the Appraisal Institute's General Appraiser
Income Approach/Part 2 course (Parts 1, 2, 4-6).

Every test cites its source problem and asserts against a value
independently recomputed in Python during test authoring. Two exceptions,
explicitly disclosed: the "more frequent compounding" fixture (no worked
numeric example exists in this material -- verified only by construction),
and the reasonableness-check fixture (trivial division, no citation
needed).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dcf_engine import (
    DCFEngineError,
    dcf_periodic_yield_rate,
    discounted_cash_flow_value,
    implied_overall_rate,
    internal_rate_of_return,
    level_equivalent_annuity,
    net_present_value,
    present_value_income_in_advance,
    split_rate_value,
)


class GeneralDCFFormulaTests(unittest.TestCase):
    def test_part2_review_quiz_q4(self):
        """Part 2, Review Quiz Q4: 5-year irregular income
        140k/150k/160k/170k/180k plus a $2,500,000 reversion, 8% discount
        rate -> $2,334,161.65."""
        value = discounted_cash_flow_value(
            [140_000, 150_000, 160_000, 170_000, 180_000], 2_500_000, 0.08)
        self.assertAlmostEqual(2_334_161.65, value, places=2)

    def test_part4_4_2_example(self):
        """Part 4, 4.2 Example: 10k/-2k/18k/18k/5k plus a $40,000
        reversion, 6% discount rate -> $70,651.42."""
        value = discounted_cash_flow_value(
            [10_000, -2_000, 18_000, 18_000, 5_000], 40_000, 0.06)
        self.assertAlmostEqual(70_651.42, value, places=2)

    def test_part3_practice_test_q2(self):
        """Part 3 Practice Test Q2: -10k/4k/4k/4k/4k plus a $40,000
        reversion, 6% discount rate -> $33,532.23."""
        value = discounted_cash_flow_value(
            [-10_000, 4_000, 4_000, 4_000, 4_000], 40_000, 0.06)
        self.assertAlmostEqual(33_532.23, value, places=2)

    def test_reversion_combined_not_extra_period(self):
        """The confirmed most common DCF error: putting the reversion in
        its own extra period instead of combining it with the final
        period's income. A 1-year, $0-income case with a reversion must
        discount the reversion over exactly 1 period, not 2."""
        value = discounted_cash_flow_value([0], 100_000, 0.10)
        self.assertAlmostEqual(100_000 / 1.10, value, places=2)

    def test_empty_cash_flows_rejected(self):
        with self.assertRaises(DCFEngineError):
            discounted_cash_flow_value([], 100_000, 0.10)


class NPVTests(unittest.TestCase):
    """Part 5, 5.3/5.4 Problems: shared 5-year irregular stream
    100k/-5k/110k/115k/120k plus a $2,100,000 reversion, 10% yield rate."""

    CASH_FLOWS = [100_000, -5_000, 110_000, 115_000, 120_000]
    REVERSION = 2_100_000
    RATE = 0.10

    def test_5_3_problem_good_deal(self):
        """Priced at $1,600,000 -> NPV +$26,413.37 (positive, good deal)."""
        npv = net_present_value(1_600_000, self.CASH_FLOWS, self.REVERSION, self.RATE)
        self.assertAlmostEqual(26_413.37, npv, places=2)

    def test_5_4_problem_overpaid(self):
        """Priced at $1,650,000 -> NPV -$23,586.63 (negative, overpaid)."""
        npv = net_present_value(1_650_000, self.CASH_FLOWS, self.REVERSION, self.RATE)
        self.assertAlmostEqual(-23_586.63, npv, places=2)


class IRRTests(unittest.TestCase):
    def test_5_6_problem(self):
        """Part 5, 5.6 Problem: same 5-year stream as NPVTests, outlay
        $1,650,000 -> IRR 9.66% (below the 10% target, confirming the
        buyer overpaid relative to that criterion)."""
        irr = internal_rate_of_return(
            1_650_000, [100_000, -5_000, 110_000, 115_000, 120_000], 2_100_000)
        self.assertAlmostEqual(0.0966, irr, places=4)

    def test_6_3_problem_split_rate_scenario(self):
        """Part 6, 6.3 Problem: split-rate scenario's combined cash flows,
        outlay $2,594,856 -> IRR 10.18%, falling strictly between the
        7%/11% component rates used to build that outlay (SplitRateTests
        below) -- confirmed sanity-check property from the source
        material."""
        irr = internal_rate_of_return(
            2_594_856, [180_000, 190_000, 200_000, 210_000, 220_000], 3_000_000)
        self.assertAlmostEqual(0.1018, irr, places=4)
        self.assertTrue(0.07 < irr < 0.11)

    def test_unbracketed_root_raises(self):
        with self.assertRaises(DCFEngineError):
            internal_rate_of_return(-100, [100, 100, 100], 100)


class LevelEquivalentAnnuityTests(unittest.TestCase):
    def test_5_8_problem(self):
        """Part 5, 5.8 Problem: 100k/-10k/300k/300k/460k @ 9% -> PV
        $826,477.36, level-equivalent $212,481.10. Simple average would be
        $230,000 -- explicitly NOT the same, confirmed by the source
        material as a named common error (ignores time value of money)."""
        cash_flows = [100_000, -10_000, 300_000, 300_000, 460_000]
        pv = discounted_cash_flow_value(cash_flows, 0, 0.09)
        self.assertAlmostEqual(826_477.36, pv, places=2)
        level = level_equivalent_annuity(cash_flows, 0, 0.09)
        self.assertAlmostEqual(212_481.10, level, places=2)
        simple_average = sum(cash_flows) / len(cash_flows)
        self.assertNotAlmostEqual(simple_average, level, places=0)

    def test_practice_test_q3(self):
        """Practice Test Q3: 8-year stream (450k/0/460k/460k/460k/460k/
        600k/850k) @ 11% -> PV $2,221,524.65, level-equivalent
        $431,689.01."""
        cash_flows = [450_000, 0, 460_000, 460_000, 460_000, 460_000, 600_000, 850_000]
        pv = discounted_cash_flow_value(cash_flows, 0, 0.11)
        self.assertAlmostEqual(2_221_524.65, pv, places=2)
        level = level_equivalent_annuity(cash_flows, 0, 0.11)
        self.assertAlmostEqual(431_689.01, level, places=2)


class SplitRateTests(unittest.TestCase):
    def test_6_2_problem(self):
        """Part 6, 6.2 Problem: income 180k/190k/200k/210k/220k @ 7%,
        $3,000,000 reversion @ 11% -> PV_income $814,502.19, PV_reversion
        $1,780,354, total $2,594,856."""
        cash_flows = [180_000, 190_000, 200_000, 210_000, 220_000]
        total = split_rate_value(cash_flows, 0.07, 3_000_000, 0.11)
        self.assertAlmostEqual(2_594_856.17, total, places=2)


class IncomeInAdvanceTests(unittest.TestCase):
    def test_6_4_problem_step_up_ground_lease(self):
        """Part 6, 6.4 Problem: 12-year remaining step-up ground lease,
        advance payments $400k (2yrs) / $425k (5yrs) / $450k (5yrs), a
        $6,000,000 reversion at year 12, 8% -> $5,856,496.33. Verified
        independently via direct timing-shift derivation (a pure one-
        period timing shift is a uniform (1+rate) multiplication for any
        cash-flow shape, not just level annuities) before being hardcoded
        here."""
        cash_flows = ([400_000] * 2 + [425_000] * 5 + [450_000] * 5)
        value = present_value_income_in_advance(cash_flows, 0.08, reversion=6_000_000)
        self.assertAlmostEqual(5_856_496.33, value, places=2)

    def test_reversion_not_shifted_by_advance_multiplier(self):
        """The confirmed common error: applying the (1+Y) advance
        multiplier to the WHOLE value (income + reversion) instead of
        only the income component. A pure single-period, zero-income case
        must leave a reversion completely undisturbed."""
        value = present_value_income_in_advance([0], 0.10, reversion=100_000)
        self.assertAlmostEqual(100_000 / 1.10, value, places=2)


class MoreFrequentCompoundingTests(unittest.TestCase):
    """Not textbook-cited -- no worked numeric example exists in this
    material for this specific conversion. Verified only by construction:
    the round-trip identity (1+periodic)^periods_per_year == 1+annual
    holds by definition."""

    def test_monthly_roundtrip_identity(self):
        annual_rate = 0.10
        periodic = dcf_periodic_yield_rate(annual_rate, 12)
        self.assertAlmostEqual(1 + annual_rate, (1 + periodic) ** 12, places=9)

    def test_not_the_same_as_naive_nominal_division(self):
        """Confirmed improper practice per the source material: naively
        dividing the annual yield rate by 12 is NOT the same as the
        effective-rate-equivalent periodic rate this function computes."""
        annual_rate = 0.10
        naive = annual_rate / 12
        correct = dcf_periodic_yield_rate(annual_rate, 12)
        self.assertNotAlmostEqual(naive, correct, places=5)


class ImpliedOverallRateTests(unittest.TestCase):
    """Trivial division; the course's own explicit reasonableness-check
    step, not a fixture requiring textbook citation."""

    def test_basic_case(self):
        self.assertAlmostEqual(0.072, implied_overall_rate(72_000, 1_000_000), places=6)

    def test_zero_value_rejected(self):
        with self.assertRaises(DCFEngineError):
            implied_overall_rate(50_000, 0)


if __name__ == "__main__":
    unittest.main()
