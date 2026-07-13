"""
comp_review.py — Comp Library extraction & review UI
========================================================
Streamlit front-end for the existing extract -> stage -> review -> commit
pipeline (extractor.py / ingest.py / db.py). Nothing here reimplements
extraction rules or database logic -- it only replaces ingest.py's
input()-based review_staged() loop with Streamlit widgets (checkboxes +
text inputs instead of a blocking terminal prompt), and calls
run_extraction() / commit_confirmed() directly for the other two steps.
Staged/confirmed files use the exact same folder + suffix conventions as
the CLI (ingest/staged/*.json -> .done or .skipped, ingest/confirmed/*.json
-> .committed), so `python ingest.py review` / `commit` still work
standalone if Derek ever needs them.

Usage: import render_comp_library() and call it from axiom_ui.py.
"""

import io
import hashlib
import json
import contextlib
import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from ingest import STAGED_DIR, run_extraction, commit_confirmed
from extractor import _coerce as _extractor_coerce
from comparable_contract import confirm_extraction_result
import db as db_module

CONFIRMED_DIR = STAGED_DIR.parent / "confirmed"
CONFIRMED_DIR.mkdir(exist_ok=True)
LOCAL_MEDIA_DIR = Path(__file__).parent / ".local" / "comp_media"
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png"}

_SALE_EDIT_FIELDS = [
    ("address_street", "Address"), ("address_city", "City"),
    ("address_county", "County"), ("sale_price", "Sale Price"),
    ("sale_date", "Sale Date"), ("gba_sf", "GBA (SF)"), ("cap_rate", "Cap Rate"),
]
_LEASE_EDIT_FIELDS = [
    ("address_street", "Address"), ("address_city", "City"),
    ("sf_leased", "SF Leased"), ("base_rent_psf", "Base Rent/SF"),
    ("rent_structure", "Structure"), ("lease_date", "Lease Date"),
]

_SALE_DISPLAY_FIELDS = [
    ("address_street", "Address"), ("address_city", "City"),
    ("sale_price", "Sale Price"), ("sale_date", "Sale Date"),
    ("gba_sf", "GBA (SF)"), ("price_per_sf", "Price/SF"),
    ("cap_rate", "Cap Rate"), ("noi", "NOI"), ("year_built", "Year Built"),
    ("property_type", "Property Type"), ("grantor", "Grantor"),
    ("grantee", "Grantee"), ("deed_ref", "Deed Ref"),
    ("verification_source", "Verification"), ("submarket", "Submarket"),
]
_LEASE_DISPLAY_FIELDS = [
    ("address_street", "Address"), ("address_city", "City"),
    ("tenant_name", "Tenant"), ("tenant_use", "Use"),
    ("lease_date", "Lease Date"), ("term_years", "Term (yrs)"),
    ("sf_leased", "SF Leased"), ("base_rent_psf", "Base Rent/SF"),
    ("rent_structure", "Structure"), ("escalations", "Escalations"),
    ("renewal_options", "Options"), ("ti_allowance_psf", "TI Allow/SF"),
    ("free_rent_months", "Free Rent"), ("submarket", "Submarket"),
]
_ASSIGNMENT_EDIT_FIELDS = [
    ("file_no", "File Number"), ("client", "Client"),
    ("effective_date", "Effective Date"), ("report_date", "Report Date"),
    ("sca_value", "SCA Value"), ("ia_value", "IA Value"),
    ("ca_value", "Cost Value"), ("reconciled_value", "Reconciled Value"),
]
_INCOME_EDIT_FIELDS = [
    ("period_year", "Period Year"), ("period_type", "Period Type"),
    ("pgi", "Potential Gross Income"), ("vacancy_pct", "Vacancy"),
    ("egi", "Effective Gross Income"),
    ("total_expenses", "Total Expenses"), ("expense_ratio", "Expense Ratio"),
    ("noi", "Net Operating Income"), ("cap_rate_applied", "Cap Rate Applied"),
]
_RENT_ROLL_EDIT_FIELDS = [
    ("unit_id", "Unit"), ("suite", "Suite"), ("tenant_name", "Tenant"),
    ("tenant_use", "Use"), ("sf_leased", "Leased SF"),
    ("lease_start", "Lease Start"), ("lease_end", "Lease End"),
    ("monthly_rent", "Monthly Rent"), ("annual_rent", "Annual Rent"),
    ("rent_psf", "Rent/SF"),
    ("reimbursement_structure", "Reimbursement"),
    ("occupancy_status", "Status"),
]
_EXPENSE_EDIT_FIELDS = [
    ("period_year", "Period Year"), ("period_type", "Period Type"),
    ("category", "Category"), ("amount", "Amount"),
    ("amount_per_sf", "Amount/SF"), ("notes", "Notes"),
]
_ARTIFACT_EDIT_FIELDS = [
    ("artifact_kind", "Artifact Kind"), ("title", "Title"),
    ("description", "Description"), ("effective_date", "Effective Date"),
    ("geography", "Geography"), ("property_type", "Property Type"),
]


