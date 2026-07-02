"""Index external and Word-embedded source artifacts without copying them."""

import hashlib
import io
import mimetypes
import posixpath
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

try:
    from PIL import Image
except ImportError:  # pragma: no cover - openpyxl normally provides Pillow
    Image = None


EXTERNAL_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
SKIP_DIRECTORIES = {
    ".git",
    ".sanitization_work",
    "__pycache__",
    "ingest",
    "node_modules",
    "outputs",
}
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
DRAWING_NS = (
    "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
)
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _dimensions(data):
    if Image is None:
        return None, None
    try:
        with Image.open(io.BytesIO(data)) as image:
            return image.width, image.height
    except Exception:
        return None, None


def _kind(name, extension, container_name=""):
    text = f"{name} {container_name}".casefold()
    if any(label in text for label in (
        "location map",
        "regional map",
        "aerial",
        "flood map",
        "fema",
        "zoning map",
        "tax map",
        "parcel map",
        "site map",
        "map",
    )):
        return "map"
    if any(label in text for label in ("chart", "graph", "trend")):
        return "chart"
    if any(label in text for label in (
        "sketch",
        "floor plan",
        "site plan",
        "building plan",
    )):
        return "sketch"
    if any(label in text for label in ("logo", "signature", "seal")):
        return "decorative"
    if extension.casefold() == ".pdf":
        return "exhibit"
    if "exhibit" in text:
        return "exhibit_image"
    return "photo"


def _record(
    *,
    source_path,
    source_locator,
    artifact_filename,
    title,
    artifact_bytes,
    container_filename=None,
):
    extension = Path(artifact_filename).suffix.lower()
    width, height = _dimensions(artifact_bytes)
    data = {
        "artifact_kind": _kind(
            title or artifact_filename,
            extension,
            container_filename or "",
        ),
        "title": title or Path(artifact_filename).stem,
        "artifact_filename": artifact_filename,
        "container_filename": container_filename,
        "media_type": (
            mimetypes.guess_type(artifact_filename)[0]
            or "application/octet-stream"
        ),
        "extension": extension,
        "artifact_sha256": _hash_bytes(artifact_bytes),
        "artifact_size": len(artifact_bytes),
        "width_px": width,
        "height_px": height,
    }
    return {
        "data": data,
        "confidence": {
            "artifact_kind": "medium",
            "title": "medium",
            "artifact_sha256": "high",
            "artifact_size": "high",
            "width_px": "high" if width is not None else "unknown",
            "height_px": "high" if height is not None else "unknown",
        },
        "source": str(source_path),
        "source_locator": source_locator,
    }


def _relationship_map(archive, xml_part):
    part = PurePosixPath(xml_part)
    rels_part = str(part.parent / "_rels" / f"{part.name}.rels")
    if rels_part not in archive.namelist():
        return {}
    root = ElementTree.fromstring(archive.read(rels_part))
    relationships = {}
    for relationship in root.findall(f"{{{REL_NS}}}Relationship"):
        if not relationship.get("Type", "").endswith("/image"):
            continue
        target = relationship.get("Target")
        if not target:
            continue
        resolved = posixpath.normpath(
            posixpath.join(str(part.parent), target)
        )
        relationships[relationship.get("Id")] = resolved
    return relationships


def extract_embedded_docx_artifacts(path):
    """Return image artifacts referenced by document/header/footer drawings."""
    path = Path(path)
    records = []
    warnings = []
    try:
        with zipfile.ZipFile(path) as archive:
            xml_parts = [
                name
                for name in archive.namelist()
                if (
                    name == "word/document.xml"
                    or name.startswith("word/header")
                    or name.startswith("word/footer")
                )
                and name.endswith(".xml")
            ]
            for xml_part in sorted(xml_parts):
                relationships = _relationship_map(archive, xml_part)
                root = ElementTree.fromstring(archive.read(xml_part))
                drawings = root.findall(f".//{{{WORD_NS}}}drawing")
                for index, drawing in enumerate(drawings, 1):
                    blip = drawing.find(f".//{{{A_NS}}}blip")
                    if blip is None:
                        continue
                    relationship_id = blip.get(f"{{{OFFICE_REL_NS}}}embed")
                    media_part = relationships.get(relationship_id)
                    if not media_part or media_part not in archive.namelist():
                        continue
                    doc_property = drawing.find(f".//{{{DRAWING_NS}}}docPr")
                    title = None
                    if doc_property is not None:
                        title = (
                            doc_property.get("descr")
                            or doc_property.get("title")
                            or doc_property.get("name")
                        )
                    artifact_bytes = archive.read(media_part)
                    records.append(_record(
                        source_path=path,
                        source_locator=f"{xml_part}:drawing:{index}:{media_part}",
                        artifact_filename=PurePosixPath(media_part).name,
                        title=title,
                        artifact_bytes=artifact_bytes,
                        container_filename=path.name,
                    ))
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        warnings.append(f"Could not index embedded media in {path.name}: {exc}")
    return records, warnings


