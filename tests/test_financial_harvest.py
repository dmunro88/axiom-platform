import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl
from docx import Document

from comparable_contract import confirm_extraction_result
from db import (
    get_conn,
    init_db,
    search_operating_expenses,
    search_rent_roll_entries,
)
from harvest_contract import (
    EXPENSE_CONTRACT_ID,
    RENT_ROLL_CONTRACT_ID,
)
from ingest import commit_extraction_result, run_extraction


def _build_report(path):
    document = Document()
    document.add_paragraph("Subject Property: 777 Fictional Finance Road")
    document.add_paragraph("Effective Date: June 30, 2025")
    document.add_paragraph("Reconciled Value: $2,500,000")
    document.save(path)


def _build_rent_roll(path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Rent Roll"
    sheet["A1"] = "Fictional Rent Roll As of June 30, 2025"
    sheet.append([])
    sheet.append([
        "Suite",
        "Tenant",
        "Use",
        "Rentable SF",
        "Lease Start",
        "Expiration",
        "Monthly Rent",
        "Annual Rent",
        "Rent/SF",
        "Rent Structure",
        "Status",
    ])
    first = [
        "101",
        "Fictional Tenant Alpha",
        "Office",
        1_000,
        date(2024, 1, 1),
        date(2028, 12, 31),
        2_000,
        24_000,
        24,
        "Modified Gross",
        "Occupied",
    ]
    sheet.append(first)
    sheet.append([
        "102",
        "Fictional Tenant Beta",
        "Office",
        1_500,
        date(2025, 3, 1),
        date(2030, 2, 28),
        3_250,
        39_000,
        26,
        "NNN",
        "Occupied",
    ])
    sheet.append(first)  # exact duplicate should collapse before review
    sheet.append(["Total", None, None, 2_500, None, None, 5_250])
    workbook.save(path)
    workbook.close()


def _build_expenses(path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Operating Expenses"
    sheet.append([
        "Expense Category",
        "Period Year",
        "Period Type",
        "Amount",
        "Per SF",
        "Notes",
    ])
    first = [
        "Real Estate Taxes",
        2025,
        "Actual",
        25_000,
        10,
        "Fictional QA",
    ]
    sheet.append(first)
    sheet.append([
        "Insurance",
        2025,
        "Actual",
        12_500,
        5,
        "Fictional QA",
    ])
    sheet.append(first)  # exact duplicate should collapse
    sheet.append(["Total Operating Expenses", 2025, "Actual", 37_500, 15])
    workbook.save(path)
    workbook.close()


def _build_wide_expenses(path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Operating Statement"
    sheet.append([None, "2023", None, "2024", None, "2025 Budget", "Notes"])
    sheet.append([
        "Expense Category",
        "Actual",
        "Actual $/SF",
        "Actual",
        "Actual $/SF",
        "Budget",
        "Notes",
    ])
    sheet.append([
        "Real Estate Taxes",
        20_000,
        8,
        25_000,
        10,
        30_000,
        "Fictional two-row header",
    ])
    sheet.append([
        "Insurance",
        10_000,
        4,
        12_000,
        4.8,
        15_000,
        "Fictional two-row header",
    ])
    sheet.append([
        "Total Operating Expenses",
        30_000,
        12,
        37_000,
        14.8,
        45_000,
        None,
    ])
    workbook.save(path)
    workbook.close()


class FinancialHarvestTests(unittest.TestCase):
    def test_contract_descriptor_matches_financial_runtime(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "schemas"
            / "historical_harvest.v1.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            RENT_ROLL_CONTRACT_ID,
            schema["contracts"]["rent_roll"],
        )
        self.assertEqual(
            EXPENSE_CONTRACT_ID,
            schema["contracts"]["expense"],
        )

    def test_fictional_rent_roll_and_expenses_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assignment = (
                root
                / "historical"
                / "25C900 - Office - 777 Fictional Finance Road, Demo City"
            )
            assignment.mkdir(parents=True)
            _build_report(assignment / "REPORT 25C900.docx")
            _build_rent_roll(assignment / "Fictional Rent Roll.xlsx")
            _build_expenses(assignment / "Operating Expenses 2025.xlsx")

            staged_paths = run_extraction(
                root / "historical",
                staged_dir=root / "staged",
            )
            self.assertEqual(1, len(staged_paths))
            staged = json.loads(staged_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(2, len(staged["rent_roll_entries"]))
            self.assertEqual(2, len(staged["expense_records"]))

            rent = staged["rent_roll_entries"][0]
            expense = staged["expense_records"][0]
            self.assertEqual(RENT_ROLL_CONTRACT_ID, rent["contract_id"])
            self.assertEqual(EXPENSE_CONTRACT_ID, expense["contract_id"])
            self.assertEqual("2025-06-30", rent["data"]["as_of_date"])
            self.assertEqual("2024-01-01", rent["data"]["lease_start"])
            self.assertEqual(
                "worksheet:Rent Roll:row:4",
                rent["provenance"]["source_locator"],
            )
            self.assertEqual(
                "worksheet:Operating Expenses:row:2",
                expense["provenance"]["source_locator"],
            )
            self.assertEqual("unreviewed", rent["review"]["status"])

            rent["data"]["monthly_rent"] = 2_100
            rent["review_edits"] = [{
                "field": "monthly_rent",
                "before": 2_000,
                "after": 2_100,
            }]
            confirmed = confirm_extraction_result(
                staged,
                reviewer="fictional-financial-qa",
                reviewed_at="2026-07-01T15:00:00+00:00",
            )

            db_path = root / "financial.db"
            init_db(db_path, quiet=True)
            connection = get_conn(db_path)
            try:
                with connection:
                    counts = commit_extraction_result(confirmed, connection)
                self.assertEqual(2, counts["rent_roll_entries"])
                self.assertEqual(2, counts["operating_expenses"])
                with connection:
                    duplicates = commit_extraction_result(confirmed, connection)
                self.assertEqual(
                    2,
                    duplicates["duplicate_rent_roll_entries"],
                )
                self.assertEqual(
                    2,
                    duplicates["duplicate_operating_expenses"],
                )
            finally:
                connection.close()

            rent_rows = search_rent_roll_entries(
                db_path,
                tenant_contains="Alpha",
                as_of_date="2025-06-30",
            )
            expense_rows = search_operating_expenses(
                db_path,
                period_year=2025,
                category_contains="tax",
            )
            self.assertEqual(1, len(rent_rows))
            self.assertEqual(2_100, rent_rows[0]["monthly_rent"])
            self.assertEqual("25C900", rent_rows[0]["file_no"])
            self.assertEqual("confirmed", rent_rows[0]["review_status"])
            self.assertEqual(1, len(expense_rows))
            self.assertEqual(25_000, expense_rows[0]["amount"])
            self.assertEqual("confirmed", expense_rows[0]["review_status"])

    def test_wide_operating_statement_explodes_to_expense_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assignment = (
                root
                / "historical"
                / "25C902 - Office - 999 Fictional Finance Road, Demo City"
            )
            assignment.mkdir(parents=True)
            _build_report(assignment / "REPORT 25C902.docx")
            _build_wide_expenses(
                assignment / "Wide Operating Statement 2023-2025.xlsx"
            )

            staged_path = run_extraction(
                root / "historical",
                staged_dir=root / "staged",
            )[0]
            staged = json.loads(staged_path.read_text(encoding="utf-8"))
            self.assertEqual(6, len(staged["expense_records"]))

            taxes_2023 = next(
                record
                for record in staged["expense_records"]
                if record["data"]["category"] == "Real Estate Taxes"
                and record["data"]["period_year"] == 2023
            )
            taxes_2025 = next(
                record
                for record in staged["expense_records"]
                if record["data"]["category"] == "Real Estate Taxes"
                and record["data"]["period_year"] == 2025
            )
            self.assertEqual(20_000, taxes_2023["data"]["amount"])
            self.assertEqual(8, taxes_2023["data"]["amount_per_sf"])
            self.assertEqual("actual", taxes_2023["data"]["period_type"])
            self.assertEqual("budget", taxes_2025["data"]["period_type"])
            self.assertEqual(
                "worksheet:Operating Statement:row:3:cols:2-3",
                taxes_2023["provenance"]["source_locator"],
            )
            self.assertEqual(
                "wide_operating_statement",
                taxes_2023["provenance"]["layout"],
            )

            confirmed = confirm_extraction_result(
                staged,
                reviewer="fictional-wide-financial-qa",
                reviewed_at="2026-07-02T15:00:00+00:00",
            )
            db_path = root / "wide-financial.db"
            init_db(db_path, quiet=True)
            connection = get_conn(db_path)
            try:
                with connection:
                    counts = commit_extraction_result(confirmed, connection)
                self.assertEqual(6, counts["operating_expenses"])
                rows = connection.execute(
                    """
                    SELECT amount, amount_per_sf, period_type, source_record_json
                    FROM operating_expenses
                    WHERE category = ? AND period_year = ?
                    """,
                    ("Real Estate Taxes", 2025),
                ).fetchall()
                self.assertEqual(1, len(rows))
                self.assertEqual(30_000, rows[0]["amount"])
                self.assertEqual("budget", rows[0]["period_type"])
                self.assertIn(
                    "wide_operating_statement",
                    rows[0]["source_record_json"],
                )
            finally:
                connection.close()

            searched = search_operating_expenses(
                db_path,
                period_year=2024,
                category_contains="insurance",
            )
            self.assertEqual(1, len(searched))
            self.assertEqual(12_000, searched[0]["amount"])
            self.assertEqual(4.8, searched[0]["amount_per_sf"])

    def test_unconfirmed_financial_row_rolls_back_everything(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assignment = (
                root
                / "historical"
                / "25C901 - Office - 888 Fictional Finance Road, Demo City"
            )
            assignment.mkdir(parents=True)
            _build_report(assignment / "REPORT 25C901.docx")
            _build_rent_roll(assignment / "Fictional Rent Roll.xlsx")
            staged_path = run_extraction(
                root / "historical",
                staged_dir=root / "staged",
            )[0]
            staged = json.loads(staged_path.read_text(encoding="utf-8"))
            confirmed = confirm_extraction_result(staged, reviewer="qa")
            confirmed["rent_roll_entries"][0]["review"]["status"] = "unreviewed"

            db_path = root / "rollback.db"
            init_db(db_path, quiet=True)
            connection = get_conn(db_path)
            try:
                with self.assertRaisesRegex(ValueError, "not been confirmed"):
                    with connection:
                        commit_extraction_result(confirmed, connection)
                for table in (
                    "assignments",
                    "rent_roll_entries",
                    "source_documents",
                ):
                    self.assertEqual(
                        0,
                        connection.execute(
                            f"SELECT count(*) FROM {table}"
                        ).fetchone()[0],
                    )
            finally:
                connection.close()

    def test_database_initialization_adds_financial_tables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "fresh.db"
            init_db(db_path, quiet=True)
            connection = get_conn(db_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertIn("rent_roll_entries", tables)
                self.assertIn("operating_expenses", tables)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
