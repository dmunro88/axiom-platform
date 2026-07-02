import os
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import openpyxl
from docx import Document

import axiom
from validation import validate_assignment


def _build_assignment(root, template_text, variables=None):
    root = Path(root)
    assignment = root / "TEST-900_Fictional_Client"
    templates = root / "templates"
    assignment.mkdir()
    templates.mkdir()

    workbook = openpyxl.Workbook()
    outputs = workbook.active
    outputs.title = "outputs"
    outputs.append(["Label", "Key", "Raw", "Formatted"])
    workbook.save(assignment / "workbook.xlsx")

    variables = variables or {}
    with open(assignment / "TEST-900_variables.json", "w", encoding="utf-8") as f:
        json.dump(variables, f)

    document = Document()
    document.add_paragraph(template_text)
    document.save(templates / "report.docx")

    config = {"documents": [{"template": "report.docx"}]}
    return assignment, templates, config


class ValidateAssignmentTests(unittest.TestCase):
    def test_ready_when_required_values_are_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assignment, templates, config = _build_assignment(
                temp_dir,
                "Value: [[VALUE_CONCLUSION]]",
                {"VALUE_CONCLUSION": "$1,000,000"},
            )

            result = validate_assignment(assignment, templates, config)

            self.assertTrue(result["checked"])
            self.assertTrue(result["ready"])
            self.assertEqual([], result["missing"])
            self.assertEqual({}, result["unresolved_blocks"])

    def test_missing_value_and_unsupported_block_prevent_readiness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assignment, templates, config = _build_assignment(
                temp_dir,
                "[[VALUE_CONCLUSION]] [[SUBJECT_PHOTOS_BLOCK]]",
            )

            result = validate_assignment(assignment, templates, config)

            self.assertFalse(result["ready"])
            self.assertEqual(["VALUE_CONCLUSION"], result["missing"])
            self.assertIn(
                "SUBJECT_PHOTOS_BLOCK",
                result["unresolved_blocks"],
            )

    def test_narrative_requires_local_api_capability(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assignment, templates, config = _build_assignment(
                temp_dir,
                "[[INSPECTION_NARRATIVE]]",
            )

            with patch.dict(os.environ, {}, clear=True):
                result = validate_assignment(assignment, templates, config)

            self.assertFalse(result["ready"])
            self.assertIn(
                "INSPECTION_NARRATIVE",
                result["unresolved_blocks"],
            )

    def test_failed_validation_cannot_mark_assignment_delivered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assignment = Path(temp_dir) / "TEST-901_Fictional_Client"
            assignment.mkdir()
            initial_state = {
                "file_no": "TEST-901",
                "stage": "new",
                "delivered": None,
            }
            with open(assignment / ".axiom.json", "w", encoding="utf-8") as f:
                json.dump(initial_state, f)

            failed_result = {
                "checked": True,
                "ready": False,
                "errors": [],
                "missing": ["VALUE_CONCLUSION"],
                "unresolved_blocks": {"SUBJECT_PHOTOS_BLOCK": "No handler."},
            }

            with (
                patch.object(axiom, "_find_assignment", return_value=assignment),
                patch.object(
                    axiom,
                    "check_delivery_readiness",
                    return_value=failed_result,
                ),
            ):
                command_result = axiom.cmd_deliver(["TEST-901"])

            with open(assignment / ".axiom.json", encoding="utf-8") as f:
                final_state = json.load(f)

            self.assertFalse(command_result)
            self.assertEqual("new", final_state["stage"])
            self.assertIsNone(final_state["delivered"])
            self.assertEqual("blocked", final_state["last_delivery_status"])
            self.assertEqual(2, final_state["last_delivery_blocker_count"])

    def test_sanitized_fixture_is_readable(self):
        project_root = Path(__file__).resolve().parents[1]
        with open(project_root / "config.json", encoding="utf-8") as config_file:
            config = json.load(config_file)

        result = validate_assignment(
            project_root / "tests" / "fixtures" / "DEMO-001",
            project_root / config["templates_dir"],
            config["stages"]["deliver"],
        )

        self.assertTrue(result["checked"])
        self.assertEqual([], result["missing"])
        self.assertEqual("DEMO-001", result["assignment"])


if __name__ == "__main__":
    unittest.main()
