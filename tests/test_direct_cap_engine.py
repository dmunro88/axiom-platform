"""
tests/test_direct_cap_engine.py — Axiom Platform

Regression coverage for direct_cap_engine.py, the Direct Capitalization
calculation core rebuilt in pure Python per the Appraisal Institute's
General Appraiser Income Approach/Part 1 course, replacing the platform's
prior (buggy) Excel formulas.

Every test cites its source problem and asserts against a value
independently recomputed in Python during test authoring — not
transcribed by eye, and not invented. The one exception is the NOI
adjustment fixture, which is explicitly disclosed as a derived (not
page-cited) formula, confirmed correct by Derek — see direct_cap_engine.py's
noi_adjustment_factor docstring.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from direct_cap_engine import (
    DirectCapEngineError,
    apply_multiplier,
    apply_noi_adjustment,
    apply_overall_cap_rate,
    band_of_investment_land_building,
    band_of_investment_mortgage_equity,
    building_residual,
    cap_rate_from_nir_and_egim,
    compute_egi,
    compute_noi,
    extract_building_rate_via_residual,
    extract_multiplier,
    extract_overall_cap_rate,
    forecast_income,
    land_residual,
    mortgage_equity_residual,
    noi_adjustment_factor,
    reversion_value,
    solve_building_rate,
    solve_equity_rate,
    solve_land_rate,
    terminal_cap_rate,
    underwriters_method_cap_rate,
)


class ComputeEGITests(unittest.TestCase):
    def test_9_11_problem_no_reimbursements(self):
        """Appraisal Institute Solutions Booklet (PC403GSB-M), 9.11 Problem,
        Part 1: PGI $350,000, 5% vacancy and collection loss, no
        reimbursements -> EGI $332,500."""
        result = compute_egi(pgi=350_000, vacancy_collection_loss_pct=0.05)
        self.assertAlmostEqual(350_000.0, result.total_pgi, places=2)
        self.assertAlmostEqual(17_500.0, result.vacancy_and_collection_loss, places=2)
        self.assertAlmostEqual(332_500.0, result.egi, places=2)

    def test_9_11_problem_with_reimbursements(self):
        """Same problem, Part 2: $30,000 reimbursements ADD to PGI before
        vacancy is applied to the combined total -- total PGI $380,000,
        EGI $361,000. Confirms reimbursements are not netted against a
        specific expense line."""
        result = compute_egi(pgi=350_000, vacancy_collection_loss_pct=0.05,
                              reimbursements=30_000)
        self.assertAlmostEqual(380_000.0, result.total_pgi, places=2)
        self.assertAlmostEqual(361_000.0, result.egi, places=2)

    def test_negative_reimbursements_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            compute_egi(pgi=100_000, vacancy_collection_loss_pct=0.05,
                        reimbursements=-1)

    def test_total_pgi_never_includes_other_income(self):
        """total_pgi must mean PGI + reimbursements only, consistently,
        regardless of other_income_subject_to_vacancy -- previously the
        vacancy-subject branch mutated total_pgi to include other_income
        before returning it, while the other branch didn't, giving the
        same field two different meanings depending on a flag."""
        subject_true = compute_egi(pgi=100_000, vacancy_collection_loss_pct=0.05,
                                    other_income=10_000, other_income_subject_to_vacancy=True)
        subject_false = compute_egi(pgi=100_000, vacancy_collection_loss_pct=0.05,
                                     other_income=10_000, other_income_subject_to_vacancy=False)
        self.assertAlmostEqual(100_000.0, subject_true.total_pgi, places=2)
        self.assertAlmostEqual(100_000.0, subject_false.total_pgi, places=2)
        # EGI still correctly differs based on the flag.
        self.assertAlmostEqual(104_500.0, subject_true.egi, places=2)
        self.assertAlmostEqual(105_000.0, subject_false.egi, places=2)

    def test_vacancy_pct_out_of_range_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            compute_egi(pgi=100_000, vacancy_collection_loss_pct=-0.05)
        with self.assertRaises(DirectCapEngineError):
            compute_egi(pgi=100_000, vacancy_collection_loss_pct=1.5)


class ComputeNOITests(unittest.TestCase):
    def test_9_11_problem_noi_and_ratios(self):
        """Same 9.11 Problem, Part 1: EGI $332,500, total expenses $50,000
        (fixed $25,000 + variable $20,000 + replacement allowance $5,000)
        -> NOI $282,500, OER 15%, NIR 85%."""
        result = compute_noi(egi=332_500, fixed_expenses=25_000,
                              variable_expenses=20_000, replacement_allowance=5_000)
        self.assertAlmostEqual(50_000.0, result.total_operating_expenses, places=2)
        self.assertAlmostEqual(282_500.0, result.noi, places=2)
        self.assertAlmostEqual(0.15038, result.operating_expense_ratio, places=5)
        self.assertAlmostEqual(0.84962, result.net_income_ratio, places=5)

    def test_zero_egi_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            compute_noi(egi=0, fixed_expenses=1_000, variable_expenses=500)


class OverallCapRateTests(unittest.TestCase):
    def test_13_4_problem_extraction_and_application(self):
        """13.4 Problem: comparable NOI $77,000 / sale price $1,200,000 ->
        R_O 6.4167%; applied to subject NOI $75,000 -> V_O $1,168,831.
        This is the direction the platform's prior Excel formula had
        backwards (it computed NOI = rate x price instead)."""
        r_o = extract_overall_cap_rate(noi=77_000, sale_price=1_200_000)
        self.assertAlmostEqual(0.064167, r_o, places=6)
        v_subject = apply_overall_cap_rate(noi=75_000, cap_rate=r_o)
        self.assertAlmostEqual(1_168_831.17, v_subject, places=2)

    def test_13_6_problem_nim_cross_check(self):
        """13.6 Problem: the Net Income Multiplier (NIM = Price / NOI =
        1/R_O) applied to the same subject NOI must reproduce the exact
        same indicated value as the R_O-based calculation above --
        confirms NIM and R_O are reciprocal, not independently-derived
        coincidences."""
        nim = extract_multiplier(sale_price=1_200_000, income=77_000)
        self.assertAlmostEqual(15.5844, nim, places=4)
        v_subject = apply_multiplier(income=75_000, multiplier=nim)
        self.assertAlmostEqual(1_168_831.17, v_subject, places=2)

    def test_zero_sale_price_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            extract_overall_cap_rate(noi=50_000, sale_price=0)


class CrossFormulaConsistencyTests(unittest.TestCase):
    def test_13_10_problem_comp_b_oer_nir_egim_ro_agree(self):
        """13.10 Problem, Comp B: sale price $1,350,000, EGI $157,200,
        NOI $78,300, total operating expenses $78,900. OER 50.19%,
        NIR 49.81%, EGIM 8.5878. R_O computed directly (NOI/Price) and
        via the cross-check relationship (NIR/EGIM) must land on the
        identical 5.80% -- a real regression test that two independently
        derived formulas agree."""
        noi_result = compute_noi(egi=157_200, fixed_expenses=0,
                                  variable_expenses=78_900, replacement_allowance=0)
        self.assertAlmostEqual(0.50191, noi_result.operating_expense_ratio, places=5)
        self.assertAlmostEqual(0.49809, noi_result.net_income_ratio, places=5)

        egim = extract_multiplier(sale_price=1_350_000, income=157_200)
        self.assertAlmostEqual(8.5878, egim, places=4)

        r_o_direct = extract_overall_cap_rate(noi=78_300, sale_price=1_350_000)
        r_o_cross = cap_rate_from_nir_and_egim(nir=noi_result.net_income_ratio, egim=egim)
        self.assertAlmostEqual(0.0580, r_o_direct, places=4)
        self.assertAlmostEqual(r_o_direct, r_o_cross, places=4)


class UnderwritersMethodTests(unittest.TestCase):
    def test_14_1_problem_dcr_and_rate(self):
        """14.1 Problem: M=70%, R_M=7.7316% (annual loan constant, given),
        DCR=1.0778 (from NOI $250,000 / annual debt service $231,949) ->
        R_O 5.833% via the underwriter's method."""
        dcr = 250_000 / 231_949
        self.assertAlmostEqual(1.0778, dcr, places=4)
        r_o = underwriters_method_cap_rate(loan_to_value_ratio=0.70,
                                            mortgage_rate=0.077316,
                                            debt_coverage_ratio=dcr)
        self.assertAlmostEqual(0.05833, r_o, places=5)

    def test_14_2_problem_lender_terms_disagree_with_market(self):
        """14.2 Problem: M=75%, R_M=8.5281%, DCR=1.15 -> underwriter's
        method gives R_O 7.355%, which the problem states correctly
        disagrees with a given market-extracted rate of 7.0% -- signaling
        the lender's quoted terms are not actually at market. This test
        asserts the formula's output, not a "flag" (the engine does not
        judge whether a rate matches the market; that's for the caller)."""
        r_o = underwriters_method_cap_rate(loan_to_value_ratio=0.75,
                                            mortgage_rate=0.085281,
                                            debt_coverage_ratio=1.15)
        self.assertAlmostEqual(0.07355, r_o, places=5)
        self.assertNotAlmostEqual(0.070, r_o, places=3)


