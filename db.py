"""
db.py — Axiom Commercial Appraisal
SQLite database for the comp library and market intelligence layer.

Tables
------
  source_documents   — every file that has been ingested; prevents duplicates
  properties         — physical property facts (shared by comps + assignments)
  comps              — sale transactions (Sales Comparison Approach support)
  lease_comps        — lease transactions (Income Approach / market rent support)
  assignments        — old appraisal reports (subject + value conclusions)
  income_snapshots   — cap rates + income figures per property per period

Usage
-----
  from db import init_db, get_conn
  init_db()                  # creates axiom.db if it doesn't exist
  conn = get_conn()          # sqlite3 connection with Row factory
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "axiom.db"

SCHEMA = """
-- ── Source documents ────────────────────────────────────────────────────────
-- Every file ingested. Prevents re-processing the same file twice.
CREATE TABLE IF NOT EXISTS source_documents (
    doc_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename            TEXT    NOT NULL,
    filepath            TEXT,
    doc_type            TEXT,           -- report / comp_workbook / lease / rent_roll / os
    report_date         TEXT,
    effective_date      TEXT,
    processed_at        TEXT    DEFAULT (datetime('now')),
    extraction_notes    TEXT,           -- unmapped headers, warnings, etc.
    reviewed            INTEGER DEFAULT 0,  -- 1 once Derek has confirmed
    notes               TEXT
);

