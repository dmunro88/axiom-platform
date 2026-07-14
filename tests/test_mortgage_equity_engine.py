"""
tests/test_mortgage_equity_engine.py — Axiom Platform

Regression coverage for mortgage_equity_engine.py, the leveraged
(mortgage-equity split) DCF engine built per the Appraisal Institute's
General Appraiser Income Approach/Part 2 course, Parts 7-10 and the
Self-Study Practice Problems, Sections 3 & 4.

Every test cites its source problem number and asserts against a value
independently recomputed in Python during test authoring, cross-checked
directly against the source PDF's own printed intermediate values (not
just its final answers). Includes cross-module integration tests against
dcf_engine.py, since this module exists specifically to feed it.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dcf_engine import discounted_cash_flow_value, internal_rate_of_return
from mortgage_equity_engine import (
    MortgageEquityEngineError,
    cash_equivalent_price,
    debt_coverage_ratio,
    equity_cash_flows,
    loan_to_value_ratio,
    mortgage_amount_from_dcr,
    yield_rate_ordering_is_plausible,
)


class CashEquivalentPriceTests(unittest.TestCase):
    def test_8_1_problem_monthly_due_in_five(self):
        """8.1 Problem: $450,000 note/4%/20yr/monthly, due in 5 years,
        market rate 5%, $100,000 down -> $531,760.50."""
        price = cash_equivalent_price(
            loan_amount=450_000, contract_rate=0.04, market_rate=0.05,
            periods_per_year=12, term_years=20, due_years=5,
            down_payment=100_000,
        )
        self.assertAlmostEqual(531_760.50, price, places=2)

    def test_8_2_problem_quarterly_due_in_ten(self):
        """8.2 Problem: $750,000 note/4.5%/30yr/quarterly, due in 10 years,
        market rate 6%, $150,000 down -> $822,605.70."""
        price = cash_equivalent_price(
            loan_amount=750_000, contract_rate=0.045, market_rate=0.06,
            periods_per_year=4, term_years=30, due_years=10,
            down_payment=150_000,
        )
        self.assertAlmostEqual(822_605.70, price, places=2)

    def test_self_study_4a_full_term(self):
        """Self-Study #4A: $75,000 sale/$60,000 note/3%/25yr/monthly, full
        term, market rate 5%, $15,000 down -> $63,671.17."""
        price = cash_equivalent_price(
            loan_amount=60_000, contract_rate=0.03, market_rate=0.05,
            periods_per_year=12, term_years=25, due_years=25,
            down_payment=15_000,
        )
        self.assertAlmostEqual(63_671.17, price, places=2)

    def test_self_study_4b_balloon_in_five(self):
        """Self-Study #4B: same note as 4A, balloon due in 5 years ->
        $70,053.07."""
        price = cash_equivalent_price(
            loan_amount=60_000, contract_rate=0.03, market_rate=0.05,
            periods_per_year=12, term_years=25, due_years=5,
            down_payment=15_000,
        )
        self.assertAlmostEqual(70_053.07, price, places=2)

    def test_self_study_5a_full_term(self):
        """Self-Study #5A: $1,750,000 sale/$1,200,000 note/3.5%/20yr/
        monthly, full term, market rate 5.5%, $550,000 down ->
        $1,561,723.37."""
        price = cash_equivalent_price(
            loan_amount=1_200_000, contract_rate=0.035, market_rate=0.055,
            periods_per_year=12, term_years=20, due_years=20,
            down_payment=550_000,
        )
        self.assertAlmostEqual(1_561_723.37, price, delta=0.01)

    def test_self_study_5b_prepayment_in_seven(self):
        """Self-Study #5B: same note as 5A, prepayment in 7 years ->
        $1,627,670.33."""
        price = cash_equivalent_price(
            loan_amount=1_200_000, contract_rate=0.035, market_rate=0.055,
            periods_per_year=12, term_years=20, due_years=7,
            down_payment=550_000,
        )
        self.assertAlmostEqual(1_627_670.33, price, places=2)


class DebtCoverageAndLoanToValueTests(unittest.TestCase):
    def test_8_4_problem_dcr_grid(self):
        """8.4 Problem: $2,000,000 property/$120,000 NOI, 6%/25yr/monthly
        loan, mortgage constant 0.077316 -> DCR 2.59/1.29/0.86 at 30%/60%/
        90% loan-to-value."""
        r_m = 0.077316
        v_o = 2_000_000
        noi = 120_000
        expected = {0.30: 2.59, 0.60: 1.29, 0.90: 0.86}
        for ltv, exp_dcr in expected.items():
            v_m = v_o * ltv
            annual_debt_service = v_m * r_m
            dcr = debt_coverage_ratio(noi, annual_debt_service)
            self.assertAlmostEqual(exp_dcr, dcr, places=2)

    def test_8_5_problem_ltv_at_dcr_of_one(self):
        """8.5 Problem: same property as 8.4, solve for the loan-to-value
        ratio where DCR = 1 -> 78%."""
        loan = mortgage_amount_from_dcr(
            noi=120_000, dcr=1.0, rate=0.06, periods_per_year=12,
            term_years=25,
        )
        ltv = loan_to_value_ratio(loan, 2_000_000)
        self.assertAlmostEqual(0.78, ltv, places=2)

    def test_21_2_problem_dcr_via_formula_and_constructed_example(self):
        """21.2 Problem: 75% LTV, 0.084814 mortgage cap rate, 0.08 overall
        cap rate -> DCR 1.26, confirmed two ways: by the formula
        DCR = R_O / (M x R_M), and by constructing a $100,000 example
        property and computing debt_coverage_ratio directly."""
        m, r_m, r_o = 0.75, 0.084814, 0.08
        dcr_by_formula = r_o / (m * r_m)
        self.assertAlmostEqual(1.26, dcr_by_formula, places=2)

        v_o = 100_000
        v_m = m * v_o
        annual_debt_service = r_m * v_m
        noi = r_o * v_o
        dcr = debt_coverage_ratio(noi, annual_debt_service)
        self.assertAlmostEqual(1.26, dcr, places=2)

    def test_zero_dcr_rejected(self):
        with self.assertRaises(MortgageEquityEngineError):
            mortgage_amount_from_dcr(noi=100_000, dcr=0, rate=0.06,
                                       periods_per_year=12, term_years=25)

    def test_zero_annual_debt_service_rejected(self):
        with self.assertRaises(MortgageEquityEngineError):
            debt_coverage_ratio(100_000, 0)


class EquityCashFlowsLevelIncomeTests(unittest.TestCase):
    """Part 12 Practice Test Question 1: level $120,000 NOI for 5 years,
    property adjusts to $200,000 in Year 6, mortgage $1,400,000 at 5.75%/
    30yr monthly, terminal cap rate 8%, equity yield rate 12%."""

    def test_p12_q1_equity_split_and_value(self):
        reversion = 200_000 / 0.08
        self.assertAlmostEqual(2_500_000, reversion, places=2)

        ecf = equity_cash_flows(
            noi_series=[120_000] * 5, mortgage_value=1_400_000,
            mortgage_rate=0.0575, periods_per_year=12,
            mortgage_term_years=30, reversion=reversion,
        )
        self.assertAlmostEqual(98_040.24, ecf.annual_debt_service, places=2)
        self.assertAlmostEqual(1_298_670.62, ecf.mortgage_balance_at_sale, places=2)
        for actual in ecf.income:
            self.assertAlmostEqual(21_960, actual, delta=1.0)
        self.assertAlmostEqual(1_201_329, ecf.reversion, delta=1.0)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.12)
        self.assertAlmostEqual(760_827, v_e, delta=1.0)

        v_o = 1_400_000 + v_e
        self.assertAlmostEqual(2_160_827, v_o, delta=1.0)


class EquityCashFlowsGrowingIncomeTests(unittest.TestCase):
    def test_p12_q5_equity_pv(self):
        """Part 12 Practice Test Question 5: NOI $100,000 rising $5,000/yr
        for 5 years, mortgage $900,000 at 6%/20yr monthly (booklet gives
        ADS $77,375/balance $764,096 as shortcuts -- independently
        reproduced here), reversion $1,500,000, Y_E 12.5%.

        Disclosed discrepancy: the booklet's stated final answer
        ($522,588.96, choice B) does not independently verify. Its own
        printed cash-flow table one line above states an equity reversion
        of $735,904 -- itself the arithmetically correct $1,500,000 minus
        the $764,096 mortgage balance the booklet also states (and which
        this module's equity_cash_flows() independently reproduces to the
        penny). But discounting that exact table (income $22,625-$42,625
        plus a $735,904 reversion) at 12.5% mathematically yields
        $520,369.24, not $522,588.96 -- reaching $522,588.96 requires a
        reversion of $739,904, a $4,000 figure that appears nowhere else
        in the problem and contradicts the booklet's own arithmetic one
        paragraph earlier. This looks like a transcription error in the
        source material itself (a self-study problem the text explicitly
        flags as lower-priority/less rigorously reviewed than the core
        course material), not an error in this module. This test asserts
        the internally-consistent, independently-verified value rather
        than the booklet's own inconsistent final answer."""
        noi_series = [100_000, 105_000, 110_000, 115_000, 120_000]
        ecf = equity_cash_flows(
            noi_series=noi_series, mortgage_value=900_000,
            mortgage_rate=0.06, periods_per_year=12,
            mortgage_term_years=20, reversion=1_500_000,
        )
        self.assertAlmostEqual(77_375, ecf.annual_debt_service, delta=1.0)
        self.assertAlmostEqual(764_096, ecf.mortgage_balance_at_sale, delta=1.0)
        self.assertAlmostEqual(735_904, ecf.reversion, delta=1.0)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.125)
        self.assertAlmostEqual(520_369.24, v_e, delta=2.0)

    def test_self_study_13_growing_noi_and_reversion(self):
        """Self-Study #13 (refers to #12): same $1,800,000/4.5%/30yr
        mortgage as #12, NOI growing 2.5%/yr from $130,000, reversion
        $3,000,000 in Year 5, Y_E 12% -> equity PV $866,607.55, property
        value $2,666,607.55."""
        noi_series = [130_000 * (1.025 ** i) for i in range(5)]
        ecf = equity_cash_flows(
            noi_series=noi_series, mortgage_value=1_800_000,
            mortgage_rate=0.045, periods_per_year=12,
            mortgage_term_years=30, reversion=3_000_000,
        )
        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.12)
        self.assertAlmostEqual(866_607.55, v_e, delta=1.0)

        v_o = 1_800_000 + v_e
        self.assertAlmostEqual(2_666_607.55, v_o, delta=1.0)