class ReversionTests(unittest.TestCase):
    def test_14_4_problem_forecast_and_terminal_rate(self):
        """14.4 Problem: Year 1 income $130,000 growing 4%/yr, 8-year
        holding period, going-in rate 8.0% + 50bp load -> Year 9 income
        $177,914, terminal rate 8.5%, reversion value $2,093,106."""
        year9 = forecast_income(year1_income=130_000, growth_rate=0.04, target_year=9)
        self.assertAlmostEqual(177_913.98, year9, places=2)
        r_n = terminal_cap_rate(going_in_rate=0.080, load=0.005)
        self.assertAlmostEqual(0.085, r_n, places=4)
        v_n = reversion_value(forecasted_income=year9, terminal_rate=r_n)
        self.assertAlmostEqual(2_093_105.61, v_n, places=2)

    def test_target_year_below_one_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            forecast_income(year1_income=100_000, growth_rate=0.03, target_year=0)


class BandOfInvestmentTests(unittest.TestCase):
    def test_part15_problem3_mortgage_equity_forward(self):
        """Part 15 Practice Test Problem 3: M=60%, R_E=10%, R_M=5.7290%
        (annual loan constant, given) -> R_O 7.4374%."""
        r_o = band_of_investment_mortgage_equity(
            loan_to_value_ratio=0.60, mortgage_rate=0.057290, equity_rate=0.10)
        self.assertAlmostEqual(0.074374, r_o, places=6)

    def test_part15_problem4_mortgage_equity_solve_for_equity_rate(self):
        """Part 15 Problem 4: sale price $980,000, M=80%, R_M=7% (given),
        NOI $75,000 -> R_O 7.653% (extracted); R_E solved at 10.265%."""
        r_o = extract_overall_cap_rate(noi=75_000, sale_price=980_000)
        self.assertAlmostEqual(0.076531, r_o, places=6)
        r_e = solve_equity_rate(overall_rate=r_o, loan_to_value_ratio=0.80,
                                 mortgage_rate=0.07)
        self.assertAlmostEqual(0.102653, r_e, places=6)

    def test_part15_problem6_land_building_solve_for_land_rate(self):
        """Part 15 Problem 6: R_O=6%, B=55%, R_B=8% -> R_L 3.556%."""
        r_l = solve_land_rate(overall_rate=0.06, building_ratio=0.55, building_rate=0.08)
        self.assertAlmostEqual(0.035556, r_l, places=6)

    def test_part15_problem7_land_building_forward(self):
        """Part 15 Problem 7: L=75%, R_L=3%, B=25%, R_B=12% -> R_O 5.25%."""
        r_o = band_of_investment_land_building(land_ratio=0.75, land_rate=0.03,
                                                building_rate=0.12)
        self.assertAlmostEqual(0.0525, r_o, places=4)

    def test_full_loan_to_value_rejected_in_equity_solve(self):
        with self.assertRaises(DirectCapEngineError):
            solve_equity_rate(overall_rate=0.07, loan_to_value_ratio=1.0,
                               mortgage_rate=0.05)


