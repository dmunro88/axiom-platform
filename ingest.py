"""
ingest.py — Axiom Commercial Appraisal
Orchestrates the Phase 5.5 extraction pipeline:

  Scan folders → Extract → Stage JSON → Review → Commit to database

Usage (standalone)
------------------
  python ingest.py scan   /path/to/projects/root
  python ingest.py run    /path/to/projects/root
  python ingest.py review
  python ingest.py commit

Or called from axiom.py via:
  python axiom.py extract /path/to/projects/root
  python axiom.py review-staged
"""

import sys
import json
import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
STAGED_DIR = BASE_DIR / "ingest" / "staged"
STAGED_DIR.mkdir(parents=True, exist_ok=True)

from extractor import scan_projects_root, scan_assignment_folder, extract_assignment
from db        import (init_db, get_conn, already_ingested,
                       insert_source_document, insert_property,
                       insert_comp, insert_lease_comp,
                       insert_assignment, insert_income_snapshot)


# ─── Staging ──────────────────────────────────────────────────────────────────

def stage_assignment(extraction_result):
    """
    Write one extraction result to ingest/staged/ as a JSON file.
    File is named by folder name + timestamp to avoid collisions.
    Returns the path to the staged file.
    """
    folder_name = extraction_result["folder_name"]
    safe_name   = "".join(c if c.isalnum() or c in "-_ " else "_"
                          for c in folder_name).strip()
    ts          = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename    = f"{safe_name}__{ts}.json"
    path        = STAGED_DIR / filename

    with open(path, "w", encoding="utf-8") as f:
        json.dump(extraction_result, f, indent=2, default=str)

    return path


def run_extraction(root_path):
    """
    Scan root_path, extract all assignments, write staged JSON files.
    Skips folders that have already been staged (checks staged dir).
    Returns list of staged file paths.
    """
    root        = Path(root_path)
    assignments = scan_projects_root(root)

    print(f"\n  Found {len(assignments)} assignment folder(s) under {root.name}")
    print()

    staged_paths = []
    for i, scan in enumerate(assignments, 1):
        name = scan["name"]
        meta = scan["folder_meta"]
        type_hint = meta.get("property_type", "")
        city_hint = meta.get("city", "")
        label = f"{name[:50]}"

        print(f"  [{i:02d}/{len(assignments):02d}] {label}")

        # Show what we found
        counts = {
            "reports":     len(scan["reports"]),
            "exhibits":    len(scan["exhibits"]),
            "sale comps":  len(scan["sale_comp_docs"]),
            "cap rate xl": len(scan["cap_rate_xls"]),
            "rental xl":   len(scan["rental_comp_xls"]),
        }
        found = [f"{v} {k}" for k, v in counts.items() if v > 0]
        if found:
            print(f"         → {', '.join(found)}")
        else:
            print(f"         → no extractable files found, skipping")
            continue

        # Extract
        try:
            result = extract_assignment(scan)
        except Exception as e:
            print(f"         ✗ Extraction error: {e}")
            continue

        n_comps  = len(result["comps"])
        n_leases = len(result["lease_comps"])
        print(f"         → {n_comps} sale comp(s), {n_leases} lease comp(s) extracted")

        if result["warnings"]:
            for w in result["warnings"][:3]:  # show first 3 warnings only
                print(f"         ⚠  {w.strip()}")
            if len(result["warnings"]) > 3:
                print(f"         ⚠  ... {len(result['warnings']) - 3} more warning(s)")

        if n_comps == 0 and n_leases == 0 and not result["narrative"].get("data"):
            print(f"         → nothing useful extracted, skipping")
            continue

        staged = stage_assignment(result)
        staged_paths.append(staged)
        print(f"         ✓ Staged: {staged.name}")
        print()

    print(f"\n  {len(staged_paths)} staged file(s) ready in {STAGED_DIR}")
    print(f"  Run: python axiom.py review-staged\n")
    return staged_paths


# ─── Review ───────────────────────────────────────────────────────────────────

def _fmt(val, field=None):
    """Format a value for display."""
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