class EquityCashFlowsLevelIncomeCrossCheckTests(unittest.TestCase):
    def test_self_study_12_full_split_and_implied_rates(self):
        """Self-Study #12: level NOI $130,000, mortgage $1,800,000 at
        4.5%/30yr monthly, net resale $2,700,000 in 5 years, Y_E 12% ->
        equity PV $675,094.09, property value $2,475,094.09, implied R_E
        3.04%, implied R_O 5.25%."""
        ecf = equity_cash_flows(
            noi_series=[130_000] * 5, mortgage_value=1_800_000,
            mortgage_rate=0.045, periods_per_year=12,
            mortgage_term_years=30, reversion=2_700_000,
        )
        self.assertAlmostEqual(109_444.03, ecf.annual_debt_service, places=2)
        self.assertAlmostEqual(1_640_842.51, ecf.mortgage_balance_at_sale, places=2)
        for actual in ecf.income:
            self.assertAlmostEqual(20_555.97, actual, places=2)
        self.assertAlmostEqual(1_059_157.49, ecf.reversion, delta=1.0)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.12)
        self.assertAlmostEqual(675_094.09, v_e, places=2)

        v_o = 1_800_000 + v_e
        self.assertAlmostEqual(2_475_094.09, v_o, places=2)

        r_e = ecf.income[0] / v_e
        self.assertAlmostEqual(0.0304, r_e, places=3)
        r_o = 130_000 / v_o
        self.assertAlmostEqual(0.0525, r_o, places=3)


