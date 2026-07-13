"""Build a sale/lease comp review packet from staged ingest batches.

This is a non-mutating helper for the real-archive import step. It reads
`ingest/staged/*.json`, keeps only the latest staged batch per assignment
folder, and writes a CSV plus a short Markdown summary under scratch/ so the
human review step has one compact artifact to work from before anything is
confirmed or committed to axiom.db.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
STAGED_DIR = BASE_DIR / "ingest" / "staged"
OUTPUT_DIR = BASE_DIR / "scratch" / "staged_comp_review"


def _latest_staged_batches(staged_dir):
    latest = {}
    for path in staged_dir.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                batch = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(batch, dict):
            continue
        folder_name = batch.get("folder_name") or path.stem
        current = latest.get(folder_name)
        if current is None or path.stat().st_mtime_ns > current[0].stat().st_mtime_ns:
            latest[folder_name] = (path, batch)
    return [latest[key] for key in sorted(latest)]


def _confidence(record, field):
    return (record.get("confidence") or {}).get(field, "")


def _validation_text(record, key):
    validation = record.get("validation") or {}
    return "; ".join(str(value) for value in validation.get(key, []) if value)


def _source_name(record):
    provenance = record.get("provenance") or {}
    source = (
        provenance.get("source_filename")
        or provenance.get("source_path")
        or record.get("source")
        or ""
    )
    return Path(source).name if source else ""


def _review_rows(batches):
    rows = []
    summary = defaultdict(lambda: {"sales": 0, "leases": 0})
    for path, batch in batches:
        folder_name = batch.get("folder_name") or path.stem
        summary[folder_name]
        for kind, collection in (
            ("sale", batch.get("comps") or []),
            ("lease", batch.get("lease_comps") or []),
        ):
            for index, record in enumerate(collection, start=1):
                data = record.get("data") or {}
                row = {
                    "review_decision": "",
                    "review_notes": "",
                    "staged_file": path.name,
                    "folder_name": folder_name,
                    "record_kind": kind,
                    "record_index": index,
                    "address_street": data.get("address_street") or "",
                    "address_city": data.get("address_city") or "",
                    "address_county": data.get("address_county") or "",
                    "property_type": data.get("property_type") or "",
                    "property_subtype": data.get("property_subtype") or "",
                    "sale_price": data.get("sale_price") or "",
                    "sale_date": data.get("sale_date") or "",
                    "price_per_sf": data.get("price_per_sf") or "",
                    "cap_rate": data.get("cap_rate") or "",
                    "tenant_name": data.get("tenant_name") or "",
                    "lease_date": data.get("lease_date") or "",
                    "sf_leased": data.get("sf_leased") or "",
                    "base_rent_psf": data.get("base_rent_psf") or "",
                    "rent_structure": data.get("rent_structure") or "",
                    "source": _source_name(record),
                    "identity_key": record.get("identity_key") or "",
                    "errors": _validation_text(record, "errors"),
                    "warnings": _validation_text(record, "warnings"),
                    "address_confidence": _confidence(record, "address_street"),
                    "price_confidence": _confidence(record, "sale_price"),
                    "rent_confidence": _confidence(record, "base_rent_psf"),
                }
                rows.append(row)
                summary[folder_name]["sales" if kind == "sale" else "leases"] += 1
    return rows, summary


def _write_csv(rows, output_path):
    fieldnames = [
        "review_decision",
        "review_notes",
        "folder_name",
        "record_kind",
        "record_index",
        "address_street",
        "address_city",
        "address_county",
        "property_type",
        "property_subtype",
        "sale_price",
        "sale_date",
        "price_per_sf",
        "cap_rate",
        "tenant_name",
        "lease_date",
        "sf_leased",
        "base_rent_psf",
        "rent_structure",
        "source",
        "warnings",
        "errors",
        "address_confidence",
        "price_confidence",
        "rent_confidence",
        "identity_key",
        "staged_file",
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(batches, rows, summary, output_path):
    lines = [
        "# Staged Comp Review Packet",
        "",
        f"- Latest staged assignment batches: {len(batches)}",
        f"- Sale/lease rows for review: {len(rows)}",
        f"- Source staged folder: `{STAGED_DIR}`",
        "",
        "| Assignment | Sale Comps | Lease Comps |",
        "|---|---:|---:|",
    ]
    for folder_name in sorted(summary):
        counts = summary[folder_name]
        lines.append(
            f"| {folder_name} | {counts['sales']} | {counts['leases']} |"
        )
    lines.extend([
        "",
        "## Latest staged files",
        "",
    ])
    for path, batch in batches:
        folder_name = batch.get("folder_name") or path.stem
        lines.append(f"- `{path.name}` - {folder_name}")
    lines.extend([
        "",
        "Suggested review decisions for the CSV: keep, edit, skip.",
        "Older duplicate staged files may still exist in `ingest/staged`; this",
        "packet intentionally selects only the newest batch per assignment.",
        "This packet does not confirm records, move staged files, or write axiom.db.",
    ])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    batches = _latest_staged_batches(STAGED_DIR)
    rows, summary = _review_rows(batches)
    csv_path = OUTPUT_DIR / "latest_sale_lease_comp_review.csv"
    summary_path = OUTPUT_DIR / "latest_sale_lease_comp_review.md"
    _write_csv(rows, csv_path)
    _write_summary(batches, rows, summary, summary_path)
    print(f"Wrote {len(rows)} sale/lease row(s) from {len(batches)} staged batch(es).")
    print(csv_path)
    print(summary_path)


if __name__ == "__main__":
    main()
