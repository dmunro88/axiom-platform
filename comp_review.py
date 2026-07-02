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
import json
import contextlib
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from ingest import STAGED_DIR, run_extraction, commit_confirmed
from extractor import _coerce as _extractor_coerce
import db as db_module

CONFIRMED_DIR = STAGED_DIR.parent / "confirmed"
CONFIRMED_DIR.mkdir(exist_ok=True)

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


def _staged_files():
    return sorted(STAGED_DIR.glob("*.json"))


def _confidence_flag(conf, field):
    c = conf.get(field, "?")
    return "" if c == "high" else " ⚠" if c == "medium" else " ✗" if c == "low" else ""


def _render_record(staged_name, kind, idx, record, display_fields, edit_fields):
    """Render one comp/lease-comp card with a Keep checkbox + Edit expander."""
    d = record["data"]
    conf = record.get("confidence", {})
    src = record.get("source", "")

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
        for field, label in edit_fields:
            edit_key = f"edit_{staged_name}_{kind}_{idx}_{field}"
            new_val = st.session_state.get(edit_key)
            original_display = _fmt(d.get(field), field) if d.get(field) is not None else ""
            if new_val is not None and new_val.strip() and new_val != original_display:
                d[field] = _extractor_coerce(field, new_val.strip())
                edited = True
        new_record = dict(record)
        new_record["data"] = d
        if edited:
            new_record["reviewed"] = True
        confirmed.append(new_record)
    return confirmed



def _distinct_values(column, table="properties"):
    """Distinct non-empty values for a column, for filter dropdowns."""
    db_path = db_module.DB_PATH
    if not db_path.exists():
        return []
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
           sd.filename AS "Source"
    FROM comps c
    LEFT JOIN properties p ON c.property_id = p.property_id
    LEFT JOIN source_documents sd ON c.source_doc_id = sd.doc_id
    WHERE 1=1
"""
_LEASE_BROWSE_SQL = """
    SELECT lc.lease_comp_id, p.address_street AS "Address", p.address_city AS "City",
           p.property_type AS "Type", p.property_subtype AS "Subtype",
           p.gba_sf AS "GBA (SF)",
           lc.tenant_name AS "Tenant", lc.tenant_use AS "Use",
           lc.lease_date AS "Lease Date", lc.term_years AS "Term (yrs)",
           lc.sf_leased AS "SF Leased", lc.base_rent_psf AS "Base Rent/SF",
           lc.rent_structure AS "Structure", lc.escalations AS "Escalations",
           lc.submarket AS "Submarket", sd.filename AS "Source"
    FROM lease_comps lc
    LEFT JOIN properties p ON lc.property_id = p.property_id
    LEFT JOIN source_documents sd ON lc.source_doc_id = sd.doc_id
    WHERE 1=1
"""


def _browse_query(kind, property_types, cities, address_search):
    """Run the filtered browse query for sale or lease comps.
    Returns a pandas DataFrame (possibly empty)."""
    db_path = db_module.DB_PATH
    if not db_path.exists():
        return pd.DataFrame()

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
    return df.drop(columns=[c for c in ("comp_id", "lease_comp_id") if c in df.columns])


def render_comp_library():
    st.subheader("📚 Comp Library")
    st.caption("Pull comp data out of old reports and build a searchable database over time.")

    tabs = st.tabs(["1. Extract", "2. Review", "3. Database", "4. Browse"])

    # ── Tab 1: Extract ──────────────────────────────────────────────────────
    with tabs[0]:
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
    with tabs[1]:
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

            st.markdown(f"**{folder_name}**")
            meta_bits = [v for v in (meta.get("property_type"), meta.get("city")) if v]
            if meta_bits:
                st.caption(" · ".join(meta_bits))
            st.caption(f"{len(comps)} sale comp(s)  ·  {len(leases)} lease comp(s)")

            if narr:
                with st.expander("Report-level data found (not editable here)"):
                    for k, v in narr.items():
                        if v:
                            st.write(f"**{k}**: {v}")

            if comps:
                st.markdown("##### Sale Comps")
                for i, comp in enumerate(comps):
                    _render_record(choice, "sale", i, comp, _SALE_DISPLAY_FIELDS, _SALE_EDIT_FIELDS)

            if leases:
                st.markdown("##### Lease Comps")
                for i, lc in enumerate(leases):
                    _render_record(choice, "lease", i, lc, _LEASE_DISPLAY_FIELDS, _LEASE_EDIT_FIELDS)

            if not comps and not leases:
                st.info("Nothing extracted from this assignment.")

            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("✓ Confirm & Save", key=f"confirm_{choice}", type="primary"):
                    confirmed_comps = _collect_confirmed(choice, "sale", comps, _SALE_EDIT_FIELDS)
                    confirmed_leases = _collect_confirmed(choice, "lease", leases, _LEASE_EDIT_FIELDS)
                    result["comps"] = confirmed_comps
                    result["lease_comps"] = confirmed_leases
                    result["reviewed"] = True
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
    with tabs[2]:
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
            for table in ["properties", "comps", "lease_comps", "assignments"]:
                try:
                    counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.OperationalError:
                    counts[table] = 0
            conn.close()
            stat_cols = st.columns(4)
            stat_cols[0].metric("Properties", counts.get("properties", 0))
            stat_cols[1].metric("Sale Comps", counts.get("comps", 0))
            stat_cols[2].metric("Lease Comps", counts.get("lease_comps", 0))
            stat_cols[3].metric("Assignments", counts.get("assignments", 0))
        else:
            st.caption("No database yet — commit your first confirmed assignment to create one.")

    # ── Tab 4: Browse ───────────────────────────────────────────────────────
    with tabs[3]:
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
                st.dataframe(df, width='stretch', hide_index=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download as CSV", data=csv,
                    file_name=f"{kind}_comps.csv", mime="text/csv",
                    key="browse_download",
                )
            else:
                st.info("No comps match these filters yet.")
