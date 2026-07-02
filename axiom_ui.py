"""
axiom_ui.py — Axiom Command Center
====================================
A local button-driven UI on top of axiom.py. Every button here calls the
exact same functions the CLI uses (cmd_new, cmd_engage, cmd_deliver,
cmd_dilmore, check_delivery_readiness) -- nothing is reimplemented, so the
UI and the CLI can never disagree about what a command does.

Run with:
    streamlit run axiom_ui.py

(Or double-click start_axiom_ui.bat, which installs streamlit if needed
and launches this for you.)
"""

import io
import os
import json
import contextlib
import subprocess
import platform
from pathlib import Path

import streamlit as st

import axiom
from axiom import (
    ASSIGNMENTS_DIR, BASE_DIR,
    cmd_new, cmd_engage, cmd_deliver, cmd_dilmore,
    _load_state, _find_json, check_delivery_readiness,
)
from comp_review import render_comp_library

st.set_page_config(page_title="Axiom Command Center", layout="wide")

_STAGE_COLORS = {
    'new':       '#EDEDED',
    'engaged':   '#FCEFC7',
    'delivered': '#DCEFDD',
}
_STAGE_TEXT = {
    'new':       '#555555',
    'engaged':   '#8A6D00',
    'delivered': '#1E6B2E',
}


