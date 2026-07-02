"""Deterministic structural signatures for generated Word documents."""

import hashlib
import zipfile
from collections import Counter
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from lxml import etree


VOLATILE_ATTRIBUTE_NAMES = frozenset({
    "paraId",
    "textId",
    "rsid",
    "rsidDel",
    "rsidP",
    "rsidR",
    "rsidRDefault",
    "rsidRPr",
    "rsidRoot",
    "rsidSect",
    "rsidTr",
})


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _normalized_xml_hash(xml_bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(xml_bytes, parser=parser)
    for element in root.iter():
        for attribute in list(element.attrib):
            if etree.QName(attribute).localname in VOLATILE_ATTRIBUTE_NAMES:
                del element.attrib[attribute]
    return _sha256(etree.tostring(root, method="c14n"))


def _relationship_signature(package):
    relationships = []
    for name in sorted(package.namelist()):
        if not name.startswith("word/") or not name.endswith(".rels"):
            continue
        root = etree.fromstring(package.read(name))
        for relationship in root:
            relationships.append({
                "part": name,
                "type": relationship.get("Type", ""),
                "target": relationship.get("Target", ""),
                "target_mode": relationship.get("TargetMode", ""),
            })
    return sorted(
        relationships,
        key=lambda item: (
            item["part"],
            item["type"],
            item["target"],
            item["target_mode"],
        ),
    )


def docx_structure_signature(docx_path):
    """Return a metadata-normalized, JSON-serializable DOCX signature."""
    docx_path = Path(docx_path)
    with zipfile.ZipFile(docx_path) as package:
        corrupt_part = package.testzip()
        if corrupt_part:
            raise ValueError(f"Corrupt DOCX package part: {corrupt_part}")

        word_parts = sorted(
            name for name in package.namelist() if name.startswith("word/")
        )
        xml_hashes = {
            name: _normalized_xml_hash(package.read(name))
            for name in word_parts
            if name.endswith(".xml")
        }
        media_hashes = {
            name: _sha256(package.read(name))
            for name in word_parts
            if name.startswith("word/media/")
        }
        relationships = _relationship_signature(package)

    document = Document(str(docx_path))
    body = document.element.body
    paragraph_styles = Counter()
    paragraph_text = []
    for paragraph in body.iter(qn("w:p")):
        properties = paragraph.find(qn("w:pPr"))
        style = properties.find(qn("w:pStyle")) if properties is not None else None
        paragraph_styles[
            style.get(qn("w:val")) if style is not None else "(none)"
        ] += 1
        paragraph_text.append(
            "".join(node.text or "" for node in paragraph.iter(qn("w:t")))
        )

    tables = []
    for table in body.iter(qn("w:tbl")):
        rows = list(table.iterchildren(qn("w:tr")))
        tables.append({
            "rows": len(rows),
            "cells_per_row": [
                len(list(row.iterchildren(qn("w:tc"))))
                for row in rows
            ],
        })

    sections = []
    for section in document.sections:
        sections.append({
            "width": section.page_width,
            "height": section.page_height,
            "top_margin": section.top_margin,
            "right_margin": section.right_margin,
            "bottom_margin": section.bottom_margin,
            "left_margin": section.left_margin,
        })

    return {
        "word_parts": word_parts,
        "xml_hashes": xml_hashes,
        "media_hashes": media_hashes,
        "relationships": relationships,
        "paragraph_count": len(paragraph_text),
        "paragraph_styles": dict(sorted(paragraph_styles.items())),
        "paragraph_text_hash": _sha256(
            "\n".join(paragraph_text).encode("utf-8")
        ),
        "table_count": len(tables),
        "tables": tables,
        "inline_shape_count": len(document.inline_shapes),
        "page_break_count": sum(
            1
            for node in body.iter(qn("w:br"))
            if node.get(qn("w:type")) == "page"
        ),
        "section_count": len(sections),
        "sections": sections,
    }
