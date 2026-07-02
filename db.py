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

import json
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
    content_sha256      TEXT,
    file_size           INTEGER,
    modified_ns         INTEGER,
    contract_version    TEXT,
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
    identity_key        TEXT,
    confidence          TEXT,           -- JSON: {"sale_price": "high", "cap_rate": "medium", ...}
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
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
    identity_key        TEXT,
    confidence          TEXT,           -- JSON per-field confidence
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
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
    identity_key        TEXT,
    confidence          TEXT,
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
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
    identity_key        TEXT,
    confidence          TEXT,
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
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


MIGRATION_COLUMNS = {
    "source_documents": {
        "content_sha256": "TEXT",
        "file_size": "INTEGER",
        "modified_ns": "INTEGER",
        "contract_version": "TEXT",
    },
    "comps": {
        "identity_key": "TEXT",
        "review_status": "TEXT DEFAULT 'unreviewed'",
        "reviewed_at": "TEXT",
        "source_record_json": "TEXT",
    },
    "lease_comps": {
        "identity_key": "TEXT",
        "review_status": "TEXT DEFAULT 'unreviewed'",
        "reviewed_at": "TEXT",
        "source_record_json": "TEXT",
    },
    "assignments": {
        "identity_key": "TEXT",
        "confidence": "TEXT",
        "review_status": "TEXT DEFAULT 'unreviewed'",
        "reviewed_at": "TEXT",
        "source_record_json": "TEXT",
    },
    "income_snapshots": {
        "identity_key": "TEXT",
        "confidence": "TEXT",
        "review_status": "TEXT DEFAULT 'unreviewed'",
        "reviewed_at": "TEXT",
        "source_record_json": "TEXT",
    },
}