def _run_captured(fn, args):
    """Call a cmd_* function, capturing its print() output as text."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(args)
        ok = True
    except Exception as e:
        buf.write(f"\nERROR: {e}\n")
        ok = False
    return ok, buf.getvalue()


def _load_variables(adir):
    json_path = _find_json(adir)
    if not json_path or not json_path.exists():
        return {}
    try:
        with open(json_path, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _get(variables, key, default='—'):
    val = variables.get(key)
    if val in (None, '', 'N/A'):
        return default
    return val


def _assignment_dirs():
    return sorted(
        (d for d in ASSIGNMENTS_DIR.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )


def _open_local(path: Path):
    """Open a file or folder in its default application (Explorer/Excel/Word)."""
    try:
        if platform.system() == 'Windows':
            os.startfile(str(path))  # noqa: only exists on Windows
        elif platform.system() == 'Darwin':
            subprocess.run(['open', str(path)], check=False)
        else:
            subprocess.run(['xdg-open', str(path)], check=False)
        return True, ''
    except Exception as e:
        return False, str(e)


# ─── Header ─────────────────────────────────────────────────────────────────

st.title("Axiom Command Center")
st.caption(f"{len(_assignment_dirs())} assignment(s) — {BASE_DIR}")

with st.expander("➕ New Assignment", expanded=False):
    with st.form("new_assignment_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_file_no = st.text_input("File number", placeholder="2026-002")
        with col2:
            new_client = st.text_input("Client name", placeholder="Client Name LLC")
        submitted = st.form_submit_button("Create Assignment")
        if submitted:
            if not new_file_no or not new_client:
                st.error("Both file number and client name are required.")
            else:
                ok, output = _run_captured(cmd_new, [new_file_no, new_client])
                st.session_state['last_output'] = output
                st.session_state['last_output_title'] = f"New: {new_file_no}"
                st.rerun()

if st.session_state.get('last_output'):
    with st.expander(f"Last run: {st.session_state.get('last_output_title', '')}", expanded=True):
        st.code(st.session_state['last_output'], language=None)
        if st.button("Dismiss"):
            st.session_state['last_output'] = ''
            st.rerun()

st.divider()

# ─── Assignment cards ───────────────────────────────────────────────────────

dirs = _assignment_dirs()

if not dirs:
    st.info("No assignments yet. Use **New Assignment** above to create one.")

for adir in dirs:
    state = _load_state(adir)
    parts = adir.name.split('_', 1)
    fno = state.get('file_no') or (parts[0] if parts else adir.name)
    client = state.get('client') or (parts[1].replace('_', ' ') if len(parts) > 1 else '')
    stage = state.get('stage', 'new')
    variables = _load_variables(adir)

    with st.container(border=True):
        top_l, top_r = st.columns([4, 1])
        with top_l:
            st.subheader(f"{client}")
            st.caption(fno)
        with top_r:
            st.markdown(
                f"<div style='background:{_STAGE_COLORS.get(stage, '#EDEDED')};"
                f"color:{_STAGE_TEXT.get(stage, '#555555')};padding:4px 10px;"
                f"border-radius:12px;text-align:center;font-weight:bold;"
                f"font-size:12px;text-transform:uppercase;'>{stage}</div>",
                unsafe_allow_html=True,
            )

        address = _get(variables, 'PROPERTY_ADDRESS', '')
        city = _get(variables, 'PROPERTY_CITY', '')
        prop_line = ', '.join(p for p in [address, city] if p and p != '—')
        if prop_line:
            st.write(prop_line)

        value_conclusion = _get(variables, 'VALUE_CONCLUSION', None)
        if value_conclusion:
            st.metric("Value Conclusion", value_conclusion)

        # Delivery readiness — same check the dashboard uses
        check_key = f"check_{adir.name}"
        if check_key not in st.session_state:
            st.session_state[check_key] = check_delivery_readiness(adir)
        check = st.session_state[check_key]

        if check['checked']:
            if not check['missing']:
                st.success("Ready to deliver — no missing fields")
            else:
                with st.expander(f"⚠ {len(check['missing'])} field(s) missing before delivery"):
                    st.write(", ".join(check['missing']))
        else:
            st.caption(f"Delivery check unavailable — {check['reason']}")

        # Do-the-work row: jump straight into the workbook or the outputs
        # folder, no hunting through File Explorer.
        work_cols = st.columns(2)
        wb_path = adir / 'workbook.xlsx'
        with work_cols[0]:
            if st.button("📊 Open Workbook", key=f"openwb_{adir.name}", disabled=not wb_path.exists()):
                ok, err = _open_local(wb_path)
                if not ok:
                    st.error(f"Couldn't open it automatically ({err}). Path: {wb_path}")
        with work_cols[1]:
            outputs_dir = adir / 'outputs'
            if st.button("📁 Open Outputs Folder", key=f"openout_{adir.name}", disabled=not outputs_dir.exists()):
                ok, err = _open_local(outputs_dir)
                if not ok:
                    st.error(f"Couldn't open it automatically ({err}). Path: {outputs_dir}")

        btn_cols = st.columns(4)
        with btn_cols[0]:
            if st.button("Engage", key=f"engage_{adir.name}"):
                ok, output = _run_captured(cmd_engage, [fno])
                st.session_state['last_output'] = output
                st.session_state['last_output_title'] = f"Engage: {fno}"
                st.rerun()
        with btn_cols[1]:
            if st.button("Deliver", key=f"deliver_{adir.name}"):
                ok, output = _run_captured(cmd_deliver, [fno])
                st.session_state['last_output'] = output
                st.session_state['last_output_title'] = f"Deliver: {fno}"
                st.rerun()
        with btn_cols[2]:
            if st.button("Run Dilmore", key=f"dilmore_{adir.name}"):
                ok, output = _run_captured(cmd_dilmore, [fno])
                st.session_state['last_output'] = output
                st.session_state['last_output_title'] = f"Dilmore: {fno}"
                st.rerun()
        with btn_cols[3]:
            if st.button("Recheck", key=f"recheck_{adir.name}"):
                st.session_state[check_key] = check_delivery_readiness(adir)
                st.rerun()

        created = state.get('created') or '—'
        engaged = state.get('engaged') or '—'
        delivered = state.get('delivered') or '—'
        st.caption(f"Created {created}  ·  Engaged {engaged}  ·  Delivered {delivered}")

        outputs_dir = adir / 'outputs'
        if outputs_dir.exists():
            docs = sorted(outputs_dir.glob('*.docx'))
            if docs:
                st.caption("Outputs: " + ", ".join(d.name for d in docs))

st.divider()
render_comp_library()
