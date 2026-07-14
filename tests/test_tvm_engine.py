"""
tests/test_tvm_engine.py — Axiom Platform

Regression coverage for tvm_engine.py, the Time Value of Money / Six
Functions of a Dollar calculation core built per the Appraisal Institute's
General Appraiser Income Approach/Part 1 course (Parts 2-4) — the
foundation Phase 3b (DCF/yield capitalization) will build on.

Every test cites its source problem and asserts against a value
independently recomputed in Python during test authoring. The one
exception is the mortgage capitalization rate fixture (4.6 Problem),
explicitly disclosed as reverse-engineered: the solutions booklet states
only the final R_M/Y_M answers, not the underlying loan term, so the
20-year/240-month term used here was found by numerically matching the
stated 8.5972% answer, not transcribed from a printed loan statement.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tvm_engine import (
    TVMEngineError,
    effective_annual_rate,
    future_value,
    future_value_annuity_factor,
    future_value_factor,
    future_value_of_annuity,
    installment_to_amortize_factor,
    loan_balance,
    mortgage_capitalization_rate,
    mortgage_payment,
    periodic_rate,
    present_value,
    present_value_annuity_due,
    present_value_annuity_factor,
    present_value_factor,
    present_value_of_annuity,
    present_value_with_reversion,
    sinking_fund_factor,
    sinking_fund_payment,
    solve_yield_rate,
)

# Appraisal Institute textbook (PC403GCH-M), 4.1 Problem: the complete
# six-function factor table at 6%, n=1-30 (solutions booklet p.29-31),
# independently recomputed and confirmed exact to 6 decimal places.
SIX_PERCENT_TABLE = {
    1: (1.060000, 1.000000, 1.000000, 0.943396, 0.943396, 1.060000),
    2: (1.123600, 2.060000, 0.485437, 0.889996, 1.833393, 0.545437),
    3: (1.191016, 3.183600, 0.314110, 0.839619, 2.673012, 0.374110),
    4: (1.262477, 4.374616, 0.228591, 0.792094, 3.465106, 0.288591),
    5: (1.338226, 5.637093, 0.177396, 0.747258, 4.212364, 0.237396),
    6: (1.418519, 6.975319, 0.143363, 0.704961, 4.917324, 0.203363),
    7: (1.503630, 8.393838, 0.119135, 0.665057, 5.582381, 0.179135),
    8: (1.593848, 9.897468, 0.101036, 0.627412, 6.209794, 0.161036),
    9: (1.689479, 11.491316, 0.087022, 0.591898, 6.801692, 0.147022),
    10: (1.790848, 13.180795, 0.075868, 0.558395, 7.360087, 0.135868),
    11: (1.898299, 14.971643, 0.066793, 0.526788, 7.886875, 0.126793),
    12: (2.012196, 16.869941, 0.059277, 0.496969, 8.383844, 0.119277),
    13: (2.132928, 18.882138, 0.052960, 0.468839, 8.852683, 0.112960),
    14: (2.260904, 21.015066, 0.047585, 0.442301, 9.294984, 0.107585),
    15: (2.396558, 23.275970, 0.042963, 0.417265, 9.712249, 0.102963),
    16: (2.540352, 25.672528, 0.038952, 0.393646, 10.105895, 0.098952),
    17: (2.692773, 28.212880, 0.035445, 0.371364, 10.477260, 0.095445),
    18: (2.854339, 30.905653, 0.032357, 0.350344, 10.827603, 0.092357),
    19: (3.025600, 33.759992, 0.029621, 0.330513, 11.158116, 0.089621),
    20: (3.207135, 36.785591, 0.027185, 0.311805, 11.469921, 0.087185),
    21: (3.399564, 39.992727, 0.025005, 0.294155, 11.764077, 0.085005),
    22: (3.603537, 43.392290, 0.023046, 0.277505, 12.041582, 0.083046),
    23: (3.819750, 46.995828, 0.021278, 0.261797, 12.303379, 0.081278),
    24: (4.048935, 50.815577, 0.019679, 0.246979, 12.550358, 0.079679),
    25: (4.291871, 54.864512, 0.018227, 0.232999, 12.783356, 0.078227),
    26: (4.549383, 59.156383, 0.016904, 0.219810, 13.003166, 0.076904),
    27: (4.822346, 63.705766, 0.015697, 0.207368, 13.210534, 0.075697),
    28: (5.111687, 68.528112, 0.014593, 0.195630, 13.406164, 0.074593),
    29: (5.418388, 73.639798, 0.013580, 0.184557, 13.590721, 0.073580),
    30: (5.743491, 79.058186, 0.012649, 0.174110, 13.764831, 0.072649),
}


class SixFunctionFactorTableTests(unittest.TestCase):
    def test_full_table_at_6_percent(self):
        """4.1 Problem: the complete printed factor table, n=1-30 at 6%,
        for all six functions. All 30 rows independently recomputed and
        confirmed exact."""
        for n, (fv, fva, sff, pv, pva, itao) in SIX_PERCENT_TABLE.items():
            with self.subTest(n=n):
                self.assertAlmostEqual(fv, future_value_factor(0.06, n), places=5)
                self.assertAlmostEqual(fva, future_value_annuity_factor(0.06, n), places=5)
                self.assertAlmostEqual(sff, sinking_fund_factor(0.06, n), places=5)
                self.assertAlmostEqual(pv, present_value_factor(0.06, n), places=5)
                self.assertAlmostEqual(pva, present_value_annuity_factor(0.06, n), places=5)
                self.assertAlmostEqual(itao, installment_to_amortize_factor(0.06, n), places=5)

    def test_sinking_fund_plus_rate_equals_installment_to_amortize(self):
        """Confirmed textbook identity: SFF + i = ITAO."""
        for n in (1, 5, 10, 30):
            with self.subTest(n=n):
                self.assertAlmostEqual(
                    sinking_fund_factor(0.06, n) + 0.06,
                    installment_to_amortize_factor(0.06, n),
                    places=6,
                )

    def test_present_value_factor_is_reciprocal_of_future_value_factor(self):
        for n in (1, 5, 10, 30):
            with self.subTest(n=n):
                self.assertAlmostEqual(
                    1.0, future_value_factor(0.06, n) * present_value_factor(0.06, n), places=9
                )

    def test_rate_at_or_below_negative_one_rejected(self):
        """A rate of exactly -100% (or lower) makes (1+rate) zero or
        negative -- not a meaningful compounding rate. Previously this
        produced a raw ZeroDivisionError or silent sign-nonsense instead
        of failing loudly."""
        for factor_fn in (future_value_factor, present_value_factor,
                           future_value_annuity_factor, present_value_annuity_factor,
                           sinking_fund_factor, installment_to_amortize_factor):
            with self.subTest(factor_fn=factor_fn.__name__):
                with self.assertRaises(TVMEngineError):
                    factor_fn(-1.0, 5)
                with self.assertRaises(TVMEngineError):
                    factor_fn(-1.5, 5)

    def test_zero_periods_rejected_regardless_of_rate(self):
        """Previously the periods==0 guard only existed inside the
        rate==0 branch, so a nonzero rate with periods=0 raised a raw
        ZeroDivisionError instead of TVMEngineError."""
        with self.assertRaises(TVMEngineError):
            sinking_fund_factor(0.06, 0)
        with self.assertRaises(TVMEngineError):
            installment_to_amortize_factor(0.06, 0)


class FutureValueLumpSumTests(unittest.TestCase):
    def test_2_7_1_problem(self):
        """2.7.1 Problem: $1,000 at 6%, compounded annually, 1 year -> $1,060.00."""
        self.assertAlmostEqual(1_060.00, future_value(1_000, 0.06, 1), places=2)

    def test_2_7_3_problem_nominal_quarterly(self):
        """2.7.3 Problem: $1,000, nominal 6% compounded quarterly, 1 year
        -> $1,061.36. Periodic rate = 6%/4 = 1.5%, n=4 quarters."""
        i = periodic_rate(0.06, 4)
        self.assertAlmostEqual(1_061.36, future_value(1_000, i, 4), places=2)

    def test_2_12_problem(self):
        """2.12 Problem: $1,000 at 6%/year for 25 years -> $4,291.87."""
        self.assertAlmostEqual(4_291.87, future_value(1_000, 0.06, 25), places=2)


class PresentValueLumpSumTests(unittest.TestCase):
    def test_3_3_problem(self):
        """3.3 Problem: $100,000 due in 5 periods at 6%/period -> $74,725.82."""
        self.assertAlmostEqual(74_725.82, present_value(100_000, 0.06, 5), places=2)

    def test_3_4_problem(self):
        """3.4 Problem: $1,000,000 due in 15 years at 8% -> $315,241.70."""
        self.assertAlmostEqual(315_241.70, present_value(1_000_000, 0.08, 15), places=2)


class FutureValueAnnuityTests(unittest.TestCase):
    def test_3_10_3_11_example(self):
        """3.10/3.11 Example: $300/month deposits (end of month), 2%/year
        compounded monthly, 12 months -> FV $3,633.18."""
        i = periodic_rate(0.02, 12)
        self.assertAlmostEqual(3_633.18, future_value_of_annuity(300, i, 12), places=2)

    def test_3_14_3_15_example_sinking_fund(self):
        """3.14/3.15 Example: level monthly deposit needed to accumulate
        $5,000 in 12 months at 6% nominal compounded monthly -> PMT $405.33."""
        i = periodic_rate(0.06, 12)
        self.assertAlmostEqual(405.33, sinking_fund_payment(5_000, i, 12), places=2)

    def test_3_16_problem_hoa_sinking_fund(self):
        """3.16 Problem: HOA sinking fund to repave streets in 20 years,
        cost $350,000, 1.5% annual -> PMT $15,136.01."""
        self.assertAlmostEqual(15_136.01, sinking_fund_payment(350_000, 0.015, 20), places=2)


class PresentValueAnnuityAndMortgageTests(unittest.TestCase):
    def test_3_7_problem(self):
        """3.7 Problem: PV of $20,000/year (ordinary annuity) for 5 years
        at 6% -> $84,247.28."""
        self.assertAlmostEqual(84_247.28, present_value_of_annuity(20_000, 0.06, 5), places=2)

    def test_3_8_problem_annuity_due(self):
        """3.8 Problem: same $20,000/year paid in advance (annuity due)
        -> $89,302.11 = ordinary PV x (1+i)."""
        ordinary = present_value_of_annuity(20_000, 0.06, 5)
        self.assertAlmostEqual(89_302.11, present_value_annuity_due(ordinary, 0.06), places=2)

    def test_3_18_3_19_example_mortgage_payment_monthly(self):
        """3.18/3.19 Example: $250,000 loan, 15 years amortized monthly at
        5.25% -> PMT $2,009.69."""
        i = periodic_rate(0.0525, 12)
        self.assertAlmostEqual(2_009.69, mortgage_payment(250_000, i, 15 * 12), places=2)

    def test_3_20_problem_mortgage_payment_quarterly(self):
        """3.20 Problem: same $250,000/15yr/5.25% loan but quarterly
        payments -> PMT $6,046.36."""
        i = periodic_rate(0.0525, 4)
        self.assertAlmostEqual(6_046.36, mortgage_payment(250_000, i, 15 * 4), places=2)


class LoanBalanceTests(unittest.TestCase):
    def test_4_2_example(self):
        """4.2 Example: $250,000 loan, 15yr monthly at 4.5%, balance after
        5 years -> $184,534.21."""
        i = periodic_rate(0.045, 12)
        balance = loan_balance(250_000, i, total_periods=15 * 12, elapsed_periods=5 * 12)
        self.assertAlmostEqual(184_534.21, balance, places=2)

    def test_4_3_problem(self):
        """4.3 Problem: $300,000 loan, 30yr monthly at 6%, balance after
        10 years -> $251,057.18."""
        i = periodic_rate(0.06, 12)
        balance = loan_balance(300_000, i, total_periods=30 * 12, elapsed_periods=10 * 12)
        self.assertAlmostEqual(251_057.18, balance, delta=0.01)

    def test_review_quiz_q2_part4(self):
        """Review Quiz Q2, Part 4: $500,000 loan, 15yr monthly at 5%,
        balance after 5 years -> $372,785.45."""
        i = periodic_rate(0.05, 12)
        balance = loan_balance(500_000, i, total_periods=15 * 12, elapsed_periods=5 * 12)
        self.assertAlmostEqual(372_785.45, balance, places=2)

    def test_elapsed_periods_out_of_range_rejected(self):
        with self.assertRaises(TVMEngineError):
            loan_balance(100_000, 0.005, total_periods=120, elapsed_periods=121)


class CombinationLevelAnnuityTests(unittest.TestCase):
    def test_4_7_problem(self):
        """4.7 Problem: $60,000/year net income for 5 years plus a
        $750,000 reversion, discount rate 10% -> PV $693,138."""
        pv = present_value_with_reversion(60_000, 0.10, 5, 750_000)
        self.assertAlmostEqual(693_138.0, pv, delta=1.0)


class NominalEffectiveRateTests(unittest.TestCase):
    """2.8 Problem: nominal 6%/year at five compounding frequencies."""

    def test_annually(self):
        self.assertAlmostEqual(0.06000, effective_annual_rate(0.06, 1), places=5)

    def test_semi_annually(self):
        self.assertAlmostEqual(0.06090, effective_annual_rate(0.06, 2), places=5)

    def test_quarterly(self):
        self.assertAlmostEqual(0.06136, effective_annual_rate(0.06, 4), places=5)

    def test_monthly(self):
        self.assertAlmostEqual(0.06168, effective_annual_rate(0.06, 12), places=5)

    def test_daily(self):
        self.assertAlmostEqual(0.06183, effective_annual_rate(0.06, 365), places=5)


class MortgageCapitalizationRateTests(unittest.TestCase):
    def test_4_6_problem_reverse_engineered_term(self):
        """4.6 Problem: the solutions booklet states only the final
        answers (Y_M=6.00%, R_M=8.5972%), not the underlying loan term.
        Confirmed by numeric match: a 6% loan, monthly payments, amortized
        over 20 years (240 months) produces R_M=8.5972% exactly -- the
        term used here was found this way, not transcribed from a printed
        loan statement. Y_M is simply the nominal rate itself."""
        r_m = mortgage_capitalization_rate(nominal_annual_rate=0.06,
                                            periods_per_year=12, amortization_years=20)
        self.assertAlmostEqual(0.085972, r_m, places=6)
        # Y_M is simply the nominal rate itself, per the source material --
        # there is no function to test here, only the fact stated above.


class SolveYieldRateTests(unittest.TestCase):
    def test_review_quiz_q1_part4(self):
        """Review Quiz Q1, Part 4: property cost $50,000, net out-of-pocket
        carrying cost $2,000/year for 14 years, sold for $200,000 at year
        14 -> yield rate i = 8.21% (8.2069% exact). Uses the textbook's own
        signed cash-flow convention (cost and carrying cost both outflows,
        sale proceeds an inflow) since this genuinely solves an equation,
        not just applies a formula."""
        i = solve_yield_rate(present_value_amount=-50_000, payment=-2_000,
                              future_value_amount=200_000, periods=14)
        self.assertAlmostEqual(0.082069, i, places=6)

    def test_unbracketed_root_raises(self):
        with self.assertRaises(TVMEngineError):
            solve_yield_rate(present_value_amount=100, payment=100,
                              future_value_amount=100, periods=5)

    def test_converges_at_institutional_scale(self):
        """Fable adversarial review finding: the same Review Quiz Q1 shape
        scaled up 100x to a routine $5M property used to raise "did not
        converge" -- an absolute-dollar NPV tolerance is far coarser than
        float precision at multi-million-dollar magnitudes. Fixed by also
        checking bisection interval width, not NPV magnitude alone."""
        i = solve_yield_rate(present_value_amount=-5_000_000, payment=-200_000,
                              future_value_amount=20_000_000, periods=14)
        self.assertAlmostEqual(0.082069, i, places=6)

    def test_does_not_converge_early_at_tiny_scale(self):
        """Converse defect the same review found: an NPV-only tolerance
        could trigger early at very small dollar magnitudes and return a
        materially wrong rate. Same shape scaled down 1e9x must still
        resolve to the correct rate, not a nearby-but-wrong one."""
        i = solve_yield_rate(present_value_amount=-50e-9, payment=-2e-9,
                              future_value_amount=200e-9, periods=14)
        self.assertAlmostEqual(0.082069, i, places=6)


if __name__ == "__main__":
    unittest.main()