class BuildingResidualTests(unittest.TestCase):
    def test_16_4_and_16_7_problem(self):
        """16.4/16.7 Problem: NOI $435,000, land value $1,500,000 @ 4.5%
        -> building value $3,500,000, total property value $5,000,000."""
        result = building_residual(noi=435_000, land_value=1_500_000,
                                    land_rate=0.045, building_rate=0.105)
        self.assertAlmostEqual(67_500.0, result.known_component_income, places=2)
        self.assertAlmostEqual(367_500.0, result.residual_income, places=2)
        self.assertAlmostEqual(3_500_000.0, result.solved_value, places=2)
        self.assertAlmostEqual(5_000_000.0, result.total_value, places=2)

    def test_16_5_problem_building_rate_extraction(self):
        """16.5 Problem: total value $1,200,000, NOI $90,000, land value
        $360,000 @ 6% -> extracted building rate 8.143%. Uses
        extract_building_rate_via_residual (building value known: total -
        land) to derive the building's own income and rate -- the inverse
        of building_residual (there, building_rate is given and value is
        solved for; here, value is given and rate is solved for)."""
        building_value = 1_200_000 - 360_000
        r_b = extract_building_rate_via_residual(
            noi=90_000, land_value=360_000, land_rate=0.06, building_value=building_value)
        self.assertAlmostEqual(0.081429, r_b, places=6)

    def test_zero_building_value_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            extract_building_rate_via_residual(
                noi=90_000, land_value=360_000, land_rate=0.06, building_value=0)