def extract_embedded_xlsx_artifacts(path):
    """Return workbook-embedded images and native chart XML artifacts."""
    path = Path(path)
    records = []
    warnings = []
    try:
        with zipfile.ZipFile(path) as archive:
            for media_part in sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/media/") and not name.endswith("/")
            ):
                records.append(_record(
                    source_path=path,
                    source_locator=f"package:{media_part}",
                    artifact_filename=PurePosixPath(media_part).name,
                    title=PurePosixPath(media_part).stem,
                    artifact_bytes=archive.read(media_part),
                    container_filename=path.name,
                ))
            for chart_part in sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/charts/chart") and name.endswith(".xml")
            ):
                chart_bytes = archive.read(chart_part)
                title = None
                try:
                    root = ElementTree.fromstring(chart_bytes)
                    text_values = [
                        element.text.strip()
                        for element in root.iter()
                        if element.tag.endswith("}t")
                        and element.text
                        and element.text.strip()
                    ]
                    if text_values:
                        title = " ".join(dict.fromkeys(text_values))
                except ElementTree.ParseError:
                    pass
                record = _record(
                    source_path=path,
                    source_locator=f"package:{chart_part}",
                    artifact_filename=PurePosixPath(chart_part).name,
                    title=title or PurePosixPath(chart_part).stem,
                    artifact_bytes=chart_bytes,
                    container_filename=path.name,
                )
                record["data"]["artifact_kind"] = "chart"
                record["data"]["media_type"] = (
                    "application/vnd.openxmlformats-officedocument."
                    "drawingml.chart+xml"
                )
                record["confidence"]["artifact_kind"] = "high"
                records.append(record)
    except (OSError, zipfile.BadZipFile) as exc:
        warnings.append(f"Could not index workbook artifacts in {path.name}: {exc}")
    return records, warnings


def extract_external_artifacts(assignment_root):
    """Return image/PDF artifacts beneath an assignment folder."""
    root = Path(assignment_root)
    records = []
    sources = []
    warnings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTERNAL_EXTENSIONS:
            continue
        if any(part.casefold() in SKIP_DIRECTORIES for part in path.parts):
            continue
        try:
            size = path.stat().st_size
            if size > MAX_ARTIFACT_BYTES:
                warnings.append(
                    f"Artifact exceeds {MAX_ARTIFACT_BYTES // (1024 * 1024)} MB "
                    f"indexing limit: {path.name}"
                )
                continue
            artifact_bytes = path.read_bytes()
        except OSError as exc:
            warnings.append(f"Could not read artifact {path.name}: {exc}")
            continue
        relative = path.relative_to(root).as_posix()
        records.append(_record(
            source_path=path,
            source_locator=f"file:{relative}",
            artifact_filename=path.name,
            title=path.stem,
            artifact_bytes=artifact_bytes,
        ))
        sources.append(str(path))
    return records, sources, warnings


def extract_assignment_artifacts(assignment_root, office_containers):
    """Index external artifacts and embedded media for one assignment."""
    records, sources, warnings = extract_external_artifacts(assignment_root)
    for container in dict.fromkeys(str(path) for path in office_containers):
        if Path(container).suffix.lower() == ".docx":
            embedded, embedded_warnings = extract_embedded_docx_artifacts(
                container
            )
        elif Path(container).suffix.lower() == ".xlsx":
            embedded, embedded_warnings = extract_embedded_xlsx_artifacts(
                container
            )
        else:
            continue
        records.extend(embedded)
        warnings.extend(embedded_warnings)
    return {
        "artifacts": records,
        "sources": sources,
        "warnings": warnings,
    }
