"""Bootstrap the authoritative field registry from the verified baseline."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from field_registry import build_registry  # noqa: E402


def main():
    with open(PROJECT_ROOT / "config.json", encoding="utf-8") as config_file:
        config = json.load(config_file)

    registry = build_registry(
        workbook_path=PROJECT_ROOT / config["workbook_template"],
        templates_dir=PROJECT_ROOT / config["templates_dir"],
        stages=config["stages"],
        fixture_json_path=(
            PROJECT_ROOT
            / "tests"
            / "fixtures"
            / "DEMO-001"
            / "DEMO-001_variables.json"
        ),
    )
    output_path = PROJECT_ROOT / config["field_registry"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as registry_file:
        json.dump(registry, registry_file, indent=2)
        registry_file.write("\n")
    print(
        f"Wrote {len(registry['fields'])} fields and "
        f"{len(registry['blocks'])} blocks to {output_path}"
    )


if __name__ == "__main__":
    main()
