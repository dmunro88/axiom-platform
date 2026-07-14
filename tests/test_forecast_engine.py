"""
tests/test_forecast_engine.py — Axiom Platform

Regression coverage for forecast_engine.py, the cash-flow-pattern
forecasting engine built per the Appraisal Institute's General Appraiser
Income Approach/Part 2 course (Part 3 "Forecasting Cash Flows" and Part 14
"Income Patterns").

Every test cites its source problem and asserts against a value
independently recomputed in Python during test authoring. Includes
cross-module integration tests against dcf_engine.py/direct_cap_engine.py,
since this module exists specifically to feed those.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dcf_engine import discounted_cash_flow_value
from forecast_engine import (
    ForecastEngineError,
    apply_below_the_line_items,
    compound_growth_series,
    deduct_deferred_maintenance,
    forecast_noi_series,
    implied_cap_rate_from_growth,
    implied_growth_rate,
    implied_yield_rate,
    level_series,
    net_reversion,
)


class CompoundGrowthSeriesTests(unittest.TestCase):
    def test_3_3_problem_pgi(self):
        """3.3 Problem: PGI $750,000 growing 4%/yr for 5 years."""
        series = compound_growth_series(750_000, 0.04, 5)
        expected = [750_000, 780_000, 811_200, 843_648, 877_393.92]
        for actual, exp in zip(series, expected):
            self.assertAlmostEqual(exp, actual, places=2)

    def test_3_3_problem_fixed_expenses(self):
        """3.3 Problem: fixed expenses $60,000 growing 3%/yr for 5 years."""
        series = compound_growth_series(60_000, 0.03, 5)
        expected = [60_000, 61_800, 63_654, 65_563.62, 67_530.53]
        for actual, exp in zip(series, expected):
            self.assertAlmostEqual(exp, actual, places=2)

    def test_3_3_problem_variable_expenses(self):
        """3.3 Problem: variable expenses $290,000 growing 5%/yr for 5 years."""
        series = compound_growth_series(290_000, 0.05, 5)
        expected = [290_000, 304_500, 319_725, 335_711.25, 352_496.81]
        for actual, exp in zip(series, expected):
            self.assertAlmostEqual(exp, actual, places=2)

    def test_14_6_problem_compound_rate_of_change(self):
        """14.6 Problem: $46,237.11 growing at a compound rate of 2%/yr
        for 10 years -- the named Compound Rate of Change Income
        Pattern, same formula as the multi-year forecasting technique
        above."""
        series = compound_growth_series(46_237.11, 0.02, 10)
        self.assertAlmostEqual(46_237.11, series[0], places=2)
        self.assertAlmostEqual(47_161.85, series[1], places=2)
        self.assertAlmostEqual(55_257.63, series[9], places=2)

    def test_zero_periods_rejected(self):
        with self.assertRaises(ForecastEngineError):
            compound_growth_series(100_000, 0.03, 0)


class LevelSeriesTests(unittest.TestCase):
    def test_level_income_pattern(self):
        """14.1 Problem: a level $50,000/yr pattern for 10 years."""
        series = level_series(50_000, 10)
        self.assertEqual([50_000] * 10, series)

    def test_zero_periods_rejected(self):
        with self.assertRaises(ForecastEngineError):
            level_series(50_000, 0)


class LevelEquivalenceCrossCheckTests(unittest.TestCase):
    """Confirmed by the source material (14.1/14.4/14.6 Problems): a level
    $50,000/yr 10-year annuity, an irregular 10-year stream, and a
    2%-compound-growth 10-year stream all produce the identical PV at 8%
    -- the textbook's own demonstration of "level equivalence." This is a
    real integration test spanning forecast_engine's generators and
    dcf_engine.discounted_cash_flow_value."""

    RATE = 0.08

    def test_level_pattern_pv(self):
        pv = discounted_cash_flow_value(level_series(50_000, 10), 0, self.RATE)
        self.assertAlmostEqual(335_504, pv, delta=1.0)

    def test_irregular_pattern_pv(self):
        """14.4 Problem's own irregular 10-year stream."""
        cash_flows = [37_000, -5_523, 44_000, 59_200, 59_200,
                       59_200, 59_200, 65_000, 79_000, 88_000]
        pv = discounted_cash_flow_value(cash_flows, 0, self.RATE)
        self.assertAlmostEqual(335_504, pv, delta=1.0)

    def test_compound_growth_pattern_pv(self):
        """14.6 Problem's compound-rate-of-change stream."""
        cash_flows = compound_growth_series(46_237.11, 0.02, 10)
        pv = discounted_cash_flow_value(cash_flows, 0, self.RATE)
        self.assertAlmostEqual(335_504, pv, delta=1.0)