def _safe_upload_name(name):
    stem = Path(name or "comp-photo").stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return stem[:80] or "comp-photo"


def _save_uploaded_comp_photo(uploaded_file, record_kind, record_id):
    suffix = Path(uploaded_file.name or "").suffix.lower()
    if suffix not in PHOTO_EXTENSIONS:
        raise ValueError("Use a JPG or PNG image.")
    data = uploaded_file.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    folder = LOCAL_MEDIA_DIR / record_kind / str(record_id)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{digest[:16]}_{_safe_upload_name(uploaded_file.name)}{suffix}"
    path = folder / filename
    if not path.exists():
        path.write_bytes(data)
    return path


def _fmt(val, field=None):
    """Format a value for display (mirrors ingest.py's CLI formatter)."""
    if val is None:
        return "—"
    if isinstance(val, float):
        if field and "price" in field and val > 1000:
            return f"${val:,.0f}"
        if field and ("rate" in field or "pct" in field or "ratio" in field):
            return f"{val:.2%}" if val < 1 else f"{val:.1f}%"
        if field and "psf" in field:
            return f"${val:.2f}/SF"
        return f"{val:,.2f}"
    return str(val)


def _run_captured(fn, *args, **kwargs):
    """Call a function, capturing its print() output as text."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(*args, **kwargs)
        ok = True
    except Exception as e:
        buf.write(f"\nERROR: {e}\n")
        ok = False
    return ok, buf.getvalue()


def _manual_text(label, key, placeholder=None):
    value = st.text_input(label, key=key, placeholder=placeholder or "")
    value = value.strip()
    return value or None


def _manual_common_fields(prefix):
    left, middle, right = st.columns(3)
    with left:
        address_street = _manual_text("Address", f"{prefix}_address_street")
        address_city = _manual_text("City", f"{prefix}_address_city")
        address_state = _manual_text(
            "State",
            f"{prefix}_address_state",
            placeholder="AL",
        ) or "AL"
        address_zip = _manual_text("ZIP", f"{prefix}_address_zip")
    with middle:
        property_type = _manual_text("Property Type", f"{prefix}_property_type")
        property_subtype = _manual_text(
            "Property Subtype",
            f"{prefix}_property_subtype",
        )
        submarket = _manual_text("Submarket", f"{prefix}_submarket")
        condition = _manual_text("Condition", f"{prefix}_condition")
    with right:
        gba_sf = _manual_text("GBA (SF)", f"{prefix}_gba_sf")
        nla_sf = _manual_text("NLA (SF)", f"{prefix}_nla_sf")
        site_area_sf = _manual_text("Site Area (SF)", f"{prefix}_site_area_sf")
        year_built = _manual_text("Year Built", f"{prefix}_year_built")
    return {
        "address_street": address_street,
        "address_city": address_city,
        "address_state": address_state,
        "address_zip": address_zip,
        "property_type": property_type,
        "property_subtype": property_subtype,
        "submarket": submarket,
        "condition": condition,
        "gba_sf": gba_sf,
        "nla_sf": nla_sf,
        "site_area_sf": site_area_sf,
        "year_built": year_built,
    }


def _render_manual_entry():
    record_label = st.radio(
        "Comp type",
        ["Sale Comp", "Lease Comp"],
        horizontal=True,
        key="manual_comp_type",
    )
    record_kind = "sale" if record_label == "Sale Comp" else "lease"
    prefix = f"manual_{record_kind}"

    with st.form(f"{prefix}_form", clear_on_submit=False):
        data = _manual_common_fields(prefix)

        if record_kind == "sale":
            st.markdown("##### Sale")
            left, middle, right = st.columns(3)
            with left:
                data["sale_price"] = _manual_text(
                    "Sale Price",
                    f"{prefix}_sale_price",
                    placeholder="$1,000,000",
                )
                data["sale_date"] = _manual_text(
                    "Sale Date",
                    f"{prefix}_sale_date",
                    placeholder="2025-01-15",
                )
                data["price_per_sf"] = _manual_text(
                    "Price/SF",
                    f"{prefix}_price_per_sf",
                )
            with middle:
                data["cap_rate"] = _manual_text(
                    "Cap Rate",
                    f"{prefix}_cap_rate",
                    placeholder="8.5%",
                )
                data["noi"] = _manual_text("NOI", f"{prefix}_noi")
                data["noi_per_sf"] = _manual_text(
                    "NOI/SF",
                    f"{prefix}_noi_per_sf",
                )
            with right:
                data["grantor"] = _manual_text("Grantor", f"{prefix}_grantor")
                data["grantee"] = _manual_text("Grantee", f"{prefix}_grantee")
                data["deed_ref"] = _manual_text("Deed Ref", f"{prefix}_deed_ref")
            data["verification_source"] = _manual_text(
                "Verification Source",
                f"{prefix}_verification_source",
            )
        else:
            st.markdown("##### Lease")
            left, middle, right = st.columns(3)
            with left:
                data["tenant_name"] = _manual_text(
                    "Tenant",
                    f"{prefix}_tenant_name",
                )
                data["tenant_use"] = _manual_text(
                    "Tenant Use",
                    f"{prefix}_tenant_use",
                )
                data["sf_leased"] = _manual_text(
                    "SF Leased",
                    f"{prefix}_sf_leased",
                )
            with middle:
                data["base_rent_psf"] = _manual_text(
                    "Base Rent/SF",
                    f"{prefix}_base_rent_psf",
                    placeholder="$21.50",
                )
                data["base_rent_monthly"] = _manual_text(
                    "Monthly Rent",
                    f"{prefix}_base_rent_monthly",
                )
                data["rent_structure"] = _manual_text(
                    "Rent Structure",
                    f"{prefix}_rent_structure",
                )
            with right:
                data["lease_date"] = _manual_text(
                    "Lease Date",
                    f"{prefix}_lease_date",
                    placeholder="2025-03-01",
                )
                data["lease_expiration"] = _manual_text(
                    "Lease Expiration",
                    f"{prefix}_lease_expiration",
                )
                data["term_years"] = _manual_text(
                    "Term (Years)",
                    f"{prefix}_term_years",
                )
            lower = st.columns(4)
            with lower[0]:
                data["expense_stop_psf"] = _manual_text(
                    "Expense Stop/SF",
                    f"{prefix}_expense_stop_psf",
                )
            with lower[1]:
                data["ti_allowance_psf"] = _manual_text(
                    "TI Allowance/SF",
                    f"{prefix}_ti_allowance_psf",
                )
            with lower[2]:
                data["free_rent_months"] = _manual_text(
                    "Free Rent Months",
                    f"{prefix}_free_rent_months",
                )
            with lower[3]:
                data["escalations"] = _manual_text(
                    "Escalations",
                    f"{prefix}_escalations",
                )
            data["renewal_options"] = _manual_text(
                "Renewal Options",
                f"{prefix}_renewal_options",
            )

        data = {key: value for key, value in data.items() if value not in (None, "")}
        submitted = st.form_submit_button("Add Comp", type="primary")

    if submitted:
        try:
            result = db_module.insert_manual_comparable(record_kind, data)
        except Exception as exc:
            st.error(f"Could not add comp: {exc}")
        else:
            label = "sale" if record_kind == "sale" else "lease"
            if result["created"]:
                st.success(f"Added {label} comp #{result['id']}.")
            else:
                st.info(f"Matching {label} comp already exists as #{result['id']}.")


def _staged_files():
    return sorted(STAGED_DIR.glob("*.json"))


def _confidence_flag(conf, field):
    c = conf.get(field, "?")
    return "" if c == "high" else " ⚠" if c == "medium" else " ✗" if c == "low" else ""


def _render_record(staged_name, kind, idx, record, display_fields, edit_fields):
    """Render one comp/lease-comp card with a Keep checkbox + Edit expander."""
    d = record["data"]
    conf = record.get("confidence", {})
    src = (
        record.get("source")
        or record.get("provenance", {}).get("source_path", "")
    )

    keep_key = f"keep_{staged_name}_{kind}_{idx}"
    with st.container(border=True):
        top = st.columns([5, 1])
        with top[0]:
            addr = d.get("address_street") or "(no address)"
            label = f"**{addr}**"
            if src:
                label += f" — _{Path(src).name}_"
            st.markdown(label)
        with top[1]:
            st.checkbox("Keep", value=True, key=keep_key)

        provenance = record.get("provenance", {})
        if str(provenance.get("extraction_method", "")).startswith("ocr"):
            ocr_conf = provenance.get("ocr_avg_word_confidence")
            rotation = provenance.get("rotation_degrees_applied")
            note = "OCR-derived — verify every field against the source scan below."
            if ocr_conf is not None:
                note += f" (OCR confidence: {ocr_conf:.0f}/100"
                note += f", rotated {rotation}°)" if rotation else ")"
            st.warning(note, icon="⚠️")
            rendered_page_image = provenance.get("rendered_page_image")
            if rendered_page_image:
                image_path = Path(__file__).parent / rendered_page_image
                if image_path.is_file():
                    st.image(str(image_path), caption=rendered_page_image, width=500)
                else:
                    st.caption(f"(source page image not found: {rendered_page_image})")

        cols = st.columns(3)
        shown = 0
        for field, label in display_fields:
            val = d.get(field)
            if val is None:
                continue
            with cols[shown % 3]:
                st.caption(f"{label}{_confidence_flag(conf, field)}")
                st.write(_fmt(val, field))
            shown += 1

        with st.expander("Edit fields"):
            for field, label in edit_fields:
                current = d.get(field)
                default_display = _fmt(current, field) if current is not None else ""
                st.text_input(
                    label, value=default_display,
                    key=f"edit_{staged_name}_{kind}_{idx}_{field}",
                )


def _collect_confirmed(staged_name, kind, records, edit_fields):
    """Rebuild the confirmed record list from current widget state
    (Keep checkbox + any edited fields), coercing edits the same way
    extractor.py coerces raw extracted values (numbers/dates parsed,
    everything else kept as text)."""
    confirmed = []
    for idx, record in enumerate(records):
        keep_key = f"keep_{staged_name}_{kind}_{idx}"
        if not st.session_state.get(keep_key, True):
            continue
        d = dict(record["data"])
        edited = False
        edits = []
        for field, label in edit_fields:
            edit_key = f"edit_{staged_name}_{kind}_{idx}_{field}"
            new_val = st.session_state.get(edit_key)
            original_display = _fmt(d.get(field), field) if d.get(field) is not None else ""
            if new_val is not None and new_val != original_display:
                stripped = new_val.strip()
                corrected = (
                    _extractor_coerce(field, stripped)
                    if stripped
                    else None
                )
                edits.append({
                    "field": field,
                    "before": d.get(field),
                    "after": corrected,
                })
                d[field] = corrected
                edited = True
        new_record = dict(record)
        new_record["data"] = d
        if edited:
            new_record["reviewed"] = True
            new_record["review_edits"] = edits
        confirmed.append(new_record)
    return confirmed


def _render_observation(staged_name, index, record):
    data = record.get("data", {})
    keep_key = f"keep_{staged_name}_observation_{index}"
    with st.container(border=True):
        top = st.columns([5, 1])
        with top[0]:
            st.markdown(f"**{data.get('title') or '(untitled observation)'}**")
            st.caption(
                " · ".join(
                    str(value)
                    for value in (
                        data.get("category"),
                        data.get("geography"),
                        data.get("effective_date"),
                    )
                    if value
                )
            )
        with top[1]:
            st.checkbox("Keep", value=True, key=keep_key)
        with st.expander("Review and edit observation"):
            for field, label in (
                ("category", "Category"),
                ("title", "Title"),
                ("effective_date", "Effective Date"),
                ("geography", "Geography"),
                ("property_type", "Property Type"),
            ):
                st.text_input(
                    label,
                    value=str(data.get(field) or ""),
                    key=f"edit_{staged_name}_observation_{index}_{field}",
                )
            st.text_area(
                "Observation Text",
                value=data.get("text") or "",
                height=240,
                key=f"edit_{staged_name}_observation_{index}_text",
            )


def _collect_observations(staged_name, records):
    retained = []
    fields = (
        "category",
        "title",
        "effective_date",
        "geography",
        "property_type",
        "text",
    )
    for index, record in enumerate(records):
        if not st.session_state.get(
            f"keep_{staged_name}_observation_{index}",
            True,
        ):
            continue
        data = dict(record.get("data", {}))
        edits = []
        for field in fields:
            key = f"edit_{staged_name}_observation_{index}_{field}"
            if key not in st.session_state:
                continue
            value = st.session_state[key].strip() or None
            if value != data.get(field):
                edits.append({
                    "field": field,
                    "before": data.get(field),
                    "after": value,
                })
                data[field] = value
        updated = dict(record)
        updated["data"] = data
        if edits:
            updated["reviewed"] = True
            updated["review_edits"] = edits
        retained.append(updated)
    return retained


def _render_artifact(staged_name, index, record):
    data = record.get("data", {})
    source = record.get("provenance", {}).get("source_path")
    keep_key = f"keep_{staged_name}_artifact_{index}"
    with st.container(border=True):
        top = st.columns([5, 1])
        with top[0]:
            st.markdown(
                f"**{data.get('title') or data.get('artifact_filename')}**"
            )
            metadata = [
                data.get("artifact_kind"),
                data.get("media_type"),
                (
                    f"{data.get('width_px')}×{data.get('height_px')} px"
                    if data.get("width_px") and data.get("height_px")
                    else None
                ),
                Path(source).name if source else None,
            ]
            st.caption(" · ".join(str(value) for value in metadata if value))
        with top[1]:
            st.checkbox("Keep", value=True, key=keep_key)
        with st.expander("Review artifact metadata"):
            for field, label in _ARTIFACT_EDIT_FIELDS:
                st.text_input(
                    label,
                    value=str(data.get(field) or ""),
                    key=f"edit_{staged_name}_artifact_{index}_{field}",
                )
            st.caption(
                f"SHA-256: {data.get('artifact_sha256')} · "
                f"Locator: {record.get('provenance', {}).get('source_locator')}"
            )
            if record.get("alternate_provenance"):
                st.caption(
                    f"{len(record['alternate_provenance'])} duplicate source "
                    "location(s) collapsed."
                )



def _distinct_values(column, table="properties"):
    """Distinct non-empty values for a column, for filter dropdowns."""
    db_path = db_module.DB_PATH
    if not db_path.exists():
        return []
    db_module.init_db(db_path, quiet=True)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM {table} "
            f"WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [r[0] for r in rows]


_SALE_BROWSE_SQL = """
    SELECT c.comp_id, p.address_street AS "Address", p.address_city AS "City",
           p.property_type AS "Type", p.property_subtype AS "Subtype",
           p.gba_sf AS "GBA (SF)", p.year_built AS "Year Built",
           c.sale_price AS "Sale Price", c.sale_date AS "Sale Date",
           c.price_per_sf AS "Price/SF", c.cap_rate AS "Cap Rate", c.noi AS "NOI",
           c.grantor AS "Grantor", c.grantee AS "Grantee",
           c.verification_source AS "Verification", c.submarket AS "Submarket",
           (
               SELECT s.artifact_filename
               FROM source_artifacts s
               WHERE s.comp_id = c.comp_id
                 AND s.review_status = 'confirmed'
                 AND lower(s.artifact_kind) = 'photo'
               ORDER BY s.artifact_id DESC
               LIMIT 1
           ) AS photo_path,
           (
               SELECT COUNT(*)
               FROM source_artifacts s
               WHERE s.comp_id = c.comp_id
                 AND s.review_status = 'confirmed'
                 AND lower(s.artifact_kind) = 'photo'
           ) AS "Photos",
           sd.filename AS "Source"
    FROM comps c
    LEFT JOIN properties p ON c.property_id = p.property_id
    LEFT JOIN source_documents sd ON c.source_doc_id = sd.doc_id
    WHERE c.review_status = 'confirmed'
