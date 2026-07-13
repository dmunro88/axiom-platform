"""Force a real Excel recalculation of an Axiom workbook and save it.

openpyxl can write formulas but cannot compute them; every formula-driven
tab (adjustment grids, income/cost calc sheets, outputs) only has real
cached values after Excel itself opens, recalculates, and saves the file.
This script automates that "open in Excel, press F9, save" step via COM so
it doesn't have to be done by hand before every validate/deliver attempt.

Usage:
    python scripts/recalc_workbook.py <path-to-workbook.xlsx>
"""
import os
import sys

import win32com.client


def recalc_workbook(path: str) -> None:
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(abs_path)

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(abs_path)
        try:
            excel.CalculateFullRebuild()
            wb.Save()
        finally:
            wb.Close(SaveChanges=False)
    finally:
        excel.Quit()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/recalc_workbook.py <path-to-workbook.xlsx>")
        return 1
    recalc_workbook(sys.argv[1])
    print(f"Recalculated and saved: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
