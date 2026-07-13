"""Axiom local Streamlit workbench.

The UI is a thin layer over the same command functions used by axiom.py.
"""

import contextlib
import io
import json
import os
import platform
import sqlite3
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from axiom import (
    ASSIGNMENTS_DIR,
    BASE_DIR,
    cmd_contract,
    cmd_dashboard,
    cmd_deliver,
    cmd_dilmore,
    cmd_engage,
    cmd_new,
    cmd_validate,
    _find_json,
    _load_state,
    check_delivery_readiness,
)
from comp_review import CONFIRMED_DIR, STAGED_DIR, render_comp_library
from db import (
    DB_PATH,
    init_db,
    search_lease_comps,
    search_market_observations,
    search_operating_expenses,
    search_rent_roll_entries,
    search_sale_comps,
    search_source_artifacts,
)


st.set_page_config(page_title="Axiom", layout="wide")

STAGE_COLORS = {
    "new": "#767676",
    "engaged": "#9A6700",
    "delivered": "#1F7A3A",
}
APP_TABLES = [
    "source_documents",
    "properties",
    "comps",
    "lease_comps",
    "assignments",
    "income_snapshots",
    "rent_roll_entries",
    "operating_expenses",
    "market_observations",
    "source_artifacts",
]


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 0.65rem 0.75rem;
    }
    .axiom-stage {
        display: inline-block;
        padding: 0.16rem 0.48rem;
        border-radius: 999px;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .axiom-subtle { color: #6b7280; font-size: 0.86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _run_captured(fn, args=None):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = fn(args or [])
        return result is not False, buf.getvalue()
    except Exception as exc:
        buf.write(f"\nERROR: {exc}\n")
        return False, buf.getvalue()


def _show_output():
    output = st.session_state.get("last_output")
    if not output:
        return
    title = st.session_state.get("last_output_title") or "Last run"
    with st.expander(title, expanded=True):
        st.code(output, language=None)
        if st.button("Dismiss", key="dismiss_last_output"):
            st.session_state["last_output"] = ""
            st.rerun()


def _record_output(title, output):
    st.session_state["last_output_title"] = title
    st.session_state["last_output"] = output


def _open_local(path):
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # noqa: only available on Windows
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _assignment_dirs():
    if not ASSIGNMENTS_DIR.exists():
        return []
    return sorted(
        [path for path in ASSIGNMENTS_DIR.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _assignment_label(adir):
    state = _load_state(adir)
    file_no = state.get("file_no") or adir.name.split("_", 1)[0]
    client = state.get("client")
    if not client and "_" in adir.name:
        client = adir.name.split("_", 1)[1].replace("_", " ")
    return f"{file_no} - {client or adir.name}"


def _assignment_file_no(adir):
    state = _load_state(adir)
    return state.get("file_no") or adir.name.split("_", 1)[0]


def _load_variables(adir):
    json_path = _find_json(adir)
    if not json_path or not json_path.exists():
        return {}
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _value(data, key, default="-"):
    value = data.get(key)
    return default if value in (None, "", "N/A") else value


def _db_counts():
    if not DB_PATH.exists():
        return {table: 0 for table in APP_TABLES}
    init_db(DB_PATH, quiet=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in APP_TABLES
        }
    finally:
        conn.close()


def _stage_badge(stage):
    color = STAGE_COLORS.get(stage, "#767676")
    return (
        f"<span class='axiom-stage' style='background:{color}'>{stage}</span>"
    )


def _assignment_frame():
    dirs = _assignment_dirs()
    if not dirs:
        return None
    labels = {_assignment_label(adir): adir for adir in dirs}
    choice = st.selectbox("Assignment", list(labels), key="selected_assignment")
    return labels[choice]


def _new_assignment_form():
    with st.expander("New Assignment", expanded=False):
        with st.form("new_assignment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            file_no = col1.text_input("File number")
            client = col2.text_input("Client")
            submitted = st.form_submit_button("Create")
        if submitted:
            if not file_no.strip() or not client.strip():
                st.error("File number and client are required.")
            else:
                ok, output = _run_captured(cmd_new, [file_no.strip(), client.strip()])
                _record_output(f"New assignment: {file_no.strip()}", output)
                st.rerun()


def _assignment_table(dirs):
    rows = []
    for adir in dirs:
        state = _load_state(adir)
        variables = _load_variables(adir)
        readiness = check_delivery_readiness(adir)
        rows.append({
            "File": state.get("file_no") or adir.name.split("_", 1)[0],
            "Client": state.get("client") or adir.name,
            "Stage": state.get("stage", "new"),
            "Property": ", ".join(
                part
                for part in (
                    _value(variables, "PROPERTY_ADDRESS", ""),
                    _value(variables, "PROPERTY_CITY", ""),
                )
                if part
            ),
            "Missing": len(readiness.get("missing", []))
            if readiness.get("checked")
            else None,
            "Modified": pd.to_datetime(adir.stat().st_mtime, unit="s").date(),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_dashboard():
    dirs = _assignment_dirs()
    counts = _db_counts()
    top = st.columns(5)
    top[0].metric("Assignments", len(dirs))
    top[1].metric("Sale Comps", counts["comps"])
    top[2].metric("Lease Comps", counts["lease_comps"])
    top[3].metric("Staged", len(list(STAGED_DIR.glob("*.json"))))
    top[4].metric("Confirmed", len(list(CONFIRMED_DIR.glob("*.json"))))

    _new_assignment_form()
    _show_output()

    if not dirs:
        st.info("No assignments yet.")
        return
    _assignment_table(dirs)


def _render_assignment_header(adir):
    state = _load_state(adir)
    variables = _load_variables(adir)
    file_no = _assignment_file_no(adir)
    client = state.get("client") or adir.name
    stage = state.get("stage", "new")

    left, right = st.columns([4, 1])
    with left:
        st.subheader(client)
        st.markdown(
            f"<span class='axiom-subtle'>{file_no}</span>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(_stage_badge(stage), unsafe_allow_html=True)

    fields = st.columns(4)
    fields[0].metric("Property", _value(variables, "PROPERTY_ADDRESS"))
    fields[1].metric("City", _value(variables, "PROPERTY_CITY"))
    fields[2].metric("Type", _value(variables, "PROPERTY_TYPE"))
    fields[3].metric("Value", _value(variables, "VALUE_CONCLUSION"))
    return file_no


def _render_assignment_actions(adir, file_no):
    st.markdown("#### Files")
    file_cols = st.columns(3)
    workbook = adir / "workbook.xlsx"
    outputs = adir / "outputs"
    folder_actions = (
        ("Workbook", workbook),
        ("Outputs", outputs),
        ("Folder", adir),
    )
    for column, (label, path) in zip(file_cols, folder_actions):
        if column.button(label, disabled=not path.exists(), key=f"open_{label}_{adir.name}"):
            ok, err = _open_local(path)
            if not ok:
                st.error(f"Could not open {path}: {err}")

    st.markdown("#### Commands")
    command_cols = st.columns(5)
    commands = (
        ("Engage", cmd_engage, [file_no]),
        ("Validate", cmd_validate, [file_no]),
        ("Deliver", cmd_deliver, [file_no]),
        ("Draft", cmd_deliver, [file_no, "--draft"]),
        ("Dilmore", cmd_dilmore, [file_no]),
    )
    for column, (label, fn, args) in zip(command_cols, commands):
        if column.button(label, key=f"{label}_{adir.name}"):
            ok, output = _run_captured(fn, args)
            _record_output(f"{label}: {file_no}", output)
            st.rerun()


def _render_readiness(adir):
    result = check_delivery_readiness(adir)
    st.markdown("#### Delivery Readiness")
    if not result.get("checked"):
        st.warning(result.get("reason") or "Validation unavailable.")
        return
    summary = st.columns(4)
    summary[0].metric("Errors", len(result.get("errors", [])))
    summary[1].metric("Missing Fields", len(result.get("missing", [])))
    summary[2].metric("Blocks", len(result.get("blocks", [])))
    summary[3].metric("Warnings", len(result.get("warnings", [])))
    if result.get("errors"):
        with st.expander("Errors", expanded=True):
            st.write(result["errors"])
    if result.get("missing"):
        with st.expander("Missing fields", expanded=False):
            st.write(result["missing"])
    if result.get("blocks"):
        with st.expander("Unresolved blocks", expanded=False):
            st.write(result["blocks"])
    if not any(result.get(key) for key in ("errors", "missing", "blocks")):
        st.success("Ready")


def render_workflow():
    dirs = _assignment_dirs()
    if not dirs:
        _new_assignment_form()
        st.info("No assignments yet.")
        return
    adir = _assignment_frame()
    if adir is None:
        return
    file_no = _render_assignment_header(adir)
    _render_assignment_actions(adir, file_no)
    _show_output()
    _render_readiness(adir)

    outputs = sorted((adir / "outputs").glob("*.docx")) if (adir / "outputs").exists() else []
    if outputs:
        st.markdown("#### Outputs")
        st.dataframe(
            pd.DataFrame({
                "Document": [path.name for path in outputs],
                "Modified": [
                    pd.to_datetime(path.stat().st_mtime, unit="s")
                    for path in outputs
                ],
            }),
            width="stretch",
            hide_index=True,
        )


def _show_dataframe(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No records found.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


def render_search():
    search_tabs = st.tabs(["Comps", "Financials", "Observations", "Artifacts"])

    with search_tabs[0]:
        kind = st.radio("Type", ["Sale", "Lease"], horizontal=True, key="search_comp_kind")
        filters = st.columns(3)
        city = filters[0].text_input("City", key="search_comp_city")
        property_type = filters[1].text_input("Property type", key="search_comp_type")
        address = filters[2].text_input("Address contains", key="search_comp_address")
        if kind == "Sale":
            rows = search_sale_comps(
                city=city or None,
                property_type=property_type or None,
                address_contains=address or None,
            )
        else:
            rows = search_lease_comps(
                city=city or None,
                property_type=property_type or None,
                address_contains=address or None,
            )
        _show_dataframe(rows)

    with search_tabs[1]:
        kind = st.radio(
            "Record type",
            ["Rent Roll", "Expenses"],
            horizontal=True,
            key="search_fin_kind",
        )
        if kind == "Rent Roll":
            tenant = st.text_input("Tenant contains")
            as_of = st.text_input("As of date")
            rows = search_rent_roll_entries(
                tenant_contains=tenant or None,
                as_of_date=as_of or None,
            )
        else:
            col1, col2 = st.columns(2)
            year_text = col1.text_input("Year")
            category = col2.text_input("Category contains")
            try:
                year = int(year_text) if year_text else None
            except ValueError:
                year = None
                st.error("Year must be numeric.")
            rows = search_operating_expenses(
                period_year=year,
                category_contains=category or None,
            )
        _show_dataframe(rows)

    with search_tabs[2]:
        cols = st.columns(4)
        category = cols[0].text_input("Category", key="obs_cat")
        geography = cols[1].text_input("Geography", key="obs_geo")
        property_type = cols[2].text_input("Property type", key="obs_type")
        text = cols[3].text_input("Text contains", key="obs_text")
        rows = search_market_observations(
            category=category or None,
            geography=geography or None,
            property_type=property_type or None,
            text_contains=text or None,
        )
        _show_dataframe(rows)

    with search_tabs[3]:
        cols = st.columns(4)
        kind = cols[0].text_input("Kind", key="artifact_kind")
        title = cols[1].text_input("Title contains", key="artifact_title")
        geography = cols[2].text_input("Geography", key="artifact_geo")
        property_type = cols[3].text_input("Property type", key="artifact_type")
        rows = search_source_artifacts(
            artifact_kind=kind or None,
            title_contains=title or None,
            geography=geography or None,
            property_type=property_type or None,
        )
        _show_dataframe(rows)


def render_system():
    counts = _db_counts()
    st.subheader("System")
    st.markdown(f"`{BASE_DIR}`")
    metrics = st.columns(5)
    metrics[0].metric("DB Rows", sum(counts.values()))
    metrics[1].metric("Staged", len(list(STAGED_DIR.glob("*.json"))))
    metrics[2].metric("Confirmed", len(list(CONFIRMED_DIR.glob("*.json"))))
    metrics[3].metric("Assignments", len(_assignment_dirs()))
    metrics[4].metric("DB Size", DB_PATH.stat().st_size if DB_PATH.exists() else 0)

    st.markdown("#### Database")
    st.dataframe(
        pd.DataFrame({"Table": list(counts), "Rows": list(counts.values())}),
        width="stretch",
        hide_index=True,
    )

    command_cols = st.columns(3)
    if command_cols[0].button("Contract"):
        ok, output = _run_captured(cmd_contract, [])
        _record_output("Contract", output)
        st.rerun()
    if command_cols[1].button("Build Dashboard"):
        ok, output = _run_captured(cmd_dashboard, [])
        _record_output("Dashboard", output)
        st.rerun()
    if command_cols[2].button("Open Dashboard", disabled=not (BASE_DIR / "dashboard.html").exists()):
        ok, err = _open_local(BASE_DIR / "dashboard.html")
        if not ok:
            st.error(f"Could not open dashboard.html: {err}")
    _show_output()


def main():
    st.title("Axiom")
    page = st.sidebar.radio(
        "View",
        ["Dashboard", "Assignment Workflow", "Comp Library", "Search", "System"],
    )
    st.sidebar.markdown(f"`{BASE_DIR}`")

    if page == "Dashboard":
        render_dashboard()
    elif page == "Assignment Workflow":
        render_workflow()
    elif page == "Comp Library":
        render_comp_library()
    elif page == "Search":
        render_search()
    elif page == "System":
        render_system()


if __name__ == "__main__":
    main()
