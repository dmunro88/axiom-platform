"""Regenerate the approved DEMO-001 structural DOCX golden fingerprint."""

import argparse
import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from docx_qa import docx_structure_signature  # noqa: E402
from tests.demo_report_builder import build_complete_demo_report  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "tests"
            / "golden"
            / "demo_report_structure.json"
        ),
    )
    parser.add_argument("--report-output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = args.report_output or Path(temp_dir) / "demo-report.docx"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        build_complete_demo_report(report_path)
        signature = docx_structure_signature(report_path)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(signature, output_file, indent=2)
        output_file.write("\n")
    print(f"Wrote structural golden: {args.output}")
    if args.report_output:
        print(f"Wrote QA report: {args.report_output}")


if __name__ == "__main__":
    main()