-- ── Properties ──────────────────────────────────────────────────────────────
-- Physical property facts. One row per building / parcel.
-- Shared by comps, lease_comps, and assignments (via FK).
CREATE TABLE IF NOT EXISTS properties (
    property_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    address_street      TEXT,
    address_city        TEXT,
    address_county      TEXT,
    address_state       TEXT    DEFAULT 'AL',
    address_zip         TEXT,
    property_type       TEXT,           -- Office / Retail / Industrial / Multifamily / Land
    property_subtype    TEXT,           -- Multi-Tenant / Single-Tenant / Strip / etc.
    gba_sf              REAL,
    nla_sf              REAL,
    site_area_sf        REAL,
    year_built          INTEGER,
    stories             INTEGER,
    construction_type   TEXT,
    condition           TEXT,
    zoning              TEXT,
    flood_zone          TEXT,
    parcel_id           TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Sale comps ───────────────────────────────────────────────────────────────
-- Closed sale transactions. Primary data for the Sales Comparison Approach.
CREATE TABLE IF NOT EXISTS comps (
    comp_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    sale_price          REAL,
    sale_date           TEXT,           -- ISO: YYYY-MM-DD
    price_per_sf        REAL,
    cap_rate            REAL,           -- as decimal: 0.085 = 8.5%
    noi                 REAL,
    noi_per_sf          REAL,
    grantor             TEXT,
    grantee             TEXT,
    deed_ref            TEXT,
    verification_source TEXT,
    submarket           TEXT,
    confidence          TEXT,           -- JSON: {"sale_price": "high", "cap_rate": "medium", ...}
    reviewed            INTEGER DEFAULT 0,
    notes               TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Lease comps ──────────────────────────────────────────────────────────────
-- Closed lease transactions. Supports market rent conclusions (Income Approach).
CREATE TABLE IF NOT EXISTS lease_comps (
    lease_comp_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    tenant_name         TEXT,
    tenant_use          TEXT,
    lease_date          TEXT,           -- ISO: YYYY-MM-DD (commencement)
    lease_expiration    TEXT,           -- ISO: YYYY-MM-DD (expiration/end date)
    term_years          REAL,
    sf_leased           REAL,
    base_rent_psf       REAL,           -- annual, per SF
    base_rent_monthly   REAL,
    rent_structure      TEXT,           -- NNN / Modified Gross / Gross / Full Service
    expense_stop_psf    REAL,
    ti_allowance_psf    REAL,
    free_rent_months    REAL,
    escalations         TEXT,           -- "3% annual", "CPI", "5% every 3 years", etc.
    renewal_options     TEXT,           -- "two 5-year options at fair market rent"
    submarket           TEXT,
    confidence          TEXT,           -- JSON per-field confidence
    reviewed            INTEGER DEFAULT 0,
    notes               TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Assignments ───────────────────────────────────────────────────────────────
-- Old appraisal reports. Tracks subject property + value conclusions.
-- Ties together the source document, the subject property, and the value opinion.
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id         INTEGER REFERENCES properties(property_id),  -- subject property
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    file_no             TEXT,
    client              TEXT,
    report_date         TEXT,
    effective_date      TEXT,
    approaches          TEXT,           -- CSV: "SCA,IA" or "SCA,IA,CA"
    sca_value           REAL,
    ia_value            REAL,
    ca_value            REAL,
    reconciled_value    REAL,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Income snapshots ─────────────────────────────────────────────────────────
-- Cap rates and income figures per property per period.
-- Accumulates over time into the market cap rate tracker.
CREATE TABLE IF NOT EXISTS income_snapshots (
    snapshot_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    period_year         INTEGER,
    period_type         TEXT,           -- actual / proforma / stabilized
    pgi                 REAL,
    vacancy_pct         REAL,           -- as decimal: 0.05 = 5%
    egi                 REAL,
    total_expenses      REAL,
    expense_ratio       REAL,           -- as decimal
    noi                 REAL,
    cap_rate_applied    REAL,           -- cap rate used to reach the IA value
    market_cap_rate_low  REAL,
    market_cap_rate_high REAL,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_properties_city    ON properties(address_city);
CREATE INDEX IF NOT EXISTS idx_properties_county  ON properties(address_county);
CREATE INDEX IF NOT EXISTS idx_properties_type    ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_comps_date         ON comps(sale_date);
CREATE INDEX IF NOT EXISTS idx_comps_type         ON comps(property_id);
CREATE INDEX IF NOT EXISTS idx_lease_comps_date   ON lease_comps(lease_date);
CREATE INDEX IF NOT EXISTS idx_source_filepath    ON source_documents(filepath);
"""


def init_db(db_path=None):
    """
    Create the database and all tables if they don't exist.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    Returns the path to the database file.
    """
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"  Database ready: {path}")
    return path


def get_conn(db_path=None):
    """
    Return a sqlite3 connection with Row factory enabled
    (rows accessible as dicts: row['field_name']).
    """
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def already_ingested(filepath, conn=None):
    """
    Check if a file has already been processed (by filepath).
    Returns the doc_id if found, None otherwise.
    """
    close_after = conn is None
    if conn is None:
        conn = get_conn()
    row = conn.execute(
        "SELECT doc_id FROM source_documents WHERE filepath = ?",
        (str(filepath),)
    ).fetchone()
    if close_after:
        conn.close()
    return row["doc_id"] if row else None


def insert_source_document(filepath, doc_type, report_date=None,
                           effective_date=None, extraction_notes=None, conn=None):
    """
    Insert a new source_documents row and return its doc_id.
    """
    close_after = conn is None
    if conn is None:
        conn = get_conn()
    cur = conn.execute(
        """INSERT INTO source_documents
           (filename, filepath, doc_type, report_date, effective_date, extraction_notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (Path(filepath).name, str(filepath), doc_type,
         report_date, effective_date, extraction_notes)
    )
    doc_id = cur.lastrowid
    if close_after:
        conn.commit()
        conn.close()
    return doc_id


def insert_property(data, conn):
    """Insert a properties row and return property_id."""
    fields = ["address_street", "address_city", "address_county", "address_state",
              "address_zip", "property_type", "property_subtype", "gba_sf", "nla_sf",
              "site_area_sf", "year_built", "stories", "construction_type",
              "condition", "zoning", "flood_zone", "parcel_id"]
    row = {f: data.get(f) for f in fields}
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO properties ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_comp(data, property_id, source_doc_id, confidence, conn):
    """Insert a comps row and return comp_id."""
    import json
    fields = ["sale_price", "sale_date", "price_per_sf", "cap_rate", "noi",
              "noi_per_sf", "grantor", "grantee", "deed_ref",
              "verification_source", "submarket"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["confidence"] = json.dumps(confidence)
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO comps ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_lease_comp(data, property_id, source_doc_id, confidence, conn):
    """Insert a lease_comps row and return lease_comp_id."""
    import json
    fields = ["tenant_name", "tenant_use", "lease_date", "lease_expiration",
              "term_years", "sf_leased",
              "base_rent_psf", "base_rent_monthly", "rent_structure", "expense_stop_psf",
              "ti_allowance_psf", "free_rent_months", "escalations",
              "renewal_options", "submarket"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["confidence"] = json.dumps(confidence)
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO lease_comps ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_assignment(data, property_id, source_doc_id, conn):
    """Insert an assignments row and return assignment_id."""
    fields = ["file_no", "client", "report_date", "effective_date",
              "approaches", "sca_value", "ia_value", "ca_value", "reconciled_value"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO assignments ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_income_snapshot(data, property_id, source_doc_id, conn):
    """Insert an income_snapshots row and return snapshot_id."""
    fields = ["period_year", "period_type", "pgi", "vacancy_pct", "egi",
              "total_expenses", "expense_ratio", "noi", "cap_rate_applied",
              "market_cap_rate_low", "market_cap_rate_high"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO income_snapshots ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


if __name__ == "__main__":
    init_db()