class MortgageFromDCRIntegrationTests(unittest.TestCase):
    def test_self_study_15_dcr_derived_mortgage(self):
        """Self-Study #15: level NOI $130,000, DCR 1.19, mortgage 4.5%/
        30yr monthly, net resale $2,700,000 in 5 years, Y_E 12% -> derived
        mortgage $1,796,705.23, equity PV $677,520, property value
        $2,474,225.69, implied LTV ~72.6%."""
        v_m = mortgage_amount_from_dcr(
            noi=130_000, dcr=1.19, rate=0.045, periods_per_year=12,
            term_years=30,
        )
        self.assertAlmostEqual(1_796_705.23, v_m, places=2)

        ecf = equity_cash_flows(
            noi_series=[130_000] * 5, mortgage_value=v_m,
            mortgage_rate=0.045, periods_per_year=12,
            mortgage_term_years=30, reversion=2_700_000,
        )
        self.assertAlmostEqual(1_637_839.06, ecf.mortgage_balance_at_sale, places=2)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.12)
        self.assertAlmostEqual(677_520, v_e, delta=1.0)

        v_o = v_m + v_e
        self.assertAlmostEqual(2_474_225.69, v_o, delta=1.0)

        ltv = loan_to_value_ratio(v_m, v_o)
        self.assertAlmostEqual(0.7262, ltv, places=3)


