"""Build a complete, deterministic DEMO-001 report for structural QA."""

import json
from pathlib import Path

from comp_builder import inject_comp_section
from adjustment_grid import inject_all_adjustment_grids
from field_registry import load_registry
from fill_engine import fill_document, load_variables
from media_blocks import inject_media_blocks
from structured_blocks import inject_ownership_history
from validation import NARRATIVE_BLOCKS, find_docx_placeholders


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = PROJECT_ROOT / "tests" / "fixtures" / "DEMO-001"

FORMULA_OVERRIDES = {
    "SCA_COMP_UNIT_LOW": "$118.00",
    "SCA_COMP_UNIT_HIGH": "$142.00",
    "SCA_COMP_UNIT_MEDIAN": "$130.00",
    "SCA_COMP_UNIT_MEAN": "$131.00",
    "SCA_ADJ_UNIT_LOW": "$120.00",
    "SCA_ADJ_UNIT_HIGH": "$140.00",
    "SCA_ADJ_UNIT_MEDIAN": "$131.00",
    "SCA_ADJ_UNIT_MEAN": "$132.00",
    "SCA_COMP_SIZE_MEAN": "13,250 SF",
    "SCA_COMP_SIZE_MEDIAN": "13,000 SF",
}


def build_complete_demo_report(output_path):
    output_path = Path(output_path)
    with open(PROJECT_ROOT / "config.json", encoding="utf-8") as config_file:
        config = json.load(config_file)

    variables = load_variables(
        json_path=ASSIGNMENT / "DEMO-001_variables.json",
        workbook_path=ASSIGNMENT / "workbook.xlsx",
    )
    variables.update(FORMULA_OVERRIDES)
    variables.update({
        block: (
            f"Fictional QA narrative for {block}. "
            "This text exists only to exercise deterministic report layout."
        )
        for block in NARRATIVE_BLOCKS
    })

    registry = load_registry(PROJECT_ROOT / config["field_registry"])
    optional_blank_keys = {
        key
        for key, definition in registry["fields"].items()
        if definition.get("required") is False
    }
    result = fill_document(
        PROJECT_ROOT
        / config["templates_dir"]
        / config["stages"]["deliver"]["documents"][0]["template"],
        output_path,
        variables,
        optional_blank_keys=optional_blank_keys,
    )
    if result["missing"]:
        raise AssertionError(f"Unexpected missing fields: {result['missing']}")

    comp_count = inject_comp_section(
        output_path,
        PROJECT_ROOT / "templates" / "comp_block_template.docx",
        ASSIGNMENT / "workbook.xlsx",
    )
    if comp_count != 3:
        raise AssertionError(f"Expected 3 comp pages, got {comp_count}")
    inject_media_blocks(output_path, ASSIGNMENT)
    if not inject_ownership_history(output_path, variables):
        raise AssertionError("Ownership history was not injected")

    # DEMO-001 has CA_DEVELOPED = "No" (this fixture models an assignment
    # where the Cost Approach wasn't developed due to age/depreciation
    # reliability concerns -- see CA_DEVELOPED_FULL above). fill_document's
    # _remove_conditional_sections strips the whole "Cost Approach" section
    # for that reason, and the land value sub-section -- including the
    # LAND_ADJUSTMENT_GRID_BLOCK / LAND_QUALITATIVE_GRID_BLOCK markers --
    # lives inside that section in the template. So those two blocks are
    # correctly gone by the time grid injection runs, and 0 rows for them
    # is the right outcome here, not a bug. Only the SCA-side grids (which
    # live in the Sales Comparison Approach section, developed for this
    # assignment) are expected to inject for this particular fixture.
    # Land-side grid injection itself is covered independently by
    # test_adjustment_grid.py, which builds a document/workbook pair where
    # a land value section is actually present.
    grid_results = inject_all_adjustment_grids(
        output_path, ASSIGNMENT / "workbook.xlsx"
    )
    expected_injected = {"SCA_ADJUSTMENT_GRID_BLOCK", "SCA_QUALITATIVE_GRID_BLOCK"}
    missing_grids = [
        block
        for block in expected_injected
        if not grid_results.get(block)
    ]
    if missing_grids:
        raise AssertionError(f"Adjustment grid(s) not injected: {missing_grids}")

    placeholders = find_docx_placeholders(output_path)
    if placeholders:
        raise AssertionError(f"Unexpected placeholders: {placeholders}")
    return output_path
