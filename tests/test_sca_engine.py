"""
tests/test_sca_engine.py — Axiom Platform

Regression coverage for sca_engine.py, the Sales Comparison Approach
calculation core rebuilt in pure Python per the Appraisal Institute's
General Appraiser Sales Comparison Approach course, replacing the
platform's prior (buggy) Excel formulas.

IMPORTANT: these fixtures are self-contained and hand-verified by direct
arithmetic in each test's docstring/comments -- they are NOT transcribed
from the Appraisal Institute textbook or Solutions Booklet. That source
material was not available in the environment this test file was written
in (no PDF/text of PC401GCH-M or PC401GSB-K was present in the repo or
session). Encoding the textbook's own named worked examples (3.2 Example,
10.3 Example, the Part 16/17 case studies, Diagnostic Quiz Q8, Part 11.1,
Part 2 statistics problems, the cross-dock/apartment CV examples) requires
either that source text or the specific numbers extracted from it -- see
HANDOFF.md. What's covered here is the same set of algorithmic properties
(compounding vs. naive-sum, fixed-order sensitivity, property-stage
summation, CV-based unit selection, the inbreeding threshold, and the
statistics wrapper) using constructed numbers this file derives and checks
by hand, not textbook citations.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sca_engine import (
    Adjustment,
    ComparableResult,
    ComparableSale,
    SCAEngineError,
    apply_property,
    apply_transactional,
    inbreeding_warning,
    indicated_value,
    rank_by_gross_adjustment,
    select_unit_of_comparison,
    unit_price_stats,
)


class AdjustmentValidationTests(unittest.TestCase):
    def test_unknown_element_raises(self):
        with self.assertRaises(SCAEngineError):
            Adjustment(element="curb_appeal", stage="property", kind="percentage", value=0.01)

    def test_element_stage_mismatch_raises(self):
        """"location" is a property element; tagging it transactional is a
        caller error and must be raised immediately, not silently coerced."""
        with self.assertRaises(SCAEngineError):
            Adjustment(element="location", stage="transactional", kind="percentage", value=0.01)

    def test_invalid_kind_raises(self):
        with self.assertRaises(SCAEngineError):
            Adjustment(element="location", stage="property", kind="flat", value=0.01)

    def test_valid_adjustment_constructs(self):
        adjustment = Adjustment(element="market_conditions", stage="transactional",
                                 kind="percentage", value=0.05)
        self.assertEqual("market_conditions", adjustment.element)


class ApplyTransactionalTests(unittest.TestCase):
    def test_compounds_sequentially_not_naive_sum(self):
        """conditions_of_sale precedes market_conditions in the fixed order.
        Compounding: 100,000 * 1.05 (conditions_of_sale) = 105,000;
        105,000 * 1.10 (market_conditions) = 115,500.
        Naive sum-then-apply-once would instead give
        100,000 * (1 + 0.05 + 0.10) = 115,000 -- a different, wrong answer."""
        adjustments = (
            Adjustment(element="conditions_of_sale", stage="transactional",
                       kind="percentage", value=0.05),
            Adjustment(element="market_conditions", stage="transactional",
                       kind="percentage", value=0.10),
        )
        result = apply_transactional(100_000, adjustments)
        self.assertAlmostEqual(115_500.0, result, places=2)
        naive_sum_result = 100_000 * (1 + 0.05 + 0.10)
        self.assertNotAlmostEqual(naive_sum_result, result, places=2)

    def test_fixed_order_applies_regardless_of_input_list_order(self):
        """financing_terms (position 2) must apply before market_conditions
        (position 5) even when the caller passes them in reverse. Fixed
        order: 200,000 - 3,000 (financing) = 197,000; 197,000 * 1.05
        (market_conditions) = 206,850. Applying market_conditions first
        would give (200,000 * 1.05) - 3,000 = 207,000 instead -- a
        different result, which is why the engine must not trust list
        order."""
        reversed_order = (
            Adjustment(element="market_conditions", stage="transactional",
                       kind="percentage", value=0.05),
            Adjustment(element="financing_terms", stage="transactional",
                       kind="dollar", value=-3_000),
        )
        result = apply_transactional(200_000, reversed_order)
        self.assertAlmostEqual(206_850.0, result, places=2)

    def test_property_stage_adjustment_rejected(self):
        with self.assertRaises(SCAEngineError):
            apply_transactional(100_000, (
                Adjustment(element="location", stage="property",
                           kind="percentage", value=0.02),
            ))

    def test_duplicate_element_rejected(self):
        with self.assertRaises(SCAEngineError):
            apply_transactional(100_000, (
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.02),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.03),
            ))

    def test_no_adjustments_returns_sale_price_unchanged(self):
        self.assertEqual(100_000, apply_transactional(100_000, ()))


class ApplyPropertyTests(unittest.TestCase):
    def test_sums_independently_against_fixed_base(self):
        """location +3% of base (100,000) = 3,000; physical_characteristics
        a flat -1,500. Property adjustments do not compound against each
        other or against base: net = 3,000 + (-1,500) = 1,500;
        indicated_value = 100,000 + 1,500 = 101,500."""
        adjustments = (
            Adjustment(element="location", stage="property",
                       kind="percentage", value=0.03),
            Adjustment(element="physical_characteristics", stage="property",
                       kind="dollar", value=-1_500),
        )
        net, value = apply_property(100_000, adjustments)
        self.assertAlmostEqual(1_500.0, net, places=2)
        self.assertAlmostEqual(101_500.0, value, places=2)

    def test_transactional_stage_adjustment_rejected(self):
        with self.assertRaises(SCAEngineError):
            apply_property(100_000, (
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.02),
            ))


class IndicatedValueTests(unittest.TestCase):
    def test_full_pipeline_both_stages(self):
        """Combines ApplyTransactionalTests.test_fixed_order_... (base
        206,850) with a property stage of location +3% of base (6,205.50)
        and physical_characteristics -1,500:
        net_property = 6,205.50 - 1,500 = 4,705.50
        indicated_value = 206,850 + 4,705.50 = 211,555.50
        gross dollars = |-3,000| + |9,850| (transactional deltas)
                        + |6,205.50| + |-1,500| (property) = 20,555.50
        gross_pct = 20,555.50 / 200,000 = 0.1027775
        net_pct = (211,555.50 - 200,000) / 200,000 = 0.0577775"""
        comp = ComparableSale(
            identifier="C1",
            sale_price=200_000,
            adjustments=(
                Adjustment(element="financing_terms", stage="transactional",
                           kind="dollar", value=-3_000),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.05),
                Adjustment(element="location", stage="property",
                           kind="percentage", value=0.03),
                Adjustment(element="physical_characteristics", stage="property",
                           kind="dollar", value=-1_500),
            ),
        )
        result = indicated_value(comp)
        self.assertIsInstance(result, ComparableResult)
        self.assertAlmostEqual(206_850.0, result.transactional_base, places=2)
        self.assertAlmostEqual(4_705.50, result.net_property_adjustment, places=2)
        self.assertAlmostEqual(211_555.50, result.indicated_value, places=2)
        self.assertAlmostEqual(0.1027775, result.gross_adjustment_pct, places=6)
        self.assertAlmostEqual(0.0577775, result.net_adjustment_pct, places=6)

    def test_no_adjustments_indicated_value_equals_sale_price(self):
        comp = ComparableSale(identifier="C2", sale_price=50_000, adjustments=())
        result = indicated_value(comp)
        self.assertAlmostEqual(50_000.0, result.indicated_value, places=2)
        self.assertAlmostEqual(0.0, result.gross_adjustment_pct, places=6)


class UnitPriceStatsTests(unittest.TestCase):
    def test_stats_match_stdlib_definitions(self):
        """Dataset [10, 12, 12, 14, 22]: mean=14, median=12, mode=12,
        range=12. Sample stdev (n-1): variance = ((-4)^2 + (-2)^2 + (-2)^2
        + 0^2 + 8^2) / 4 = (16+4+4+0+64)/4 = 22; stdev = sqrt(22).
        CV = sqrt(22) / 14. This checks the module wraps `statistics`
        correctly (sample stdev via statistics.stdev, not pstdev)."""
        values = [10, 12, 12, 14, 22]
        stats = unit_price_stats(values)
        self.assertAlmostEqual(14.0, stats.mean, places=6)
        self.assertAlmostEqual(12.0, stats.median, places=6)
        self.assertAlmostEqual(12.0, stats.mode, places=6)
        self.assertAlmostEqual(12.0, stats.range, places=6)
        expected_stdev = math.sqrt(22)
        self.assertAlmostEqual(expected_stdev, stats.stdev, places=6)
        self.assertAlmostEqual(expected_stdev / 14.0, stats.cv, places=6)

    def test_fewer_than_two_values_raises(self):
        with self.assertRaises(SCAEngineError):
            unit_price_stats([42.0])


class SelectUnitOfComparisonTests(unittest.TestCase):
    def test_lowest_cv_wins(self):
        """Unit A is perfectly consistent (CV=0); unit B has high spread
        (CV>0). A must win regardless of dict insertion order."""
        candidates = {
            "price_per_acre": [50, 150, 50, 150],
            "price_per_sf": [100, 100, 100, 100],
            "price_per_unit": [80, 120, 80, 120],
        }
        self.assertEqual("price_per_sf", select_unit_of_comparison(candidates))

    def test_empty_candidates_raises(self):
        with self.assertRaises(SCAEngineError):
            select_unit_of_comparison({})


class RankByGrossAdjustmentTests(unittest.TestCase):
    def test_ranks_ascending_by_gross_pct(self):
        def result(identifier, gross_pct):
            return ComparableResult(
                identifier=identifier, sale_price=100_000,
                transactional_base=100_000, net_property_adjustment=0,
                indicated_value=100_000, gross_adjustment_pct=gross_pct,
                net_adjustment_pct=0,
            )

        results = [result("C3", 0.25), result("C1", 0.05), result("C2", 0.12)]
        ranked = rank_by_gross_adjustment(results)
        self.assertEqual(["C1", "C2", "C3"], [r.identifier for r in ranked])


class InbreedingWarningTests(unittest.TestCase):
    def test_warns_at_threshold(self):
        """4 comps -> threshold = 3. Solving for 3 adjustments from that
        closed set hits the threshold and must warn."""
        self.assertIsNotNone(inbreeding_warning(num_comps=4, num_solved_adjustments=3))

    def test_warns_above_threshold(self):
        self.assertIsNotNone(inbreeding_warning(num_comps=4, num_solved_adjustments=4))

    def test_no_warning_below_threshold(self):
        self.assertIsNone(inbreeding_warning(num_comps=4, num_solved_adjustments=2))

    def test_single_comp_raises(self):
        with self.assertRaises(SCAEngineError):
            inbreeding_warning(num_comps=1, num_solved_adjustments=0)


if __name__ == "__main__":
    unittest.main()
