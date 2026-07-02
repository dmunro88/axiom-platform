"""Non-mutating delivery validation for Axiom assignments."""

import contextlib
import importlib.util
import io
import os
import re
import tempfile
import zipfile
from pathlib import Path

import openpyxl

from comp_builder import load_comp_data
from fill_engine import fill_document, load_variables


NARRATIVE_BLOCKS = frozenset({
    "INSPECTION_NARRATIVE",
    "MARKET_AREA_OVERVIEW",
    "SCA_APPROACH_NARRATIVE",
    "SCA_ADJUSTMENT_NARRATIVE",
    "SCA_CONCLUSION_NARRATIVE",
    "CAP_RATE_NARRATIVE",
    "ENCUMBRANCES_NARRATIVE",
    "RECONCILIATION_NARRATIVE",
    "LAND_ADJUSTMENT_NARRATIVE",
})

EXCEL_ERROR_VALUES = frozenset({
    "#NULL!",
    "#DIV/0!",
    "#VALUE!",
    "#REF!",
    "#NAME?",
    "#NUM!",
    "#N/A",
    "#GETTING_DATA",
    "#SPILL!",
    "#CALC!",
})

PLACEHOLDER_PATTERN = re.compile(r"\[\[([A-Z0-9_]+)\]\]")


def _find_variables_json(assignment_dir):
    matches = sorted(Path(assignment_dir).glob("*_variables.json"))
    if len(matches) == 1:
        return matches[0], None
    if not matches:
        return None, "No *_variables.json file found."
    names = ", ".join(path.name for path in matches)
    return None, f"Multiple variables JSON files found: {names}"


def _formula_cache_findings(workbook_path):
    """Return output-formula errors and warnings without modifying the workbook."""
    errors = []
    warnings = []

    try:
        formula_wb = openpyxl.load_workbook(
            workbook_path, data_only=False, read_only=True
        )
        value_wb = openpyxl.load_workbook(
            workbook_path, data_only=True, read_only=True
        )
    except Exception as exc:
        return [f"Workbook could not be read: {exc}"], warnings

    try:
        if "outputs" not in formula_wb.sheetnames:
            return ["Workbook has no outputs sheet."], warnings

        formula_ws = formula_wb["outputs"]
        value_ws = value_wb["outputs"]
        if formula_ws.max_row is None:
            formula_ws.calculate_dimension(force=True)
        if value_ws.max_row is None:
            value_ws.calculate_dimension(force=True)
        uncached = []

        for row_number in range(2, formula_ws.max_row + 1):
            source_key = formula_ws.cell(row=row_number, column=2).value
            cached_key = value_ws.cell(row=row_number, column=2).value
            key = cached_key if cached_key is not None else source_key
            if key is None:
                continue
            key = str(key).strip()
            if key.startswith("="):
                key = f"outputs!B{row_number}"
            if not key or " " in key:
                continue

            has_formula = False
            has_usable_cached_value = False
            for column in (3, 4):
                source_value = formula_ws.cell(
                    row=row_number, column=column
                ).value
                cached_value = value_ws.cell(
                    row=row_number, column=column
                ).value

                if isinstance(source_value, str) and source_value.startswith("="):
                    has_formula = True

                if (
                    isinstance(cached_value, str)
                    and cached_value.upper() in EXCEL_ERROR_VALUES
                ):
                    errors.append(
                        f"{key} has Excel error {cached_value} "
                        f"in outputs!{formula_ws.cell(row=row_number, column=column).coordinate}."
                    )
                elif cached_value not in (None, "", "None"):
                    has_usable_cached_value = True

            if has_formula and not has_usable_cached_value:
                uncached.append(key)

        if uncached:
            unique_keys = sorted(set(uncached))
            preview = ", ".join(unique_keys[:10])
            remainder = len(unique_keys) - 10
            suffix = f" (+{remainder} more)" if remainder > 0 else ""
            warnings.append(
                "Workbook contains formulas without cached Excel results: "
                f"{preview}{suffix}. Open and recalculate/save the workbook "
                "in Excel before relying on delivery output."
            )
    finally:
        formula_wb.close()
        value_wb.close()

    return errors, warnings


