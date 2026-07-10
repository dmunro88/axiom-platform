"""
adjustment_grid.py — Axiom Commercial Appraisal Platform
==========================================================
Reads the Phase 6 adjustment-grid workbook tabs (sca_adjustment_grid,
land_adjustment_grid, sca_qualitative, land_qualitative) and injects each
as a Word table at its [[..._GRID_BLOCK]] marker.

Unlike comp_builder.py's fixed COMP_COLUMNS letter map, these sheets' column
sets are variable (they depend on adjustment_factors.json's per-property-
type preset), so the header row is read at runtime and the column map is
built from header text -> column index, following docs/ADJUSTMENT_GRID_
DESIGN.md's Pipeline step 6. A hand-added one-off category column, or a
preset with fewer columns, both just work without a code change.

Category adjustments and qualitative factor scores are manual-entry cells;
Time Adjustment, Adjusted Price, Net Adjustment/Overall, and Indicated
Value/Rating are Excel formulas in the sheet (matching size_adj/dilmore's
existing convention). This module opens the workbook with data_only=True
and reads already-computed results -- it performs no calculation itself,
so the workbook must have gone through a real Excel/LibreOffice
recalculation pass for these cells to have cached values.

Called automatically by axiom.py during the deliver stage, gated by the
same `inject_comps` doc_cfg flag as inject_comp_section/inject_media_blocks/
inject_ownership_history. Can also be run standalone:
    python adjustment_grid.py <report_path> <workbook_path>
"""

import sys
from pathlib import Path

from docx import Document
import openpyxl


# Each grid tab's header row and first data row. These match the tabs as
# built (Phase 6 steps 1, 2, 4). MAX_DATA_ROW gives headroom to keep
# reading further populated rows if the sheet is ever hand-expanded beyond
# its current 10-comp capacity, without a code change.
HEADER_ROW = 6
FIRST_DATA_ROW = 7
MAX_DATA_ROW = 40

# The one fixed expectation every grid sheet must satisfy: its header row's
# first column must literally read "Comp". Everything else is discovered
# from the header row text, not a hardcoded position -- if this anchor is
# missing, the sheet doesn't match what this injector expects, and it fails
# loudly (AdjustmentGridError) instead of silently reading garbage, per the
# design doc's drift-protection requirement.
ANCHOR_HEADER = "Comp"

GRIDS = {
    "SCA_ADJUSTMENT_GRID_BLOCK": "sca_adjustment_grid",
    "LAND_ADJUSTMENT_GRID_BLOCK": "land_adjustment_grid",
    "SCA_QUALITATIVE_GRID_BLOCK": "sca_qualitative",
    "LAND_QUALITATIVE_GRID_BLOCK": "land_qualitative",
}


class AdjustmentGridError(Exception):
    """Raised when a grid sheet's header row doesn't match expectations."""