class NonReconcilingDCFConclusionsTests(unittest.TestCase):
    def test_self_study_16_property_and_equity_dcf_diverge(self):
        """Self-Study #16: full PGI -> vacancy(15%) -> opex(35% of EGI) ->
        NOI 5-year build growing 2%/yr from $700,000 PGI, mortgage
        $3,200,000 at 6% ANNUAL payments over 20 years, reversion
        $4,600,000. Booklet computes an unlevered property DCF at
        Y_O=10% ($4,376,420.29) AND a levered equity DCF at Y_E=12%
        (equity PV $1,511,518.87, implying $4,711,518.87 property value)
        -- explicitly confirmed by the source material's own discussion
        to be two DIFFERENT numbers, not an algebraic identity to force."""
        pgi = [700_000 * (1.02 ** i) for i in range(5)]
        egi = [p * 0.85 for p in pgi]
        noi_series = [e * 0.65 for e in egi]
        expected_noi = [386_750, 394_485, 402_375, 410_422, 418_631]
        for actual, exp in zip(noi_series, expected_noi):
            self.assertAlmostEqual(exp, actual, delta=1.0)

        v_o_direct = discounted_cash_flow_value(noi_series, 4_600_000, 0.10)
        self.assertAlmostEqual(4_376_420.29, v_o_direct, delta=1.0)

        ecf = equity_cash_flows(
            noi_series=noi_series, mortgage_value=3_200_000,
            mortgage_rate=0.06, periods_per_year=1,
            mortgage_term_years=20, reversion=4_600_000,
        )
        self.assertAlmostEqual(278_990.58, ecf.annual_debt_service, places=2)
        self.assertAlmostEqual(2_709_626.00, ecf.mortgage_balance_at_sale, places=2)
        self.assertAlmostEqual(1_890_374, ecf.reversion, delta=1.0)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.12)
        self.assertAlmostEqual(1_511_518.87, v_e, delta=1.0)

        v_o_via_equity = 3_200_000 + v_e
        self.assertAlmostEqual(4_711_518.87, v_o_via_equity, delta=1.0)

        self.assertNotAlmostEqual(v_o_direct, v_o_via_equity, delta=1000)

    def test_hold_period_exceeding_mortgage_term_rejected(self):
        with self.assertRaises(MortgageEquityEngineError):
            equity_cash_flows(
                noi_series=[100_000] * 10, mortgage_value=1_000_000,
                mortgage_rate=0.06, periods_per_year=12,
                mortgage_term_years=5, reversion=1_500_000,
            )

    def test_empty_noi_series_rejected(self):
        with self.assertRaises(MortgageEquityEngineError):
            equity_cash_flows(
                noi_series=[], mortgage_value=1_000_000,
                mortgage_rate=0.06, periods_per_year=12,
                mortgage_term_years=20, reversion=1_500_000,
            )


class YieldRateOrderingTests(unittest.TestCase):
    def test_self_study_8_solved_yo_falls_between(self):
        """Self-Study #8: I_O $460,000 (Years 1-5), Y_E 11%, mortgage 6%
        interest/20yr monthly due in 5 with DCR 1.15, terminal cap rate
        8.5% on Year 6 income of $510,000. The booklet's own component
        grid gives V_M=$4,652,692/mortgage reversion $3,950,117 (both
        independently reproduced here), but leaves solving for Y_O as an
        unworked exercise -- solved here via dcf_engine.internal_rate_of_return
        and confirmed to land at ~7.29%, satisfying the expected ordering
        Y_E (11%) > Y_O > Y_M (6%)."""
        v_m = mortgage_amount_from_dcr(
            noi=460_000, dcr=1.15, rate=0.06, periods_per_year=12,
            term_years=20,
        )
        self.assertAlmostEqual(4_652_692, v_m, delta=1.0)

        reversion = 510_000 / 0.085
        self.assertAlmostEqual(6_000_000, reversion, delta=1.0)

        ecf = equity_cash_flows(
            noi_series=[460_000] * 5, mortgage_value=v_m, mortgage_rate=0.06,
            periods_per_year=12, mortgage_term_years=20, reversion=reversion,
        )
        self.assertAlmostEqual(3_950_117, ecf.mortgage_balance_at_sale, delta=1.0)

        v_e = discounted_cash_flow_value(ecf.income, ecf.reversion, 0.11)
        v_o = v_m + v_e

        y_o = internal_rate_of_return(v_o, [460_000] * 5, reversion)
        self.assertAlmostEqual(0.0729, y_o, places=3)

        self.assertTrue(yield_rate_ordering_is_plausible(
            mortgage_rate=0.06, overall_yield_rate=y_o, equity_yield_rate=0.11,
        ))

    def test_implausible_ordering_returns_false(self):
        self.assertFalse(yield_rate_ordering_is_plausible(
            mortgage_rate=0.09, overall_yield_rate=0.07, equity_yield_rate=0.11,
        ))


if __name__ == "__main__":
    unittest.main()
