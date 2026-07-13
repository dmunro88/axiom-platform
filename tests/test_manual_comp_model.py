import unittest

from manual_comp_model import (
    DROPDOWNS,
    PROPERTY_TYPE_VALUES,
    calculate_lease_indicators,
    calculate_sale_indicators,
    evaluate_manual_comp,
    normalize_manual_comp_data,
)


class ManualCompModelTests(unittest.TestCase):
    def test_sale_calculations_cover_core_indicators(self):
        result = calculate_sale_indicators(
            {
                "property_type": "Office",
                "sale_price": "$1,250,000",
                "sale_date": "01/15/2025",
                "gba_sf": "10,000 SF",
                "site_area_acres": "2.5 acres",
                "number_of_units": "20",
                "potential_gross_income": "$200,000",
                "effective_gross_income": "$180,000",
                "expenses": "$72,000",
                "noi": "$108,000",
            },
            effective_date="2026-01-15",
        )

        self.assertEqual(125.0, result["price_per_gba_sf"])
        self.assertEqual(125.0, result["price_per_sf"])
        self.assertEqual("gba_sf", result["price_per_sf_basis"])
        self.assertEqual(500000.0, result["price_per_acre"])
        self.assertEqual(62500.0, result["sale_price_per_unit"])
        self.assertEqual(108900.0, result["site_area_sf"])
        self.assertEqual(10.89, result["land_to_building_ratio"])
        self.assertEqual(0.0918, result["floor_area_ratio"])
        self.assertEqual(500.0, result["average_unit_size"])
        self.assertEqual(0.0864, result["cap_rate"])
        self.assertEqual(10.8, result["noi_per_sf"])
        self.assertEqual(5400.0, result["noi_per_unit"])
        self.assertEqual(6.25, result["pgim"])
        self.assertEqual(6.9444, result["egim"])
        self.assertEqual(7.2, result["expenses_per_sf"])
        self.assertEqual(3600.0, result["expenses_per_unit"])
        self.assertEqual(0.36, result["expenses_as_pct_of_pgi"])
        self.assertEqual(0.4, result["expenses_as_pct_of_egi"])
        self.assertEqual(12, result["months_since_sale"])

    def test_sale_confirmed_validation_requires_baseline_fields(self):
        result = evaluate_manual_comp(
            "sale",
            {
                "property_type": "Retail-Service",
                "address_street": "100 Manual Road",
                "sale_price": "$1,000,000",
                "sale_status": "Closed",
                "gba_sf": "8,000",
                "verification_source": "Broker",
                "cap_rate": "25%",
            },
            status="confirmed",
        )

        self.assertEqual([], result["errors"])
        self.assertEqual("retail_service", result["data"]["property_type"])
        self.assertIn(
            "cap_rate is outside the typical 0% to 20% review range.",
            result["warnings"],
        )
        self.assertIn("verification_notes are recommended.", result["warnings"])

        missing = evaluate_manual_comp(
            "sale",
            {"property_type": "Land", "sale_price": "$500,000"},
            status="confirmed",
        )
        self.assertIn(
            "address or usable location identifier is required to confirm.",
            missing["errors"],
        )
        self.assertIn(
            "sale_date or sale_status is required to confirm.",
            missing["errors"],
        )
        self.assertIn(
            "verification_source is required to confirm.",
            missing["errors"],
        )
        self.assertIn(
            "At least one usable comparison denominator is required to confirm.",
            missing["errors"],
        )

    def test_lease_calculations_derive_rent_and_concessions(self):
        result = calculate_lease_indicators({
            "lease_date": "01/01/2025",
            "lease_expiration": "01/01/2030",
            "sf_leased": "2,500 SF",
            "base_rent_psf": "$24.00",
            "free_rent_months": "2",
            "ti_allowance_psf": "$10.00",
        })

        self.assertEqual(60000.0, result["base_rent_annual"])
        self.assertEqual(5000.0, result["base_rent_monthly"])
        self.assertEqual(24.0, result["rent_psf_year"])
        self.assertEqual(2.0, result["rent_psf_month"])
        self.assertEqual(60, result["term_months"])
        self.assertEqual(5.0, result["term_years"])
        self.assertEqual(10000.0, result["free_rent_value"])
        self.assertEqual(25000.0, result["ti_allowance_total"])
        self.assertEqual(21.2, result["effective_rent_psf"])

    def test_lease_confirmed_validation_requires_terms(self):
        result = evaluate_manual_comp(
            "lease",
            {
                "property_type": "Medical Office",
                "address_street": "200 Lease Lane",
                "sf_leased": "3,000",
                "base_rent_monthly": "$6,000",
                "rent_structure": "Modified Gross",
                "commencement_date": "02/01/2025",
            },
            status="confirmed",
        )

        self.assertEqual([], result["errors"])
        self.assertEqual(72000.0, result["calculations"]["base_rent_annual"])
        self.assertEqual(24.0, result["calculations"]["base_rent_psf"])

        missing = evaluate_manual_comp(
            "lease",
            {"property_type": "Office", "address_street": "Missing Lease"},
            status="confirmed",
        )
        self.assertIn(
            "sf_leased is required to confirm a lease comp.",
            missing["errors"],
        )
        self.assertIn(
            "base rent is required to confirm a lease comp.",
            missing["errors"],
        )
        self.assertIn(
            "rent_structure is required to confirm a lease comp.",
            missing["errors"],
        )
        self.assertIn(
            "lease_date or commencement_date is required to confirm a lease comp.",
            missing["errors"],
        )

    def test_dropdown_baseline_contains_property_profiles(self):
        self.assertIn("retail_service", PROPERTY_TYPE_VALUES)
        self.assertIn("self_storage", PROPERTY_TYPE_VALUES)
        self.assertIn("religious_facility", PROPERTY_TYPE_VALUES)
        self.assertIn("Service Retail", DROPDOWNS["tenant_use"])

    def test_normalization_preserves_controlled_property_type_values(self):
        data = normalize_manual_comp_data({
            "property_type": "Self-Storage",
            "vacancy": "5%",
            "address_state": "al",
        })
        self.assertEqual("self_storage", data["property_type"])
        self.assertEqual(0.05, data["vacancy"])
        self.assertEqual("AL", data["address_state"])


if __name__ == "__main__":
    unittest.main()
