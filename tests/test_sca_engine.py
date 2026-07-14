"""
tests/test_sca_engine.py — Axiom Platform

Regression coverage for sca_engine.py, the Sales Comparison Approach
calculation core rebuilt in pure Python per the Appraisal Institute's
General Appraiser Sales Comparison Approach course, replacing the
platform's prior (buggy) Excel formulas.

The classes above this line (through InbreedingWarningTests) are
self-contained, hand-verified constructed fixtures written in an earlier
pass that didn't have access to the source textbook/solutions booklet in
that environment -- they check the same algorithmic properties (compounding
vs. naive-sum, fixed-order sensitivity, property-stage summation, CV-based
unit selection, the inbreeding threshold, the statistics wrapper) with
invented numbers, not textbook citations.

The classes below that line ARE transcribed from, and verified against, the
actual source material: the Appraisal Institute's *General Appraiser Sales
Comparison Approach* course (PC401GCH-M) and its Solutions Booklet
(PC401GSB-K). Every expected value in those classes was independently
recomputed in Python (not just hand-checked) against the booklet's own
printed figures before being hardcoded here; any known rounding-path
difference between the engine's unrounded arithmetic and the booklet's own
manually-rounded intermediate steps is called out explicitly in the
relevant test's docstring rather than silently tolerated.
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

    def test_mode_is_none_when_nothing_repeats(self):
        """Fable adversarial review finding: Python's statistics.mode()
        (3.8+) returns the first value instead of raising when nothing
        actually repeats -- a fabricated "mode" that would mislead a
        reader into thinking a real most-frequent value exists."""
        stats = unit_price_stats([10, 12, 14, 22])
        self.assertIsNone(stats.mode)

    def test_non_positive_mean_rejected(self):
        """Unit prices should always be positive; a non-positive mean
        would otherwise let a nonsensical negative CV silently win in
        select_unit_of_comparison."""
        with self.assertRaises(SCAEngineError):
            unit_price_stats([-100, -100, -100, -101])
        with self.assertRaises(SCAEngineError):
            unit_price_stats([100, -100, 50, -50])


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

    def test_negative_mean_candidate_rejected_not_silently_selected(self):
        """Fable adversarial review finding: a candidate unit with a
        negative mean produces a negative CV, which used to win min()
        outright regardless of how sane the other candidates were.
        unit_price_stats now rejects non-positive means, so this raises
        instead of silently selecting nonsense."""
        candidates = {
            "sane": [100, 101, 99, 100],
            "garbage_negative": [-100, -100, -100, -101],
        }
        with self.assertRaises(SCAEngineError):
            select_unit_of_comparison(candidates)


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


class Part3Example32Tests(unittest.TestCase):
    """Appraisal Institute, *General Appraiser Sales Comparison Approach*
    (PC401GCH-M), Part 3, "3.2 Example" (printed p.63) -- the textbook's own
    worked proof that transactional adjustments compound sequentially while
    property adjustments sum independently against the fixed
    post-transactional base. Summing every adjustment and applying it once
    instead gives a different, and wrong, answer -- this is the single most
    load-bearing formula-design fact behind this whole module."""

    def test_exact_textbook_dollar_deltas(self):
        """Uses the textbook's own printed per-step DOLLAR amounts (not the
        percentages) for both stages, so this test matches the textbook's
        exact final figure with zero rounding ambiguity: transactional
        100,000 -> 105,000 -> 102,900 -> 108,045 -> 111,286 -> 116,850;
        property net -2,337 (3,506 - 5,843 - 5,843 + 2,337 + 3,506); final
        114,513."""
        comp = ComparableSale(
            identifier="3.2 Example (exact)",
            sale_price=100_000,
            adjustments=(
                Adjustment(element="property_rights", stage="transactional",
                           kind="dollar", value=5_000),
                Adjustment(element="financing_terms", stage="transactional",
                           kind="dollar", value=-2_100),
                Adjustment(element="conditions_of_sale", stage="transactional",
                           kind="dollar", value=5_145),
                Adjustment(element="expenditures_after_purchase", stage="transactional",
                           kind="dollar", value=3_241),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="dollar", value=5_564),
                Adjustment(element="location", stage="property",
                           kind="dollar", value=3_506),
                Adjustment(element="physical_characteristics", stage="property",
                           kind="dollar", value=-5_843),
                Adjustment(element="economic_characteristics", stage="property",
                           kind="dollar", value=-5_843),
                Adjustment(element="use", stage="property",
                           kind="dollar", value=2_337),
                Adjustment(element="non_realty_components", stage="property",
                           kind="dollar", value=3_506),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(116_850.0, result.transactional_base, places=2)
        self.assertAlmostEqual(-2_337.0, result.net_property_adjustment, places=2)
        self.assertAlmostEqual(114_513.0, result.indicated_value, places=2)

    def test_stated_percentages_match_within_a_dollar(self):
        """Same example, using the textbook's STATED percentages (5%, -2%,
        5%, 3%, 5% transactional; 3%, -5%, -5%, 2%, 3% property) instead of
        its own pre-rounded per-step dollar amounts. The engine does not
        round intermediate steps -- a deliberate design choice, see the
        module docstring -- so this lands at $114,513.65 (recomputed
        independently in Python during test authoring), about $0.65 away
        from the textbook's own manually-rounded-at-each-step $114,513.
        That gap is rounding-path noise, not a discrepancy in the method:
        confirmed by the exact-dollar-delta test above landing precisely on
        $114,513 using the very same combination logic."""
        comp = ComparableSale(
            identifier="3.2 Example (pct)",
            sale_price=100_000,
            adjustments=(
                Adjustment(element="property_rights", stage="transactional",
                           kind="percentage", value=0.05),
                Adjustment(element="financing_terms", stage="transactional",
                           kind="percentage", value=-0.02),
                Adjustment(element="conditions_of_sale", stage="transactional",
                           kind="percentage", value=0.05),
                Adjustment(element="expenditures_after_purchase", stage="transactional",
                           kind="percentage", value=0.03),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.05),
                Adjustment(element="location", stage="property",
                           kind="percentage", value=0.03),
                Adjustment(element="physical_characteristics", stage="property",
                           kind="percentage", value=-0.05),
                Adjustment(element="economic_characteristics", stage="property",
                           kind="percentage", value=-0.05),
                Adjustment(element="use", stage="property",
                           kind="percentage", value=0.02),
                Adjustment(element="non_realty_components", stage="property",
                           kind="percentage", value=0.03),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(114_513.65, result.indicated_value, places=2)
        self.assertLess(abs(result.indicated_value - 114_513.0), 1.0)


class Part17OfficeRetailCaseStudyTests(unittest.TestCase):
    """Appraisal Institute Solutions Booklet (PC401GSB-K), Part 17 case
    study: a 4-sale office/retail grid. Each sale exercises a different
    subset of the five transactional elements, several mixing a dollar
    adjustment with a percentage adjustment in the same chain -- exactly
    the case the textbook itself warns is order-sensitive (10.5/10.6
    Examples), so this is a real test of "trust the fixed order, not input
    order" against genuine textbook data rather than invented numbers."""

    def test_sale1_financing_then_market_conditions(self):
        """Financing -$75,000 (dollar) must apply before market conditions
        +12% (12 months at the case's derived 1%/month rate): 3,120,000 -
        75,000 = 3,045,000; * 1.12 = 3,410,400. (The booklet's own summary
        table prints $3,410,000, a $400 rounding note in the source
        material itself -- $3,410,400 is the mathematically exact result of
        the stated $75,000 and 12% figures.)"""
        comp = ComparableSale(
            identifier="Sale1", sale_price=3_120_000,
            adjustments=(
                Adjustment(element="financing_terms", stage="transactional",
                           kind="dollar", value=-75_000),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.12),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(3_410_400.0, result.indicated_value, places=2)

    def test_sale2_market_conditions_only(self):
        """6 months at 1%/month = 6%: 2,520,000 * 1.06 = 2,671,200."""
        comp = ComparableSale(
            identifier="Sale2", sale_price=2_520_000,
            adjustments=(
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.06),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(2_671_200.0, result.indicated_value, places=2)

    def test_sale3_conditions_of_sale_only(self):
        """-$100,000 for seller motivation; contemporaneous sale, so no
        market-conditions adjustment: 4,100,000 - 100,000 = 4,000,000."""
        comp = ComparableSale(
            identifier="Sale3", sale_price=4_100_000,
            adjustments=(
                Adjustment(element="conditions_of_sale", stage="transactional",
                           kind="dollar", value=-100_000),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(4_000_000.0, result.indicated_value, places=2)

    def test_sale4_expenditures_then_market_conditions(self):
        """+$50,000 new-roof expenditure must apply before +6% market
        conditions: 3,410,000 + 50,000 = 3,460,000; * 1.06 = 3,667,600."""
        comp = ComparableSale(
            identifier="Sale4", sale_price=3_410_000,
            adjustments=(
                Adjustment(element="expenditures_after_purchase", stage="transactional",
                           kind="dollar", value=50_000),
                Adjustment(element="market_conditions", stage="transactional",
                           kind="percentage", value=0.06),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(3_667_600.0, result.indicated_value, places=2)


class Part16ApartmentCaseStudyTests(unittest.TestCase):
    """Appraisal Institute Solutions Booklet, Part 16 case study: a 6-sale
    apartment grid, the richest multi-comp worked example in the source
    material, including its own reconciliation-support ranking. The
    booklet's descriptive categories are mapped onto this engine's fixed
    element names as follows: "distance from beach" -> location;
    "age/condition" and "amenities" both -> physical_characteristics (two
    separate line items on the same element, distinguished by `note` --
    apply_property does not require element uniqueness the way
    apply_transactional does, since property adjustments never compound
    against each other regardless of how many touch the same element)."""

    COMPS = {
        "Sale1": dict(price=8_400_000, financing=0, expenditures=0, market=0,
                       distance=0, age=0, amenities=-135_000, units=110),
        "Sale2": dict(price=7_025_000, financing=-375_000, expenditures=0, market=0,
                       distance=1_125_000, age=0, amenities=-1_350_000, units=90),
        "Sale3": dict(price=9_100_000, financing=0, expenditures=0, market=1_820_000,
                       distance=0, age=0, amenities=0, units=150),
        "Sale4": dict(price=7_425_000, financing=0, expenditures=150_000, market=189_375,
                       distance=1_625_000, age=0, amenities=-27_000, units=130),
        "Sale5": dict(price=6_100_000, financing=0, expenditures=0, market=610_000,
                       distance=500_000, age=125_000, amenities=-112_500, units=100),
        "Sale6": dict(price=8_590_000, financing=0, expenditures=0, market=429_500,
                       distance=625_000, age=75_000, amenities=-450_000, units=125),
    }

    # Both dicts recomputed independently in Python during test authoring
    # against the booklet's own printed "Indicated value" / "Gross adj % of
    # price" columns -- not transcribed by eye from the table.
    EXPECTED_INDICATED = {
        "Sale1": 8_265_000, "Sale2": 6_425_000, "Sale3": 10_920_000,
        "Sale4": 9_362_375, "Sale5": 7_222_500, "Sale6": 9_269_500,
    }
    EXPECTED_GROSS_PCT = {
        "Sale1": 0.016, "Sale2": 0.406, "Sale3": 0.200,
        "Sale4": 0.268, "Sale5": 0.221, "Sale6": 0.184,
    }

    @staticmethod
    def _build(name, c):
        adjustments = []
        if c["financing"]:
            adjustments.append(Adjustment(
                element="financing_terms", stage="transactional",
                kind="dollar", value=c["financing"]))
        if c["expenditures"]:
            adjustments.append(Adjustment(
                element="expenditures_after_purchase", stage="transactional",
                kind="dollar", value=c["expenditures"]))
        if c["market"]:
            adjustments.append(Adjustment(
                element="market_conditions", stage="transactional",
                kind="dollar", value=c["market"]))
        if c["distance"]:
            adjustments.append(Adjustment(
                element="location", stage="property",
                kind="dollar", value=c["distance"], note="distance from beach"))
        if c["age"]:
            adjustments.append(Adjustment(
                element="physical_characteristics", stage="property",
                kind="dollar", value=c["age"], note="age/condition"))
        if c["amenities"]:
            adjustments.append(Adjustment(
                element="physical_characteristics", stage="property",
                kind="dollar", value=c["amenities"], note="amenities"))
        return ComparableSale(identifier=name, sale_price=c["price"],
                               adjustments=tuple(adjustments))

    def test_each_comp_indicated_value_and_gross_pct(self):
        for name, c in self.COMPS.items():
            with self.subTest(sale=name):
                result = indicated_value(self._build(name, c))
                self.assertAlmostEqual(
                    self.EXPECTED_INDICATED[name], result.indicated_value, places=2)
                self.assertAlmostEqual(
                    self.EXPECTED_GROSS_PCT[name], result.gross_adjustment_pct, places=3)

    def test_per_unit_stats_match_textbook(self):
        """Per the booklet: mean $72,954/unit, sample stdev $1,420.31,
        CV ~1.9%. This matches exactly when each comp's per-unit indicated
        value is rounded to the nearest whole dollar BEFORE computing
        stats -- the booklet's own convention (it works from its own
        rounded per-unit dollar column, not raw unrounded quotients);
        confirmed by recomputing both ways independently in Python during
        test authoring."""
        per_unit = []
        for name, c in self.COMPS.items():
            result = indicated_value(self._build(name, c))
            per_unit.append(round(result.indicated_value / c["units"]))
        stats = unit_price_stats(per_unit)
        self.assertAlmostEqual(72_954, stats.mean, places=0)
        self.assertAlmostEqual(1_420.31, stats.stdev, places=2)
        self.assertAlmostEqual(0.019, stats.cv, places=3)

    def test_rank_by_gross_adjustment_matches_textbook_reconciliation_order(self):
        """The booklet's own reconciliation gives Sale1 (1.6% gross
        adjustment) the most weight and Sale2 (40.6%) the least -- confirms
        rank_by_gross_adjustment reproduces that same ordering, the
        reconciliation-support data this function exists to provide."""
        results = [indicated_value(self._build(name, c)) for name, c in self.COMPS.items()]
        ranked = rank_by_gross_adjustment(results)
        self.assertEqual("Sale1", ranked[0].identifier)
        self.assertEqual("Sale2", ranked[-1].identifier)


class Part2StatisticsProblemTests(unittest.TestCase):
    """Appraisal Institute textbook, Part 2 ("Units of Comparison" /
    "Statistical Analysis"), worked problems 2.7 and 2.12."""

    def test_27_problem_acreage_and_price_per_sf(self):
        """Four vacant office sites. Acres: mean 2.78, sd 0.63. Price/SF:
        mean $4.12, sd $0.84 -- both printed exactly in the booklet, and
        both reproduced by unit_price_stats to 2 decimal places."""
        acres = unit_price_stats([2.15, 2.35, 3.10, 3.50])
        psf = unit_price_stats([4.80, 4.88, 3.55, 3.25])
        self.assertAlmostEqual(2.78, acres.mean, places=2)
        self.assertAlmostEqual(0.63, acres.stdev, places=2)
        self.assertAlmostEqual(4.12, psf.mean, places=2)
        self.assertAlmostEqual(0.84, psf.stdev, places=2)

    def test_212_cross_dock_industrial_unit_selection(self):
        """Cross-dock industrial property, 4 sales, 4 candidate units of
        comparison. Price/loading-dock has by far the lowest CV (1.4% vs.
        12.7-16.5% for the other three) and is the unit "the market is
        using" per the textbook's own selection rule -- confirms
        select_unit_of_comparison picks it, and unit_price_stats reproduces
        the booklet's own mean/stdev/CV for that winning unit."""
        candidates = {
            "price_per_sf": [85.00, 68.00, 77.00, 100.00],
            "price_per_cuft": [3.86, 3.40, 4.81, 4.00],
            "price_per_acre": [1_700_000, 1_500_000, 1_925_000, 2_000_000],
            "price_per_dock": [85_000, 85_000, 87_500, 86_000],
        }
        self.assertEqual("price_per_dock", select_unit_of_comparison(candidates))
        dock_stats = unit_price_stats(candidates["price_per_dock"])
        self.assertAlmostEqual(85_875, dock_stats.mean, places=0)
        self.assertAlmostEqual(1_181, dock_stats.stdev, places=0)
        self.assertAlmostEqual(0.014, dock_stats.cv, places=3)


class DiagnosticQuizQ8Test(unittest.TestCase):
    def test_single_attribute_office_area_adjustment(self):
        """Appraisal Institute Solutions Booklet, Diagnostic Quiz Q8: a
        7,500-SF industrial building's comparable sold for $900,000 but
        included 3,000 SF of additional office area contributing $50.00/SF
        -- adjusted sale price $750,000. The simplest possible smoke test
        of the property-adjustment path against real textbook data."""
        comp = ComparableSale(
            identifier="Q8", sale_price=900_000,
            adjustments=(
                Adjustment(element="physical_characteristics", stage="property",
                           kind="dollar", value=-3_000 * 50.00,
                           note="additional office area"),
            ),
        )
        result = indicated_value(comp)
        self.assertAlmostEqual(750_000.0, result.indicated_value, places=2)


class Part11InbreedingOfDataTest(unittest.TestCase):
    def test_four_comps_three_adjustments_matches_part11_example(self):
        """Appraisal Institute textbook, Part 11.1 "Inbreeding of Data":
        deriving 3 adjustments from a closed set of 4 comps + subject
        produces a mathematically consistent but non-resilient answer -- a
        single bad input price swings the "perfectly consistent" conclusion
        from $13.00/SF to $11.00/SF in the booklet's own illustration. Same
        shape as InbreedingWarningTests.test_warns_at_threshold, named
        explicitly to this citation since it's the textbook example that
        motivated building this guardrail into the engine at all."""
        self.assertIsNotNone(inbreeding_warning(num_comps=4, num_solved_adjustments=3))


if __name__ == "__main__":
    unittest.main()