class LandResidualHBUTests(unittest.TestCase):
    """16.8 Problem: four-scenario highest-and-best-use comparison via land
    residual (building value/rate known, solving for land value at a
    reconciled land rate of 5%). The Office scenario resolves to a negative
    residual land value -- a valid, meaningful result signaling that use is
    not financially feasible, not an error."""

    SCENARIOS = {
        "Retail": dict(building_value=1_300_000, noi=110_000, building_rate=0.0700,
                        expected_land_value=380_000.0),
        "Warehouse": dict(building_value=1_050_000, noi=80_000, building_rate=0.0600,
                           expected_land_value=340_000.0),
        "Medical office": dict(building_value=1_000_000, noi=97_500, building_rate=0.0750,
                                expected_land_value=450_000.0),
        "Office": dict(building_value=1_400_000, noi=90_000, building_rate=0.0725,
                        expected_land_value=-230_000.0),
    }

    def test_each_scenario_land_value(self):
        for name, s in self.SCENARIOS.items():
            with self.subTest(scenario=name):
                result = land_residual(noi=s["noi"], building_value=s["building_value"],
                                        building_rate=s["building_rate"], land_rate=0.05)
                self.assertAlmostEqual(s["expected_land_value"], result.solved_value, places=2)

    def test_office_scenario_is_negative_not_an_error(self):
        """The textbook's own conclusion: Office is not a financially
        feasible use here (negative land residual), while Medical Office
        wins as highest and best use at $450,000 -- the highest positive
        residual among the four."""
        result = land_residual(noi=90_000, building_value=1_400_000,
                                building_rate=0.0725, land_rate=0.05)
        self.assertLess(result.solved_value, 0)

        medical = land_residual(noi=97_500, building_value=1_000_000,
                                 building_rate=0.0750, land_rate=0.05)
        self.assertAlmostEqual(450_000.0, medical.solved_value, places=2)
        all_values = [
            land_residual(noi=s["noi"], building_value=s["building_value"],
                          building_rate=s["building_rate"], land_rate=0.05).solved_value
            for s in self.SCENARIOS.values()
        ]
        self.assertEqual(max(all_values), medical.solved_value)


class MortgageEquityResidualTests(unittest.TestCase):
    def test_17_1_problem(self):
        """17.1 Problem: NOI $220,000, mortgage value $2,400,000 @ 8%,
        equity rate 4% -> equity value $700,000, total $3,100,000."""
        result = mortgage_equity_residual(noi=220_000, mortgage_value=2_400_000,
                                           mortgage_rate=0.08, equity_rate=0.04)
        self.assertAlmostEqual(192_000.0, result.known_component_income, places=2)
        self.assertAlmostEqual(28_000.0, result.residual_income, places=2)
        self.assertAlmostEqual(700_000.0, result.solved_value, places=2)
        self.assertAlmostEqual(3_100_000.0, result.total_value, places=2)


class NOIAdjustmentTests(unittest.TestCase):
    """Not textbook-cited -- a derived formula confirmed correct by Derek
    (2026-07-13), for the platform's previously-orphaned noi_adj sheet.
    Hand-constructed fixture, clearly disclosed as such."""

    def test_subject_stronger_than_comp_scales_price_up(self):
        """Subject NOI/SF $12.00 vs. comp NOI/SF $10.00 (subject is
        stronger) -> factor 1.20, scaling the comp's own $/SF upward to
        reflect the subject's higher income level."""
        factor = noi_adjustment_factor(subject_noi_psf=12.00, comp_noi_psf=10.00)
        self.assertAlmostEqual(1.20, factor, places=4)
        adjusted = apply_noi_adjustment(comp_price_psf=100.00, factor=factor)
        self.assertAlmostEqual(120.00, adjusted, places=2)

    def test_equal_noi_psf_leaves_price_unchanged(self):
        factor = noi_adjustment_factor(subject_noi_psf=10.00, comp_noi_psf=10.00)
        self.assertAlmostEqual(1.0, factor, places=4)
        self.assertAlmostEqual(100.00, apply_noi_adjustment(100.00, factor), places=2)

    def test_zero_comp_noi_rejected(self):
        with self.assertRaises(DirectCapEngineError):
            noi_adjustment_factor(subject_noi_psf=10.00, comp_noi_psf=0.00)


if __name__ == "__main__":
    unittest.main()
