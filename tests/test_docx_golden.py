import json
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from docx_qa import docx_structure_signature
from tests.demo_report_builder import PROJECT_ROOT, build_complete_demo_report


class GeneratedDocxGoldenTests(unittest.TestCase):
    def test_complete_demo_report_matches_structural_golden(self):
        golden_path = (
            PROJECT_ROOT / "tests" / "golden" / "demo_report_structure.json"
        )
        with open(golden_path, encoding="utf-8") as golden_file:
            expected = json.load(golden_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "demo-report.docx"
            build_complete_demo_report(report_path)
            actual = docx_structure_signature(report_path)

        self.assertEqual(expected, actual)

    def test_complete_demo_report_has_valid_unique_image_relationships(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "demo-report.docx"
            build_complete_demo_report(report_path)
            document = Document(report_path)
            drawing_ids = [
                element.get("id")
                for element in document.element.body.iter(qn("wp:docPr"))
            ]
            self.assertEqual(len(drawing_ids), len(set(drawing_ids)))
            for shape in document.inline_shapes:
                relationship_id = (
                    shape._inline.graphic.graphicData.pic.blipFill.blip.get(
                        qn("r:embed")
                    )
                )
                related_part = document.part.related_parts[relationship_id]
                self.assertTrue(
                    related_part.content_type.startswith("image/"),
                    related_part.partname,
                )
                self.assertTrue(shape._inline.docPr.get("descr"))


if __name__ == "__main__":
    unittest.main()
