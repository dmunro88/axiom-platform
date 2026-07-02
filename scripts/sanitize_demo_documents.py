"""Create fictionalized JSON/DOCX fixture artifacts without changing layout."""

import argparse
import json
import re
import zipfile
from pathlib import Path

from lxml import etree


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_TEXT = f"{{{WORD_NS}}}t"
W_PARAGRAPH = f"{{{WORD_NS}}}p"
W_RSID_PREFIX = f"{{{WORD_NS}}}rsid"

PRESERVED_TEXT = (
    "2159 Rocky Ridge Road, Suite 103",
    "Hoover, Alabama 35216",
)

DOCX_SKIPPED_REPLACEMENTS = {
    # Regional context and Axiom's business location may legitimately use this
    # city name. Exact comparable addresses are still fictionalized.
    "Birmingham",
}

JSON_OVERRIDES = {
    "FILE_NO": "DEMO-001",
    "CLIENT_NAME": "Northstar Example Holdings, LLC",
    "CONTACT_NAME": "Jordan Example",
    "CONTACT_SALUTATION": "Ms. Example",
    "CLIENT_ADDR1": "1000 Demonstration Plaza, Suite 200",
    "CLIENT_ADDR2": "Sample City, Alabama 35000",
    "PROPERTY_ADDRESS": "100 Example Commerce Way",
    "PROPERTY_CITY": "Sample City",
    "PROPERTY_COUNTY": "Example County",
    "PROPERTY_STATE": "Alabama",
    "PROPERTY_ZIP": "35000",
    "OWNER_NAME": "Example Property Owner, LLC",
    "SUBMARKET": "Demo North",
    "FEMA_PANEL": "00000C0001A - 01/01/2025",
    "FRONTAGE_STREET": "Example Commerce Way",
    "LEGAL_DESCRIPTION": (
        "Demo Lot 1, Example Commerce Center, fictional legal description "
        "for software testing only"
    ),
    "SERVICE_DESCRIPTION": (
        "Appraisal of 100 Example Commerce Way, Sample City, Alabama 35000"
    ),
    "INVOICE_NO": "DEMO-001",
}

JSON_PRESERVED_KEYS = {
    "REMIT_ADDRESS",
}


def load_profile(path):
    with open(path, encoding="utf-8") as profile_file:
        profile = json.load(profile_file)
    replacements = profile.get("replacements")
    if not replacements:
        raise ValueError(
            "The migration profile must contain a non-empty 'replacements' object. "
            "The canonical demo_profile.json intentionally contains no retired data."
        )
    return dict(sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True))


def replace_text(text, replacements, preserve=()):
    if not text:
        return text

    protected = {}
    for index, value in enumerate(preserve):
        token = f"__AXIOM_PRESERVE_{index}__"
        if value in text:
            text = text.replace(value, token)
            protected[token] = value

    for original, fictional in replacements.items():
        text = text.replace(original, fictional)

    for token, value in protected.items():
        text = text.replace(token, value)
    return text


def _replace_paragraph(paragraph, replacements):
    text_nodes = list(paragraph.iter(W_TEXT))
    if not text_nodes:
        return False

    original_parts = [node.text or "" for node in text_nodes]
    original = "".join(original_parts)
    fictional = replace_text(original, replacements, PRESERVED_TEXT)
    if fictional == original:
        return False

    cursor = 0
    for node, original_part in zip(text_nodes[:-1], original_parts[:-1]):
        width = len(original_part)
        node.text = fictional[cursor:cursor + width]
        cursor += width
    text_nodes[-1].text = fictional[cursor:]
    return True


def _sanitize_word_xml(data, replacements):
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(data, parser)
    changed = False

    for paragraph in root.iter(W_PARAGRAPH):
        changed = _replace_paragraph(paragraph, replacements) or changed

    for element in root.iter():
        for attribute in list(element.attrib):
            if attribute.startswith(W_RSID_PREFIX):
                del element.attrib[attribute]
                changed = True

    if not changed:
        return data
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def _sanitize_core_properties(data):
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(data, parser)
    namespaces = {
        "dc": "http://purl.org/dc/elements/1.1/",
        "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    }
    for expression in ("//dc:creator", "//cp:lastModifiedBy"):
        for element in root.xpath(expression, namespaces=namespaces):
            element.text = "Axiom Platform"
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def sanitize_docx(source, destination, profile_path):
    replacements = load_profile(profile_path)
    replacements = {
        original: fictional
        for original, fictional in replacements.items()
        if original not in DOCX_SKIPPED_REPLACEMENTS
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as input_package:
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output_package:
            for item in input_package.infolist():
                data = input_package.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    data = _sanitize_word_xml(data, replacements)
                elif item.filename == "docProps/core.xml":
                    data = _sanitize_core_properties(data)
                output_package.writestr(item, data)


def _sanitize_json_value(value, replacements):
    if isinstance(value, str):
        return replace_text(value, replacements)
    if isinstance(value, list):
        return [_sanitize_json_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                item
                if key in JSON_PRESERVED_KEYS
                else _sanitize_json_value(item, replacements)
            )
            for key, item in value.items()
        }
    return value


def sanitize_json(source, destination, profile_path):
    replacements = load_profile(profile_path)
    with open(source, encoding="utf-8") as source_file:
        data = json.load(source_file)

    data = _sanitize_json_value(data, replacements)
    for key, value in JSON_OVERRIDES.items():
        if key in data:
            data[key] = value

    if "file_no" in data:
        data["file_no"] = "DEMO-001"
    if "client" in data:
        data["client"] = "Northstar Example Holdings"

    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as destination_file:
        json.dump(data, destination_file, indent=2, ensure_ascii=False)
        destination_file.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("json", "docx"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("source", type=Path)
        subparser.add_argument("destination", type=Path)

    args = parser.parse_args()
    if args.command == "json":
        sanitize_json(args.source, args.destination, args.profile)
    else:
        sanitize_docx(args.source, args.destination, args.profile)


if __name__ == "__main__":
    main()