"""
_LEASE_BROWSE_SQL = """
    SELECT lc.lease_comp_id, p.address_street AS "Address", p.address_city AS "City",
           p.property_type AS "Type", p.property_subtype AS "Subtype",
           p.gba_sf AS "GBA (SF)",
           lc.tenant_name AS "Tenant", lc.tenant_use AS "Use",
           lc.lease_date AS "Lease Date", lc.term_years AS "Term (yrs)",
           lc.sf_leased AS "SF Leased", lc.base_rent_psf AS "Base Rent/SF",
           lc.rent_structure AS "Structure", lc.escalations AS "Escalations",
           (
               SELECT s.artifact_filename
               FROM source_artifacts s
               WHERE s.lease_comp_id = lc.lease_comp_id
                 AND s.review_status = 'confirmed'
                 AND lower(s.artifact_kind) = 'photo'
               ORDER BY s.artifact_id DESC
               LIMIT 1
           ) AS photo_path,
           (
               SELECT COUNT(*)
               FROM source_artifacts s
               WHERE s.lease_comp_id = lc.lease_comp_id
                 AND s.review_status = 'confirmed'
                 AND lower(s.artifact_kind) = 'photo'
           ) AS "Photos",
           lc.submarket AS "Submarket", sd.filename AS "Source"
    FROM lease_comps lc
    LEFT JOIN properties p ON lc.property_id = p.property_id
    LEFT JOIN source_documents sd ON lc.source_doc_id = sd.doc_id
    WHERE lc.review_status = 'confirmed'