def _format_value(header, value):
    """Render a computed cell value for display, guided by its header text
    (not a fixed column position, since positions vary by preset)."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        header_lower = header.lower()
        if "%" in header:
            return f"{value * 100:.1f}%"
        if any(token in header_lower for token in ("price", "value")) and (
            "$" in header or "sf" in header_lower or "acre" in header_lower
        ):
            return f"${value:,.2f}"
        if header_lower == "overall":
            return f"{value:.2f}"
        if isinstance(value, int):
            return str(value)
        return f"{value:,.2f}"
    if hasattr(value, "strftime"):
        return value.strftime("%m/%d/%Y")
    return str(value).strip()


def _read_header_map(ws):
    """Build {header_text: column_index} from HEADER_ROW, skipping blanks."""
    header_map = {}
    for cell in ws[HEADER_ROW]:
        text = cell.value
        if text is None or str(text).strip() == "":
            continue
        header_map[str(text).strip()] = cell.column

    if header_map.get(ANCHOR_HEADER) != 1:
        raise AdjustmentGridError(
            f"Sheet '{ws.title}' header row {HEADER_ROW} doesn't have "
            f"'{ANCHOR_HEADER}' in column A as expected -- refusing to "
            "guess at a different layout. Check the sheet hasn't been "
            "restructured, or update adjustment_grid.py's ANCHOR_HEADER "
            "expectation if this is an intentional template change."
        )
    return header_map


def read_grid_rows(workbook_path, sheet_name):
    """Read a grid sheet's header row and populated data rows.

    Returns (headers, rows): headers is an ordered list of column header
    strings (left to right, as they appear in the sheet); rows is a list of
    dicts {header: formatted_value_str}, one per populated comp row.

    A row counts as a real comp row only if its Comp/anchor cell literally
    starts with "Sale No." -- every grid tab writes that label into each of
    its fixed comp rows when the tab is built, so it's the one reliable
    signal that distinguishes a genuine comp row from a summary row below
    the comp rows (MEAN, LAND VALUE CONCLUSION, etc.), which can otherwise
    have non-blank values in the same header columns by coincidence of
    position, not because they're actually comp data. Scanning stops at the
    first row whose Comp cell doesn't match, rather than scanning all the
    way to MAX_DATA_ROW and collecting every row with any value -- the
    latter approach collected the MEAN and LAND VALUE CONCLUSION rows on
    land_adjustment_grid's first real test against realistic fixture data.
    """
    wb = openpyxl.load_workbook(str(workbook_path), data_only=True)
    if sheet_name not in wb.sheetnames:
        wb.close()
        return [], []

    ws = wb[sheet_name]
    header_map = _read_header_map(ws)
    headers = [h for h, _ in sorted(header_map.items(), key=lambda kv: kv[1])]
    anchor_col = header_map[ANCHOR_HEADER]

    rows = []
    for r in range(FIRST_DATA_ROW, MAX_DATA_ROW + 1):
        comp_label = ws.cell(row=r, column=anchor_col).value
        if not (isinstance(comp_label, str) and comp_label.startswith("Sale No.")):
            break

        row_values = {}
        any_non_label_value = False
        for header, col_idx in header_map.items():
            value = ws.cell(row=r, column=col_idx).value
            if header != ANCHOR_HEADER and value not in (None, ""):
                any_non_label_value = True
            row_values[header] = _format_value(header, value)
        if not any_non_label_value:
            continue
        rows.append(row_values)

    wb.close()
    return headers, rows


def _build_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    header_cells = table.rows[0].cells
    for idx, header in enumerate(headers):
        header_cells[idx].text = header
        if header_cells[idx].paragraphs[0].runs:
            header_cells[idx].paragraphs[0].runs[0].bold = True

    for row in rows:
        cells = table.add_row().cells
        for idx, header in enumerate(headers):
            cells[idx].text = row.get(header, "")

    return table


def inject_adjustment_grid_block(doc_path, workbook_path, block_name, sheet_name):
    """Replace ``[[<block_name>]]`` with a table built from *sheet_name*.

    Returns the number of comp rows injected. Returns 0 (leaving the marker
    text in place) if the marker isn't found in the document, the sheet
    doesn't exist in the workbook, or the sheet has no populated rows --
    matching inject_ownership_history's convention of a silent no-op rather
    than an error for "nothing to inject yet". A header-row mismatch
    (AdjustmentGridError) is not caught here -- it propagates, per the
    design doc's loud-failure requirement for a sheet that doesn't match
    what this injector expects.
    """
    doc_path = Path(doc_path)
    doc = Document(str(doc_path))
    marker = f"[[{block_name}]]"

    marker_paragraph = None
    for paragraph in doc.paragraphs:
        if marker in paragraph.text:
            marker_paragraph = paragraph
            break

    if marker_paragraph is None:
        return 0

    headers, rows = read_grid_rows(workbook_path, sheet_name)
    if not rows:
        return 0

    table = _build_table(doc, headers, rows)
    marker_paragraph._p.addnext(table._tbl)
    parent = marker_paragraph._p.getparent()
    parent.remove(marker_paragraph._p)

    doc.save(str(doc_path))
    return len(rows)


def inject_all_adjustment_grids(doc_path, workbook_path):
    """Inject all four adjustment-grid blocks found in *doc_path*.

    Returns {block_name: rows_injected}. Each block is handled
    independently -- a missing/empty sheet for one grid doesn't stop the
    others from being injected.
    """
    results = {}
    for block_name, sheet_name in GRIDS.items():
        results[block_name] = inject_adjustment_grid_block(
            doc_path, workbook_path, block_name, sheet_name
        )
    return results


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python adjustment_grid.py <report.docx> <workbook.xlsx>")
        sys.exit(1)

    report_path = Path(sys.argv[1])
    workbook_path = Path(sys.argv[2])

    if not report_path.exists():
        print(f"Error: report not found: {report_path}")
        sys.exit(1)
    if not workbook_path.exists():
        print(f"Error: workbook not found: {workbook_path}")
        sys.exit(1)

    grid_results = inject_all_adjustment_grids(report_path, workbook_path)
    for block, count in grid_results.items():
        print(f"{block}: {count} row(s) injected")