IDENTITY_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_source_content_sha256
    ON source_documents(content_sha256)
    WHERE content_sha256 IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_comps_identity_key
    ON comps(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lease_comps_identity_key
    ON lease_comps(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_assignments_identity_key
    ON assignments(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_income_snapshots_identity_key
    ON income_snapshots(identity_key)
    WHERE identity_key IS NOT NULL;
"""


def _apply_migrations(conn):
    for table, columns in MIGRATION_COLUMNS.items():
        existing = {
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )
    conn.execute(
        """
        UPDATE comps
        SET review_status = CASE
            WHEN reviewed = 1 THEN 'confirmed'
            ELSE 'unreviewed'
        END
        WHERE review_status IS NULL OR review_status = ''
           OR (review_status = 'unreviewed' AND reviewed = 1)
        """
    )
    conn.execute(
        """
        UPDATE lease_comps
        SET review_status = CASE
            WHEN reviewed = 1 THEN 'confirmed'
            ELSE 'unreviewed'
        END
        WHERE review_status IS NULL OR review_status = ''
           OR (review_status = 'unreviewed' AND reviewed = 1)
        """
    )
    conn.executescript(IDENTITY_INDEXES)


def init_db(db_path=None, quiet=False):
    """
    Create the database and all tables if they don't exist.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    Returns the path to the database file.
    """
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    _apply_migrations(conn)
    conn.commit()
    conn.close()
    if not quiet:
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


def already_ingested(filepath=None, conn=None, content_sha256=None):
    """
    Check if a file has already been processed (by filepath).
    Returns the doc_id if found, None otherwise.
    """
    close_after = conn is None
    if conn is None:
        conn = get_conn()
    row = None
    if content_sha256:
        row = conn.execute(
            "SELECT doc_id FROM source_documents WHERE content_sha256 = ?",
            (content_sha256,),
        ).fetchone()
    if row is None and filepath is not None:
        row = conn.execute(
            "SELECT doc_id FROM source_documents WHERE filepath = ?",
            (str(filepath),),
        ).fetchone()
    if close_after:
        conn.close()
    return row["doc_id"] if row else None


def insert_source_document(
    filepath,
    doc_type,
    report_date=None,
    effective_date=None,
    extraction_notes=None,
    conn=None,
    content_sha256=None,
    file_size=None,
    modified_ns=None,
    contract_version=None,
):
    """
    Insert a new source_documents row and return its doc_id.
    """
    close_after = conn is None
    if conn is None:
        conn = get_conn()
    cur = conn.execute(
        """INSERT INTO source_documents
           (filename, filepath, doc_type, report_date, effective_date,
            extraction_notes, content_sha256, file_size, modified_ns,
            contract_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (Path(filepath).name, str(filepath), doc_type,
         report_date, effective_date, extraction_notes, content_sha256,
         file_size, modified_ns, contract_version)
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
    row["address_state"] = row["address_state"] or "AL"
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO properties ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_comp(
    data,
    property_id,
    source_doc_id,
    confidence,
    conn,
    identity_key=None,
    review=None,
    source_record=None,
):
    """Insert a comps row and return comp_id."""
    fields = ["sale_price", "sale_date", "price_per_sf", "cap_rate", "noi",
              "noi_per_sf", "grantor", "grantee", "deed_ref",
              "verification_source", "submarket"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["confidence"] = json.dumps(confidence)
    row["identity_key"] = identity_key
    review = review or {}
    row["review_status"] = review.get("status", "unreviewed")
    row["reviewed_at"] = review.get("reviewed_at")
    row["reviewed"] = 1 if row["review_status"] == "confirmed" else 0
    row["source_record_json"] = (
        json.dumps(source_record, default=str) if source_record else None
    )
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO comps ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_lease_comp(
    data,
    property_id,
    source_doc_id,
    confidence,
    conn,
    identity_key=None,
    review=None,
    source_record=None,
):
    """Insert a lease_comps row and return lease_comp_id."""
    fields = ["tenant_name", "tenant_use", "lease_date", "lease_expiration",
              "term_years", "sf_leased",
              "base_rent_psf", "base_rent_monthly", "rent_structure", "expense_stop_psf",
              "ti_allowance_psf", "free_rent_months", "escalations",
              "renewal_options", "submarket"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["confidence"] = json.dumps(confidence)
    row["identity_key"] = identity_key
    review = review or {}
    row["review_status"] = review.get("status", "unreviewed")
    row["reviewed_at"] = review.get("reviewed_at")
    row["reviewed"] = 1 if row["review_status"] == "confirmed" else 0
    row["source_record_json"] = (
        json.dumps(source_record, default=str) if source_record else None
    )
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO lease_comps ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_assignment(
    data,
    property_id,
    source_doc_id,
    conn,
    *,
    identity_key=None,
    confidence=None,
    review=None,
    source_record=None,
):
    """Insert an assignments row and return assignment_id."""
    fields = ["file_no", "client", "report_date", "effective_date",
              "approaches", "sca_value", "ia_value", "ca_value", "reconciled_value"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["identity_key"] = identity_key
    row["confidence"] = json.dumps(confidence or {}, sort_keys=True)
    row["review_status"] = (review or {}).get("status", "unreviewed")
    row["reviewed_at"] = (review or {}).get("reviewed_at")
    row["source_record_json"] = json.dumps(
        source_record or {},
        sort_keys=True,
        default=str,
    )
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO assignments ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def insert_income_snapshot(
    data,
    property_id,
    source_doc_id,
    conn,
    *,
    identity_key=None,
    confidence=None,
    review=None,
    source_record=None,
):
    """Insert an income_snapshots row and return snapshot_id."""
    fields = ["period_year", "period_type", "pgi", "vacancy_pct", "egi",
              "total_expenses", "expense_ratio", "noi", "cap_rate_applied",
              "market_cap_rate_low", "market_cap_rate_high"]
    row = {f: data.get(f) for f in fields}
    row["property_id"] = property_id
    row["source_doc_id"] = source_doc_id
    row["identity_key"] = identity_key
    row["confidence"] = json.dumps(confidence or {}, sort_keys=True)
    row["review_status"] = (review or {}).get("status", "unreviewed")
    row["reviewed_at"] = (review or {}).get("reviewed_at")
    row["source_record_json"] = json.dumps(
        source_record or {},
        sort_keys=True,
        default=str,
    )
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    cur = conn.execute(
        f"INSERT INTO income_snapshots ({cols}) VALUES ({placeholders})",
        list(row.values())
    )
    return cur.lastrowid


def harvest_id_by_identity(record_kind, identity_key, conn):
    table, id_column = (
        ("assignments", "assignment_id")
        if record_kind == "assignment"
        else ("income_snapshots", "snapshot_id")
    )
    row = conn.execute(
        f"SELECT {id_column} FROM {table} WHERE identity_key = ?",
        (identity_key,),
    ).fetchone()
    return row[id_column] if row else None


def search_assignments(
    db_path=None,
    *,
    file_no=None,
    client_contains=None,
    effective_date_from=None,
    effective_date_to=None,
    include_unreviewed=False,
):
    """Return reusable historical assignment conclusions."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT a.*, p.address_street, p.address_city, p.address_state,
               p.property_type, sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM assignments a
        LEFT JOIN properties p ON p.property_id = a.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = a.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND a.review_status = 'confirmed'"
    if file_no:
        sql += " AND lower(a.file_no) = lower(?)"
        params.append(file_no)
    if client_contains:
        sql += " AND lower(a.client) LIKE lower(?)"
        params.append(f"%{client_contains}%")
    if effective_date_from:
        sql += " AND a.effective_date >= ?"
        params.append(effective_date_from)
    if effective_date_to:
        sql += " AND a.effective_date <= ?"
        params.append(effective_date_to)
    sql += " ORDER BY a.effective_date DESC, a.assignment_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def search_income_snapshots(
    db_path=None,
    *,
    period_year=None,
    period_type=None,
    include_unreviewed=False,
):
    """Return reusable historical income snapshots."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT i.*, p.address_street, p.address_city, p.address_state,
               p.property_type, sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM income_snapshots i
        LEFT JOIN properties p ON p.property_id = i.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = i.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND i.review_status = 'confirmed'"
    if period_year is not None:
        sql += " AND i.period_year = ?"
        params.append(period_year)
    if period_type:
        sql += " AND lower(i.period_type) = lower(?)"
        params.append(period_type)
    sql += " ORDER BY i.period_year DESC, i.snapshot_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def comparable_id_by_identity(record_kind, identity_key, conn):
    table = "comps" if record_kind == "sale" else "lease_comps"
    id_column = "comp_id" if record_kind == "sale" else "lease_comp_id"
    row = conn.execute(
        f"SELECT {id_column} FROM {table} WHERE identity_key = ?",
        (identity_key,),
    ).fetchone()
    return row[id_column] if row else None


def search_sale_comps(
    db_path=None,
    *,
    city=None,
    property_type=None,
    address_contains=None,
    sale_date_from=None,
    sale_date_to=None,
    include_unreviewed=False,
):
    """Return canonical sale-comp rows for application and workbook reuse."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(db_path)
    sql = """
        SELECT c.comp_id, c.identity_key, c.review_status,
               c.sale_price, c.sale_date, c.price_per_sf, c.cap_rate,
               c.noi, c.noi_per_sf, c.grantor, c.grantee, c.deed_ref,
               c.verification_source, c.submarket, c.confidence,
               p.address_street, p.address_city, p.address_county,
               p.address_state, p.address_zip, p.property_type,
               p.property_subtype, p.gba_sf, p.nla_sf, p.site_area_sf,
               p.year_built, p.stories, p.construction_type, p.condition,
               p.zoning, p.flood_zone, p.parcel_id,
               sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM comps c
        JOIN properties p ON p.property_id = c.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = c.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND c.review_status = 'confirmed'"
    if city:
        sql += " AND lower(p.address_city) = lower(?)"
        params.append(city)
    if property_type:
        sql += " AND lower(p.property_type) = lower(?)"
        params.append(property_type)
    if address_contains:
        sql += " AND lower(p.address_street) LIKE lower(?)"
        params.append(f"%{address_contains}%")
    if sale_date_from:
        sql += " AND c.sale_date >= ?"
        params.append(sale_date_from)
    if sale_date_to:
        sql += " AND c.sale_date <= ?"
        params.append(sale_date_to)
    sql += " ORDER BY c.sale_date DESC, c.comp_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def search_lease_comps(
    db_path=None,
    *,
    city=None,
    property_type=None,
    address_contains=None,
    include_unreviewed=False,
):
    """Return canonical lease-comp rows for market-rent analysis."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(db_path)
    sql = """
        SELECT lc.lease_comp_id, lc.identity_key, lc.review_status,
               lc.tenant_name, lc.tenant_use, lc.lease_date,
               lc.lease_expiration, lc.term_years, lc.sf_leased,
               lc.base_rent_psf, lc.base_rent_monthly, lc.rent_structure,
               lc.expense_stop_psf, lc.ti_allowance_psf,
               lc.free_rent_months, lc.escalations, lc.renewal_options,
               lc.submarket, lc.confidence,
               p.address_street, p.address_city, p.address_county,
               p.address_state, p.address_zip, p.property_type,
               p.property_subtype, p.gba_sf,
               sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM lease_comps lc
        JOIN properties p ON p.property_id = lc.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = lc.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND lc.review_status = 'confirmed'"
    if city:
        sql += " AND lower(p.address_city) = lower(?)"
        params.append(city)
    if property_type:
        sql += " AND lower(p.property_type) = lower(?)"
        params.append(property_type)
    if address_contains:
        sql += " AND lower(p.address_street) LIKE lower(?)"
        params.append(f"%{address_contains}%")
    sql += " ORDER BY lc.lease_date DESC, lc.lease_comp_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


if __name__ == "__main__":
    init_db()