class ForecastNOISeriesTests(unittest.TestCase):
    def test_3_3_problem_full_forecast(self):
        """3.3 Problem: PGI $750,000 @ 4%, 8% vacancy, fixed expenses
        $60,000 @ 3%, variable expenses $290,000 @ 5%, 5-year forecast ->
        NOI = [340,000; 351,300; 362,925; 374,881; 387,175]."""
        noi = forecast_noi_series(
            pgi_year1=750_000, pgi_growth_rate=0.04,
            vacancy_collection_loss_pct=0.08,
            fixed_expenses_year1=60_000, fixed_growth_rate=0.03,
            variable_expenses_year1=290_000, variable_growth_rate=0.05,
            periods=5,
        )
        expected = [340_000, 351_300, 362_925, 374_881, 387_175]
        for actual, exp in zip(noi, expected):
            self.assertAlmostEqual(exp, actual, delta=1.0)


class BelowTheLineItemsTests(unittest.TestCase):
    def test_3_3_problem_roof_replacement_year_3_only(self):
        """3.3 Problem: a $15,000 roof replacement applied only to Year 3
        -> net cash flow [340,000; 351,300; 347,925; 374,881; 387,175],
        every other year unchanged."""
        noi = [340_000, 351_300, 362_925, 374_881.29, 387_175.07]
        net_cf = apply_below_the_line_items(noi, {3: 15_000})
        expected = [340_000, 351_300, 347_925, 374_881.29, 387_175.07]
        for actual, exp in zip(net_cf, expected):
            self.assertAlmostEqual(exp, actual, delta=1.0)

    def test_year_out_of_range_rejected(self):
        with self.assertRaises(ForecastEngineError):
            apply_below_the_line_items([100, 100, 100], {5: 10})

    def test_non_int_year_rejected(self):
        """Fable adversarial review finding: a float year key (e.g. 3.0)
        used to raise a raw TypeError from the list-indexing arithmetic
        instead of ForecastEngineError."""
        with self.assertRaises(ForecastEngineError):
            apply_below_the_line_items([100, 100, 100], {3.0: 10})


class DeferredMaintenanceTests(unittest.TestCase):
    def test_3_2_problem(self):
        """3.2 Problem: $5,320,000 as-cured value, less $20,000 cost to
        cure -> $5,300,000 current value. Deferred maintenance is
        explicitly NOT a below-the-line expense -- it comes out of value,
        never out of a year's cash flow."""
        value = deduct_deferred_maintenance(5_320_000, 20_000)
        self.assertAlmostEqual(5_300_000, value, places=2)


class ReversionWithExpensesOfSaleTests(unittest.TestCase):
    def test_3_4_problem(self):
        """3.4 Problem: Year 6 NOI $399,812 capitalized at a 6.5% terminal
        rate, less 3% expenses of sale -> net reversion ~$5,966,425 (the
        booklet's own printed intermediate rounding of the gross figure
        cascades to a few-dollar difference from its final $5,966,431,
        same class of rounding drift already handled in Phase 2's loan-
        balance test)."""
        gross = 399_812 / 0.065
        net = net_reversion(gross, 0.03)
        self.assertAlmostEqual(5_966_425, net, delta=10.0)


class ImpliedRateRelationshipTests(unittest.TestCase):
    """R = Y - CR, confirmed ONLY under a "frozen rate," perpetual-growth
    premise (Part 16) -- income and value both growing at the same
    constant rate forever. NOT the same condition as a finite-horizon
    compound_growth_series forecast."""

    def test_16_4_problem(self):
        """16.4 Problem: I_O $24,000 / V $400,000 -> R=6%; given Y=10% ->
        CR=4%."""
        r = 24_000 / 400_000
        self.assertAlmostEqual(0.06, r, places=4)
        cr = implied_growth_rate(yield_rate=0.10, cap_rate=r)
        self.assertAlmostEqual(0.04, cr, places=4)

    def test_18_3_problem(self):
        """18.3 Problem: I_O $135,000 / V $2,400,000 -> R=5.625%; Y=10% ->
        CR=4.375%."""
        r = 135_000 / 2_400_000
        self.assertAlmostEqual(0.05625, r, places=5)
        cr = implied_growth_rate(yield_rate=0.10, cap_rate=r)
        self.assertAlmostEqual(0.04375, cr, places=5)

    def test_practice_test_q4_q6_pair(self):
        """Practice Test Q4/Q6: Y=11%, CR=4% -> R=7%, and V =
        $150,000/0.07 = $2,142,857. Q4 (a finite 7-year holding with zero
        reversion, PV $784,651) and Q6 (perpetual growth at the same
        rate) are explicitly DIFFERENT scenarios -- not asserted equal to
        each other, only that Q6's own R/Y/CR relationship and resulting
        value are internally consistent."""
        r = implied_cap_rate_from_growth(yield_rate=0.11, growth_rate=0.04)
        self.assertAlmostEqual(0.07, r, places=4)
        v = 150_000 / r
        self.assertAlmostEqual(2_142_857, v, delta=1.0)
        y = implied_yield_rate(cap_rate=r, growth_rate=0.04)
        self.assertAlmostEqual(0.11, y, places=4)


if __name__ == "__main__":
    unittest.main()