def _print_comp(comp, idx, total):
    d = comp["data"]
    c = comp.get("confidence", {})

    print(f"\n    ── Sale Comp {idx}/{total} ──────────────────────────────")
    fields = [
        ("address_street",      "Address"),
        ("address_city",        "City"),
        ("sale_price",          "Sale Price"),
        ("sale_date",           "Sale Date"),
        ("gba_sf",              "GBA (SF)"),
        ("price_per_sf",        "Price/SF"),
        ("cap_rate",            "Cap Rate"),
        ("noi",                 "NOI"),
        ("year_built",          "Year Built"),
        ("property_type",       "Property Type"),
        ("grantor",             "Grantor"),
        ("grantee",             "Grantee"),
        ("deed_ref",            "Deed Ref"),
        ("verification_source", "Verification"),
        ("submarket",           "Submarket"),
    ]
    for field, label in fields:
        val = d.get(field)
        if val is None:
            continue
        conf = c.get(field, "?")
        flag = "" if conf == "high" else " ⚠ " if conf == "medium" else " ✗ "
        print(f"      {label:<20} {_fmt(val, field)}{flag}")

    src = comp.get("source", "")
    if src:
        print(f"      {'Source':<20} {Path(src).name}")


def _print_lease_comp(lc, idx, total):
    d = lc["data"]
    c = lc.get("confidence", {})

    print(f"\n    ── Lease Comp {idx}/{total} ─────────────────────────────")
    fields = [
        ("address_street",   "Address"),
        ("address_city",     "City"),
        ("tenant_name",      "Tenant"),
        ("tenant_use",       "Use"),
        ("lease_date",       "Lease Date"),
        ("term_years",       "Term (yrs)"),
        ("sf_leased",        "SF Leased"),
        ("base_rent_psf",    "Base Rent/SF"),
        ("rent_structure",   "Structure"),
        ("escalations",      "Escalations"),
        ("renewal_options",  "Options"),
        ("ti_allowance_psf", "TI Allow/SF"),
        ("free_rent_months", "Free Rent"),
        ("submarket",        "Submarket"),
    ]
    for field, label in fields:
        val = d.get(field)
        if val is None:
            continue
        conf = c.get(field, "?")
        flag = "" if conf == "high" else " ⚠ " if conf == "medium" else " ✗ "
        print(f"      {label:<20} {_fmt(val, field)}{flag}")

    src = lc.get("source", "")
    if src:
        print(f"      {'Source':<20} {Path(src).name}")


def _input_yn(prompt, default="y"):
    """Prompt for y/n with a default."""
    suffix = " [Y/n]" if default == "y" else " [y/N]"
    resp   = input(f"    {prompt}{suffix}: ").strip().lower()
    if not resp:
        return default == "y"
    return resp.startswith("y")


def _edit_field(data, field, label):
    """Prompt Derek to correct a field value. Empty = keep current."""
    current = data.get(field)
    resp = input(f"    {label} [{_fmt(current, field)}]: ").strip()
    if resp:
        data[field] = resp
    return data