"""


def _browse_query(kind, property_types, cities, address_search):
    """Run the filtered browse query for sale or lease comps.
    Returns a pandas DataFrame (possibly empty)."""
    db_path = db_module.DB_PATH
    if not db_path.exists():
        return pd.DataFrame()
    db_module.init_db(db_path, quiet=True)

    sql = _SALE_BROWSE_SQL if kind == "sale" else _LEASE_BROWSE_SQL
    params = []
    if property_types:
        placeholders = ",".join("?" for _ in property_types)
        sql += f" AND p.property_type IN ({placeholders})"
        params.extend(property_types)
    if cities:
        placeholders = ",".join("?" for _ in cities)
        sql += f" AND p.address_city IN ({placeholders})"
        params.extend(cities)
    if address_search:
        sql += " AND p.address_street LIKE ?"
        params.append(f"%{address_search}%")

    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()
    return df


def _browse_display_df(df):
    hidden = {"comp_id", "lease_comp_id", "photo_path"}
    return df.drop(columns=[column for column in hidden if column in df.columns])


def _browse_row_label(row, kind):
    address = row.get("Address") or "(no address)"
    city = row.get("City") or ""
    if kind == "lease" and row.get("Tenant"):
        return f"{address}, {city} - {row.get('Tenant')}".strip(" ,-")
    date = row.get("Sale Date") or row.get("Lease Date") or ""
    return f"{address}, {city} - {date}".strip(" ,-")


def _render_browse_thumbnails(df, kind):
    photo_rows = [
        row
        for _, row in df.iterrows()
        if row.get("photo_path") and Path(str(row.get("photo_path"))).is_file()
    ]
    if not photo_rows:
        return
    st.markdown("##### Attached Photos")
    columns = st.columns(min(4, len(photo_rows)))
    for index, row in enumerate(photo_rows):
        with columns[index % len(columns)]:
            st.image(
                str(row["photo_path"]),
                caption=_browse_row_label(row, kind),
                width=160,
            )


def _render_photo_attachment(kind, df):
    id_column = "comp_id" if kind == "sale" else "lease_comp_id"
    if id_column not in df.columns or df.empty:
        return
    st.markdown("##### Photo Attachment")
    choices = list(df.index)
    selected_index = st.selectbox(
        "Selected comp",
        choices,
        format_func=lambda idx: _browse_row_label(df.loc[idx], kind),
        key=f"attach_target_{kind}",
    )
    record_id = int(df.loc[selected_index, id_column])
    photos = db_module.comp_photo_artifacts(
        record_kind=kind,
        record_id=record_id,
    )
    if photos:
        columns = st.columns(min(3, len(photos)))
        for index, photo in enumerate(photos):
            path = Path(photo.get("artifact_filename") or "")
            with columns[index % len(columns)]:
                if path.is_file():
                    st.image(str(path), caption=photo.get("title"), width=180)
                else:
                    st.caption(f"Missing local file: {path}")
    else:
        st.caption("No attached photos yet.")

    upload_key = f"photo_upload_{kind}_{record_id}"
    title_key = f"photo_title_{kind}_{record_id}"
    uploaded = st.file_uploader(
        "Attach photo",
        type=["jpg", "jpeg", "png"],
        key=upload_key,
    )
    title = st.text_input("Photo title", key=title_key)
    if st.button(
        "Attach to selected comp",
        disabled=uploaded is None,
        key=f"attach_photo_{kind}_{record_id}",
    ):
        try:
            saved_path = _save_uploaded_comp_photo(uploaded, kind, record_id)
            artifact_id = db_module.insert_manual_comp_photo(
                kind,
                record_id,
                saved_path,
                title=title.strip() or None,
                original_filename=uploaded.name,
            )
        except Exception as exc:
            st.error(f"Could not attach photo: {exc}")
        else:
            st.success(f"Attached photo artifact #{artifact_id}.")
            st.rerun()


def render_comp_library():
    st.subheader("Comp Library")
    st.caption("Pull comp data out of old reports and build a searchable database over time.")

    tabs = st.tabs([
        "1. Manual Entry",
        "2. Extract",
        "3. Review",
        "4. Database",
        "5. Browse",
    ])

    with tabs[0]:
        _render_manual_entry()

    # ── Tab 1: Extract ──────────────────────────────────────────────────────
    with tabs[1]:
        st.write(
            "Point at a folder of old assignment folders (each one a completed "
            "report). This scans them and stages whatever comp data it can find "
            "for your review — nothing goes into the database yet."
        )
        root_path = st.text_input(
            "Old reports folder", key="extract_root_path",
            placeholder=r"C:\Users\derek\...\Old Reports",
        )
        if st.button("Scan & Stage", disabled=not root_path):
            path = Path(root_path)
            if not path.exists() or not path.is_dir():
                st.error(f"Folder not found: {root_path}")
            else:
                ok, output = _run_captured(run_extraction, root_path)
                st.session_state['extract_last_output'] = output
                st.rerun()
        if st.session_state.get('extract_last_output'):
            st.code(st.session_state['extract_last_output'], language=None)

        st.caption(f"{len(_staged_files())} assignment(s) currently staged for review.")

    # ── Tab 2: Review ────────────────────────────────────────────────────────
    with tabs[2]:
        staged = _staged_files()
        if not staged:
            st.info("Nothing staged yet. Run a scan in the Extract tab first.")
        else:
            names = [p.name for p in staged]
            choice = st.selectbox("Assignment to review", names, key="review_choice")
            staged_path = STAGED_DIR / choice

            with open(staged_path, encoding="utf-8") as f:
                result = json.load(f)

            folder_name = result.get("folder_name", staged_path.stem)
            meta = result.get("folder_meta", {})
            comps = result.get("comps", [])
            leases = result.get("lease_comps", [])
            narr = result.get("narrative", {}).get("data", {})
            assignment_record = result.get("assignment_record")
            income_record = result.get("income_snapshot")
            rent_roll_entries = result.get("rent_roll_entries", [])
            expense_records = result.get("expense_records", [])
            market_observations = result.get("market_observations", [])
            artifacts = result.get("artifacts", [])

            st.markdown(f"**{folder_name}**")
            meta_bits = [v for v in (meta.get("property_type"), meta.get("city")) if v]
            if meta_bits:
                st.caption(" · ".join(meta_bits))
            st.caption(f"{len(comps)} sale comp(s)  ·  {len(leases)} lease comp(s)")

            if assignment_record:
                st.markdown("##### Assignment Conclusion")
                _render_record(
                    choice,
                    "assignment",
                    0,
                    assignment_record,
                    _ASSIGNMENT_EDIT_FIELDS,
                    _ASSIGNMENT_EDIT_FIELDS,
                )

            if income_record:
                st.markdown("##### Income Snapshot")
                _render_record(
                    choice,
                    "income",
                    0,
                    income_record,
                    _INCOME_EDIT_FIELDS,
                    _INCOME_EDIT_FIELDS,
                )

            if rent_roll_entries:
                st.markdown("##### Rent Roll")
                for index, record in enumerate(rent_roll_entries):
                    _render_record(
                        choice,
                        "rent_roll",
                        index,
                        record,
                        _RENT_ROLL_EDIT_FIELDS,
                        _RENT_ROLL_EDIT_FIELDS,
                    )

            if expense_records:
                st.markdown("##### Operating Expenses")
                for index, record in enumerate(expense_records):
                    _render_record(
                        choice,
                        "expense",
                        index,
                        record,
                        _EXPENSE_EDIT_FIELDS,
                        _EXPENSE_EDIT_FIELDS,
                    )

            if market_observations:
                st.markdown("##### Market Observations")
                for index, record in enumerate(market_observations):
                    _render_observation(choice, index, record)

            if artifacts:
                st.markdown("##### Source Artifacts")
                for index, record in enumerate(artifacts):
                    _render_artifact(choice, index, record)

            if comps:
                st.markdown("##### Sale Comps")
                for i, comp in enumerate(comps):
                    _render_record(choice, "sale", i, comp, _SALE_DISPLAY_FIELDS, _SALE_EDIT_FIELDS)

            if leases:
                st.markdown("##### Lease Comps")
                for i, lc in enumerate(leases):
                    _render_record(choice, "lease", i, lc, _LEASE_DISPLAY_FIELDS, _LEASE_EDIT_FIELDS)

            if (
                not comps
                and not leases
                and not assignment_record
                and not income_record
                and not rent_roll_entries
                and not expense_records
                and not market_observations
                and not artifacts
            ):
                st.info("Nothing extracted from this assignment.")

            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("✓ Confirm & Save", key=f"confirm_{choice}", type="primary"):
                    confirmed_comps = _collect_confirmed(choice, "sale", comps, _SALE_EDIT_FIELDS)
                    confirmed_leases = _collect_confirmed(choice, "lease", leases, _LEASE_EDIT_FIELDS)
                    result["comps"] = confirmed_comps
                    result["lease_comps"] = confirmed_leases
                    if assignment_record:
                        retained = _collect_confirmed(
                            choice,
                            "assignment",
                            [assignment_record],
                            _ASSIGNMENT_EDIT_FIELDS,
                        )
                        result["assignment_record"] = retained[0] if retained else None
                    if income_record:
                        retained = _collect_confirmed(
                            choice,
                            "income",
                            [income_record],
                            _INCOME_EDIT_FIELDS,
                        )
                        result["income_snapshot"] = retained[0] if retained else None
                    result["rent_roll_entries"] = _collect_confirmed(
                        choice,
                        "rent_roll",
                        rent_roll_entries,
                        _RENT_ROLL_EDIT_FIELDS,
                    )
                    result["expense_records"] = _collect_confirmed(
                        choice,
                        "expense",
                        expense_records,
                        _EXPENSE_EDIT_FIELDS,
                    )
                    result["market_observations"] = _collect_observations(
                        choice,
                        market_observations,
                    )
                    result["artifacts"] = _collect_confirmed(
                        choice,
                        "artifact",
                        artifacts,
                        _ARTIFACT_EDIT_FIELDS,
                    )
                    result = confirm_extraction_result(
                        result,
                        reviewer="streamlit",
                    )
                    confirmed_path = CONFIRMED_DIR / staged_path.name
                    with open(confirmed_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, default=str)
                    staged_path.rename(staged_path.with_suffix(".done"))
                    st.session_state.pop("review_choice", None)
                    st.session_state['review_flash'] = (
                        f"Saved {len(confirmed_comps)} sale comp(s) and "
                        f"{len(confirmed_leases)} lease comp(s) from {folder_name} — ready to commit."
                    )
                    st.rerun()
            with btn_cols[1]:
                if st.button("Skip this assignment", key=f"skip_{choice}"):
                    staged_path.rename(staged_path.with_suffix(".skipped"))
                    st.session_state.pop("review_choice", None)
                    st.session_state['review_flash'] = f"Skipped {folder_name}."
                    st.rerun()

        if st.session_state.get('review_flash'):
            st.success(st.session_state.pop('review_flash'))

    # ── Tab 3: Database ─────────────────────────────────────────────────────
    with tabs[3]:
        confirmed_files = list(CONFIRMED_DIR.glob("*.json"))
        st.caption(f"{len(confirmed_files)} confirmed assignment(s) ready to commit.")
        if st.button("Commit to Database", disabled=not confirmed_files):
            ok, output = _run_captured(commit_confirmed)
            st.session_state['commit_last_output'] = output
            st.rerun()
        if st.session_state.get('commit_last_output'):
            st.code(st.session_state['commit_last_output'], language=None)

        st.divider()
        db_path = db_module.DB_PATH
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            counts = {}
            for table in [
                "properties",
                "comps",
                "lease_comps",
                "assignments",
                "income_snapshots",
                "rent_roll_entries",
                "operating_expenses",
                "market_observations",
                "source_artifacts",
            ]:
                try:
                    counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.OperationalError:
                    counts[table] = 0
            conn.close()
            stat_cols = st.columns(5)
            stat_cols[0].metric("Properties", counts.get("properties", 0))
            stat_cols[1].metric("Sale Comps", counts.get("comps", 0))
            stat_cols[2].metric("Lease Comps", counts.get("lease_comps", 0))
            stat_cols[3].metric("Assignments", counts.get("assignments", 0))
            stat_cols[4].metric(
                "Income Snapshots",
                counts.get("income_snapshots", 0),
            )
            harvest_cols = st.columns(4)
            harvest_cols[0].metric(
                "Rent-Roll Rows",
                counts.get("rent_roll_entries", 0),
            )
            harvest_cols[1].metric(
                "Expense Lines",
                counts.get("operating_expenses", 0),
            )
            harvest_cols[2].metric(
                "Observations",
                counts.get("market_observations", 0),
            )
            harvest_cols[3].metric(
                "Artifacts",
                counts.get("source_artifacts", 0),
            )
        else:
            st.caption("No database yet — commit your first confirmed assignment to create one.")

    # ── Tab 4: Browse ───────────────────────────────────────────────────────
    with tabs[4]:
        db_path = db_module.DB_PATH
        if not db_path.exists():
            st.caption("No database yet — commit your first confirmed assignment to create one.")
        else:
            kind_label = st.radio(
                "Comp type", ["Sale Comps", "Lease Comps"],
                horizontal=True, key="browse_kind",
            )
            kind = "sale" if kind_label == "Sale Comps" else "lease"

            filter_cols = st.columns(3)
            with filter_cols[0]:
                types = st.multiselect(
                    "Property type", _distinct_values("property_type"), key="browse_types"
                )
            with filter_cols[1]:
                cities = st.multiselect(
                    "City", _distinct_values("address_city"), key="browse_cities"
                )
            with filter_cols[2]:
                addr_search = st.text_input("Address contains", key="browse_addr")

            df = _browse_query(kind, types, cities, addr_search)
            st.caption(f"{len(df)} {kind_label.lower()} found")

            if len(df):
                _render_browse_thumbnails(df, kind)
                display_df = _browse_display_df(df)
                st.dataframe(display_df, width='stretch', hide_index=True)
                csv = display_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download as CSV", data=csv,
                    file_name=f"{kind}_comps.csv", mime="text/csv",
                    key="browse_download",
                )
                _render_photo_attachment(kind, df)
            else:
                st.info("No comps match these filters yet.")