def _classify_blocks(blocks, workbook_path):
    handled = []
    unresolved = {}

    anthropic_available = importlib.util.find_spec("anthropic") is not None
    anthropic_key_available = bool(os.environ.get("ANTHROPIC_API_KEY"))

    for block in sorted(blocks):
        if block == "COMP_SHEETS_BLOCK":
            with contextlib.redirect_stdout(io.StringIO()):
                comps = load_comp_data(workbook_path)
            if comps:
                handled.append(block)
            else:
                unresolved[block] = (
                    "Comp-page handler is registered, but the workbook has no "
                    "usable comp_data rows."
                )
            continue

        if block in NARRATIVE_BLOCKS:
            if anthropic_available and anthropic_key_available:
                handled.append(block)
            elif not anthropic_available:
                unresolved[block] = (
                    "Narrative handler requires the anthropic Python package."
                )
            else:
                unresolved[block] = (
                    "Narrative handler requires ANTHROPIC_API_KEY."
                )
            continue

        unresolved[block] = "No pipeline handler is registered for this block."

    return handled, unresolved


def find_docx_placeholders(docx_path):
    """Return unresolved ``[[KEY]]`` placeholders found anywhere in a DOCX."""
    placeholders = set()
    with zipfile.ZipFile(docx_path) as package:
        for name in package.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            text = package.read(name).decode("utf-8", errors="ignore")
            placeholders.update(PLACEHOLDER_PATTERN.findall(text))
    return sorted(placeholders)


def validate_assignment(assignment_dir, templates_dir, deliver_config):
    """
    Validate delivery readiness without writing assignment files or state.

    Warnings are advisory. Errors, missing ordinary placeholders, and unresolved
    block placeholders make ``ready`` false.
    """
    assignment_dir = Path(assignment_dir)
    templates_dir = Path(templates_dir)

    result = {
        "checked": False,
        "ready": False,
        "assignment": assignment_dir.name,
        "errors": [],
        "warnings": [],
        "missing": [],
        "blocks": [],
        "handled_blocks": [],
        "unresolved_blocks": {},
    }

    if not assignment_dir.is_dir():
        result["errors"].append(f"Assignment directory not found: {assignment_dir}")
        return result

    json_path, json_error = _find_variables_json(assignment_dir)
    if json_error:
        result["errors"].append(json_error)

    workbook_path = assignment_dir / "workbook.xlsx"
    if not workbook_path.exists():
        result["errors"].append("workbook.xlsx not found.")

    documents = deliver_config.get("documents", [])
    if not documents:
        result["errors"].append("No delivery document is configured.")
        return result

    template_name = documents[0].get("template")
    template_path = templates_dir / template_name if template_name else None
    if not template_name:
        result["errors"].append("Delivery template name is missing from config.")
    elif not template_path.exists():
        result["errors"].append(f"Delivery template not found: {template_name}")

    if result["errors"]:
        return result

    formula_errors, formula_warnings = _formula_cache_findings(workbook_path)
    result["errors"].extend(formula_errors)
    result["warnings"].extend(formula_warnings)

    if json_path.stat().st_mtime < workbook_path.stat().st_mtime:
        result["warnings"].append(
            "The variables JSON is older than workbook.xlsx. This can be normal "
            "after calculation work, but Intake changes may not have been exported."
        )

    try:
        variables = load_variables(
            json_path=json_path,
            workbook_path=workbook_path,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            scratch_path = Path(temp_dir) / "validation.docx"
            fill_result = fill_document(template_path, scratch_path, variables)
    except Exception as exc:
        result["errors"].append(f"Template fill validation failed: {exc}")
        return result

    result["checked"] = True
    result["missing"] = fill_result["missing"]
    result["blocks"] = fill_result["blocks"]

    handled, unresolved = _classify_blocks(result["blocks"], workbook_path)
    result["handled_blocks"] = handled
    result["unresolved_blocks"] = unresolved
    result["ready"] = not (
        result["errors"]
        or result["missing"]
        or result["unresolved_blocks"]
    )
    return result