def review_staged(interactive=True):
    """
    Walk ingest/staged/, present each record for Derek's review,
    and write confirmed results to ingest/confirmed/.
    """
    staged_files = sorted(STAGED_DIR.glob("*.json"))
    if not staged_files:
        print("\n  No staged files found.")
        print(f"  Run: python axiom.py extract <path/to/projects/root>\n")
        return []

    confirmed_dir = STAGED_DIR.parent / "confirmed"
    confirmed_dir.mkdir(exist_ok=True)

    print(f"\n  {len(staged_files)} staged file(s) to review\n")
    confirmed_paths = []

    for staged_path in staged_files:
        with open(staged_path, encoding="utf-8") as f:
            result = json.load(f)

        folder_name = result.get("folder_name", staged_path.stem)
        meta        = result.get("folder_meta", {})
        comps       = result.get("comps", [])
        leases      = result.get("lease_comps", [])
        narr        = result.get("narrative", {})

        print("  " + "═" * 60)
        print(f"  ASSIGNMENT: {folder_name}")
        if meta.get("property_type"):
            print(f"  Type: {meta['property_type']}  |  City: {meta.get('city', '—')}")
        print(f"  {len(comps)} sale comp(s)  |  {len(leases)} lease comp(s)")

        # Narrative summary
        nd = narr.get("data", {})
        if nd:
            print(f"\n  Report data found:")
            for k, v in nd.items():
                if v:
                    print(f"    {k:<25} {v}")

        if not comps and not leases:
            print("\n  Nothing to commit for this assignment.")
            if _input_yn("Skip and move to next?"):
                staged_path.rename(staged_path.with_suffix(".skipped"))
                continue

        # ── Review sale comps ──────────────────────────────────────────────
        confirmed_comps = []
        for i, comp in enumerate(comps, 1):
            _print_comp(comp, i, len(comps))
            print()

            if not interactive:
                confirmed_comps.append(comp)
                continue

            action = input("    (k)eep / (e)dit / (s)kip / (q)uit review? [k]: ").strip().lower()
            if not action or action == "k":
                confirmed_comps.append(comp)
            elif action == "e":
                d = comp["data"]
                print("    Enter corrections (press Enter to keep current value):")
                for field in ["address_street", "address_city", "address_county",
                               "sale_price", "sale_date", "gba_sf", "cap_rate"]:
                    _edit_field(d, field, field)
                comp["data"]      = d
                comp["reviewed"]  = True
                confirmed_comps.append(comp)
            elif action == "q":
                print("\n  Review paused. Run again to continue.\n")
                return confirmed_paths
            # 's' = skip this comp

        # ── Review lease comps ──────────────────────────────────────────────
        confirmed_leases = []
        for i, lc in enumerate(leases, 1):
            _print_lease_comp(lc, i, len(leases))
            print()

            if not interactive:
                confirmed_leases.append(lc)
                continue

            action = input("    (k)eep / (e)dit / (s)kip / (q)uit review? [k]: ").strip().lower()
            if not action or action == "k":
                confirmed_leases.append(lc)
            elif action == "e":
                d = lc["data"]
                print("    Enter corrections (press Enter to keep current value):")
                for field in ["address_street", "address_city", "sf_leased",
                               "base_rent_psf", "rent_structure", "lease_date"]:
                    _edit_field(d, field, field)
                lc["data"]     = d
                lc["reviewed"] = True
                confirmed_leases.append(lc)
            elif action == "q":
                print("\n  Review paused. Run again to continue.\n")
                return confirmed_paths

        # ── Save confirmed ─────────────────────────────────────────────────
        result["comps"]       = confirmed_comps
        result["lease_comps"] = confirmed_leases
        result["reviewed"]    = True

        confirmed_path = confirmed_dir / staged_path.name
        with open(confirmed_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        confirmed_paths.append(confirmed_path)
        staged_path.rename(staged_path.with_suffix(".done"))

        print(f"\n  ✓ {len(confirmed_comps)} sale comp(s), "
              f"{len(confirmed_leases)} lease comp(s) confirmed\n")

    return confirmed_paths


# ─── Commit ───────────────────────────────────────────────────────────────────

def _upsert_property(data, conn):
    """
    Find an existing property by address, or insert a new one.
    Returns property_id.
    """
    street = data.get("address_street", "").strip().lower() if data.get("address_street") else ""
    city   = data.get("address_city",   "").strip().lower() if data.get("address_city")   else ""

    if street:
        row = conn.execute(
            "SELECT property_id FROM properties WHERE lower(address_street) = ? AND lower(address_city) = ?",
            (street, city)
        ).fetchone()
        if row:
            return row["property_id"]

    return insert_property(data, conn)


def commit_confirmed():
    """
    Read all confirmed JSON files and write records to axiom.db.
    Marks each file as .committed when done.
    """
    confirmed_dir  = STAGED_DIR.parent / "confirmed"
    confirmed_files = list(confirmed_dir.glob("*.json"))

    if not confirmed_files:
        print("\n  No confirmed files to commit.")
        print(f"  Run: python axiom.py review-staged first.\n")
        return

    init_db()
    conn = get_conn()

    total_comps  = 0
    total_leases = 0
    total_asgn   = 0

    print(f"\n  Committing {len(confirmed_files)} confirmed file(s) to axiom.db ...\n")

    for conf_path in confirmed_files:
        with open(conf_path, encoding="utf-8") as f:
            result = json.load(f)

        folder_name = result.get("folder_name", conf_path.stem)
        print(f"  {folder_name}")

        # ── Register source documents ──────────────────────────────────────
        sources = result.get("sources", [])
        doc_ids = {}
        for src in sources:
            existing = already_ingested(src, conn)
            if existing:
                doc_ids[src] = existing
            else:
                ext = Path(src).suffix.lower()
                doc_type = ("comp_workbook" if ext == ".xlsx"
                            else "report" if "report" in Path(src).stem.lower()
                            else "exhibits" if "exhibit" in Path(src).stem.lower()
                            else "document")
                doc_ids[src] = insert_source_document(
                    src, doc_type, conn=conn
                )

        primary_doc_id = list(doc_ids.values())[0] if doc_ids else None

        # ── Narrative / assignment ─────────────────────────────────────────
        narr = result.get("narrative", {}).get("data", {})
        meta = result.get("folder_meta", {})

        # Property from narrative + folder meta
        prop_data = {
            "address_street":  narr.get("address_street"),
            "address_city":    narr.get("address_city") or meta.get("city"),
            "address_state":   "AL",
            "property_type":   narr.get("property_type") or meta.get("property_type"),
        }
        subject_property_id = _upsert_property(prop_data, conn) if any(prop_data.values()) else None

        # Assignment row
        if subject_property_id and primary_doc_id:
            asgn_data = {
                "file_no":         narr.get("file_no") or meta.get("file_no"),
                "client":          narr.get("client"),
                "report_date":     narr.get("report_date"),
                "effective_date":  narr.get("effective_date"),
                "reconciled_value": narr.get("reconciled_value"),
                "sca_value":       narr.get("sca_value"),
                "ia_value":        narr.get("ia_value"),
                "ca_value":        narr.get("ca_value"),
            }
            insert_assignment(asgn_data, subject_property_id, primary_doc_id, conn)
            total_asgn += 1

        # Income snapshot
        income = result.get("income_data", {})
        if income and subject_property_id and primary_doc_id:
            income["market_cap_rate_low"]  = narr.get("market_cap_rate_low")
            income["market_cap_rate_high"] = narr.get("market_cap_rate_high")
            insert_income_snapshot(income, subject_property_id, primary_doc_id, conn)

        # ── Sale comps ────────────────────────────────────────────────────
        for comp in result.get("comps", []):
            d    = comp["data"]
            conf = comp.get("confidence", {})
            src  = comp.get("source", sources[0] if sources else "")
            doc_id = doc_ids.get(src, primary_doc_id)

            prop_id = _upsert_property(d, conn)
            insert_comp(d, prop_id, doc_id, conf, conn)
            total_comps += 1

        # ── Lease comps ───────────────────────────────────────────────────
        for lc in result.get("lease_comps", []):
            d    = lc["data"]
            conf = lc.get("confidence", {})
            src  = lc.get("source", sources[0] if sources else "")
            doc_id = doc_ids.get(src, primary_doc_id)

            prop_id = _upsert_property(d, conn)
            insert_lease_comp(d, prop_id, doc_id, conf, conn)
            total_leases += 1

        conn.commit()
        conf_path.rename(conf_path.with_suffix(".committed"))
        print(f"         ✓ committed")

    conn.close()

    print(f"\n  Summary:")
    print(f"    {total_asgn}  assignment(s) recorded")
    print(f"    {total_comps}  sale comp(s) added to database")
    print(f"    {total_leases}  lease comp(s) added to database")
    print(f"\n  Run: python axiom.py comp-search   to query the database\n")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "scan" and len(sys.argv) >= 3:
        scans = scan_projects_root(sys.argv[2])
        for s in scans:
            meta = s["folder_meta"]
            print(f"  {s['name'][:55]:<55} "
                  f"reports:{len(s['reports'])} "
                  f"exhibits:{len(s['exhibits'])} "
                  f"cap_rate_xl:{len(s['cap_rate_xls'])} "
                  f"rental_xl:{len(s['rental_comp_xls'])}")

    elif cmd == "run" and len(sys.argv) >= 3:
        run_extraction(sys.argv[2])

    elif cmd == "review":
        review_staged()

    elif cmd == "commit":
        commit_confirmed()

    else:
        print(__doc__)
