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
  rent_roll_entries  — subject occupancy and contract-rent rows
  operating_expenses — normalized historical expense lines
  market_observations — reviewed, bounded narrative evidence
  source_artifacts    — reviewed external and Office-embedded media/evidence

Usage
-----
  from db import init_db, get_conn
  init_db()                  # creates axiom.db if it doesn't exist
  conn = get_conn()          # sqlite3 connection with Row factory
"""

import datetime
import hashlib
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

-- ── Rent-roll entries ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rent_roll_entries (
    rent_roll_entry_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id       INTEGER REFERENCES assignments(assignment_id),
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    as_of_date          TEXT,
    unit_id             TEXT,
    suite               TEXT,
    tenant_name         TEXT,
    tenant_use          TEXT,
    sf_leased           REAL,
    lease_start         TEXT,
    lease_end           TEXT,
    monthly_rent        REAL,
    annual_rent         REAL,
    rent_psf            REAL,
    reimbursement_structure TEXT,
    occupancy_status    TEXT,
    identity_key        TEXT,
    confidence          TEXT,
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Operating-expense lines ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS operating_expenses (
    expense_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id       INTEGER REFERENCES assignments(assignment_id),
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    period_year         INTEGER,
    period_type         TEXT,
    category            TEXT,
    amount              REAL,
    amount_per_sf       REAL,
    notes               TEXT,
    identity_key        TEXT,
    confidence          TEXT,
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Reviewed market observations ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_observations (
    observation_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id       INTEGER REFERENCES assignments(assignment_id),
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    category            TEXT,
    title               TEXT,
    observation_text    TEXT,
    effective_date      TEXT,
    geography           TEXT,
    property_type       TEXT,
    truncated           TEXT,
    identity_key        TEXT,
    confidence          TEXT,
    review_status       TEXT    DEFAULT 'unreviewed',
    reviewed_at         TEXT,
    source_record_json  TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ── Searchable source artifacts ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_artifacts (
    artifact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id       INTEGER REFERENCES assignments(assignment_id),
    property_id         INTEGER REFERENCES properties(property_id),
    source_doc_id       INTEGER REFERENCES source_documents(doc_id),
    comp_id             INTEGER REFERENCES comps(comp_id),
    lease_comp_id       INTEGER REFERENCES lease_comps(lease_comp_id),
    artifact_kind       TEXT,
    title               TEXT,
    description         TEXT,
    artifact_filename   TEXT,
    container_filename  TEXT,
    media_type          TEXT,
    extension           TEXT,
    artifact_sha256     TEXT,
    artifact_size       INTEGER,
    width_px            INTEGER,
    height_px           INTEGER,
    effective_date      TEXT,
    geography           TEXT,
    property_type       TEXT,
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
    "source_artifacts": {
        "comp_id": "INTEGER REFERENCES comps(comp_id)",
        "lease_comp_id": "INTEGER REFERENCES lease_comps(lease_comp_id)",
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_rent_roll_entries_identity_key
    ON rent_roll_entries(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_operating_expenses_identity_key
    ON operating_expenses(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_market_observations_identity_key
    ON market_observations(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_source_artifacts_identity_key
    ON source_artifacts(identity_key)
    WHERE identity_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_artifacts_sha256
    ON source_artifacts(artifact_sha256);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_comp_id
    ON source_artifacts(comp_id);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_lease_comp_id
    ON source_artifacts(lease_comp_id);
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


def backfill_legacy_identities(conn):
    """Compute and store identity_key for legacy comps/lease_comps/
    assignments/income_snapshots rows that predate the identity-key column
    (still NULL after `_apply_migrations` merely added the column). Without
    this, a legacy row is invisible to `comparable_id_by_identity`/
    `harvest_id_by_identity` -- both match on identity_key, and NULL never
    matches -- so re-importing a real historical archive that overlaps with
    already-ingested legacy data would insert duplicates instead of being
    recognized and skipped. Safe to call repeatedly: it only ever fills
    identity_key where it is currently NULL and never overwrites an existing
    value. Returns a dict of rows backfilled per table.

    `rent_roll_entries`/`operating_expenses`/`market_observations`/
    `source_artifacts` are not handled here: unlike comps/lease_comps/
    assignments/income_snapshots, those tables were introduced with
    identity_key already part of their schema, so every row in them was
    already assigned one at insert time -- there is no legacy-without-
    identity case for those tables to backfill.
    """
    from comparable_contract import comparable_identity
    from harvest_contract import assignment_identity, income_identity

    counts = {
        "comps": 0,
        "lease_comps": 0,
        "assignments": 0,
        "income_snapshots": 0,
    }

    def _table_has_columns(table, columns):
        try:
            existing = {
                row[1]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
        except sqlite3.OperationalError:
            return False
        return set(columns).issubset(existing)

    if not _table_has_columns(
        "comps", {"identity_key", "sale_date", "sale_price"}
    ) or not _table_has_columns("properties", {"address_street", "address_city"}):
        return counts

    for row in conn.execute(
        """
        SELECT c.comp_id, c.sale_date, c.sale_price,
               p.address_street, p.address_city
        FROM comps c
        LEFT JOIN properties p ON p.property_id = c.property_id
        WHERE c.identity_key IS NULL
        """
    ).fetchall():
        identity_key = comparable_identity("sale", {
            "address_street": row["address_street"],
            "address_city": row["address_city"],
            "sale_date": row["sale_date"],
            "sale_price": row["sale_price"],
        })
        conn.execute(
            "UPDATE comps SET identity_key = ? WHERE comp_id = ?",
            (identity_key, row["comp_id"]),
        )
        counts["comps"] += 1

    if _table_has_columns(
        "lease_comps",
        {"identity_key", "tenant_name", "lease_date", "sf_leased", "base_rent_psf"},
    ) and _table_has_columns("properties", {"address_street", "address_city"}):
        rows = conn.execute(
            """
            SELECT lc.lease_comp_id, lc.tenant_name, lc.lease_date,
                   lc.sf_leased, lc.base_rent_psf,
                   p.address_street, p.address_city
            FROM lease_comps lc
            LEFT JOIN properties p ON p.property_id = lc.property_id
            WHERE lc.identity_key IS NULL
            """
        ).fetchall()
    else:
        rows = []
    for row in rows:
        identity_key = comparable_identity("lease", {
            "address_street": row["address_street"],
            "address_city": row["address_city"],
            "tenant_name": row["tenant_name"],
            "lease_date": row["lease_date"],
            "sf_leased": row["sf_leased"],
            "base_rent_psf": row["base_rent_psf"],
        })
        conn.execute(
            "UPDATE lease_comps SET identity_key = ? WHERE lease_comp_id = ?",
            (identity_key, row["lease_comp_id"]),
        )
        counts["lease_comps"] += 1

    if _table_has_columns(
        "assignments",
        {"identity_key", "file_no", "effective_date", "reconciled_value"},
    ) and _table_has_columns("properties", {"address_street"}) and _table_has_columns(
        "source_documents", {"content_sha256"}
    ):
        rows = conn.execute(
            """
            SELECT a.assignment_id, a.file_no, a.effective_date,
                   a.reconciled_value, p.address_street,
                   sd.content_sha256 AS source_sha256
            FROM assignments a
            LEFT JOIN properties p ON p.property_id = a.property_id
            LEFT JOIN source_documents sd ON sd.doc_id = a.source_doc_id
            WHERE a.identity_key IS NULL
            """
        ).fetchall()
    else:
        rows = []
    for row in rows:
        identity_key = assignment_identity(
            {
                "file_no": row["file_no"],
                "address_street": row["address_street"],
                "effective_date": row["effective_date"],
                "reconciled_value": row["reconciled_value"],
            },
            row["source_sha256"],
        )
        conn.execute(
            "UPDATE assignments SET identity_key = ? WHERE assignment_id = ?",
            (identity_key, row["assignment_id"]),
        )
        counts["assignments"] += 1

    # income_snapshots has no assignment_id FK (see schema above), so legacy
    # rows fall back to their source document's content hash for identity --
    # the same fallback `_record()` uses at insert time when no assignment
    # context is available.
    if _table_has_columns(
        "income_snapshots",
        {"identity_key", "period_year", "period_type", "noi"},
    ) and _table_has_columns("source_documents", {"content_sha256"}):
        rows = conn.execute(
            """
            SELECT i.snapshot_id, i.period_year, i.period_type, i.noi,
                   sd.content_sha256 AS source_sha256
            FROM income_snapshots i
            LEFT JOIN source_documents sd ON sd.doc_id = i.source_doc_id
            WHERE i.identity_key IS NULL
            """
        ).fetchall()
    else:
        rows = []
    for row in rows:
        identity_key = income_identity(
            {
                "period_year": row["period_year"],
                "period_type": row["period_type"],
                "noi": row["noi"],
            },
            None,
            row["source_sha256"],
        )
        conn.execute(
            "UPDATE income_snapshots SET identity_key = ? WHERE snapshot_id = ?",
            (identity_key, row["snapshot_id"]),
        )
        counts["income_snapshots"] += 1

    return counts


def init_db(db_path=None, quiet=False):
    """
    Create the database and all tables if they don't exist.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    Returns the path to the database file.
    """
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _apply_migrations(conn)
    backfill_legacy_identities(conn)
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


def _upsert_property_by_address(data, conn):
    street = (data.get("address_street") or "").strip().lower()
    city = (data.get("address_city") or "").strip().lower()
    if street:
        row = conn.execute(
            """
            SELECT property_id
            FROM properties
            WHERE lower(address_street) = ?
              AND lower(coalesce(address_city, '')) = ?
            """,
            (street, city),
        ).fetchone()
        if row:
            return row["property_id"]
    return insert_property(data, conn)


def insert_manual_comparable(record_kind, data, db_path=None, conn=None):
    """Insert a user-entered sale or lease comparable as a confirmed record."""
    from comparable_contract import (
        comparable_identity,
        normalize_data,
        validate_record,
    )

    if record_kind not in {"sale", "lease"}:
        raise ValueError("record_kind must be 'sale' or 'lease'.")

    close_after = conn is None
    if conn is None:
        init_db(db_path, quiet=True)
        conn = get_conn(db_path)

    try:
        normalized = normalize_data(data or {})
        confidence = {
            key: "high"
            for key, value in normalized.items()
            if value not in (None, "")
        }
        reviewed_at = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        review = {
            "status": "confirmed",
            "reviewed_at": reviewed_at,
        }
        source_record = {
            "contract_id": "axiom.comparable.record",
            "schema_version": "1.0.0",
            "record_kind": record_kind,
            "data": normalized,
            "confidence": confidence,
            "review": review,
            "provenance": {
                "source_path": "manual-entry",
                "source_sha256": "manual-entry",
            },
            "source": {
                "type": "manual_entry",
            },
        }
        findings = validate_record(source_record)
        if findings["errors"]:
            raise ValueError("; ".join(findings["errors"]))

        identity_key = comparable_identity(record_kind, normalized)
        with conn:
            existing_id = comparable_id_by_identity(record_kind, identity_key, conn)
            if existing_id:
                return {
                    "created": False,
                    "id": existing_id,
                    "identity_key": identity_key,
                }
            property_id = _upsert_property_by_address(normalized, conn)
            if record_kind == "sale":
                record_id = insert_comp(
                    normalized,
                    property_id,
                    None,
                    confidence,
                    conn,
                    identity_key=identity_key,
                    review=review,
                    source_record=source_record,
                )
            else:
                record_id = insert_lease_comp(
                    normalized,
                    property_id,
                    None,
                    confidence,
                    conn,
                    identity_key=identity_key,
                    review=review,
                    source_record=source_record,
                )
            return {
                "created": True,
                "id": record_id,
                "identity_key": identity_key,
            }
    finally:
        if close_after:
            conn.close()


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


def _insert_harvest_row(
    table,
    fields,
    data,
    assignment_id,
    property_id,
    source_doc_id,
    conn,
    *,
    identity_key,
    confidence,
    review,
    source_record,
):
    row = {field: data.get(field) for field in fields}
    row["assignment_id"] = assignment_id
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
    columns = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    cursor = conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        list(row.values()),
    )
    return cursor.lastrowid


def insert_rent_roll_entry(
    data,
    assignment_id,
    property_id,
    source_doc_id,
    conn,
    **record_metadata,
):
    fields = [
        "as_of_date",
        "unit_id",
        "suite",
        "tenant_name",
        "tenant_use",
        "sf_leased",
        "lease_start",
        "lease_end",
        "monthly_rent",
        "annual_rent",
        "rent_psf",
        "reimbursement_structure",
        "occupancy_status",
    ]
    return _insert_harvest_row(
        "rent_roll_entries",
        fields,
        data,
        assignment_id,
        property_id,
        source_doc_id,
        conn,
        **record_metadata,
    )


def insert_operating_expense(
    data,
    assignment_id,
    property_id,
    source_doc_id,
    conn,
    **record_metadata,
):
    fields = [
        "period_year",
        "period_type",
        "category",
        "amount",
        "amount_per_sf",
        "notes",
    ]
    return _insert_harvest_row(
        "operating_expenses",
        fields,
        data,
        assignment_id,
        property_id,
        source_doc_id,
        conn,
        **record_metadata,
    )


def insert_market_observation(
    data,
    assignment_id,
    property_id,
    source_doc_id,
    conn,
    **record_metadata,
):
    storage_data = dict(data)
    storage_data["observation_text"] = storage_data.pop("text", None)
    fields = [
        "category",
        "title",
        "observation_text",
        "effective_date",
        "geography",
        "property_type",
        "truncated",
    ]
    return _insert_harvest_row(
        "market_observations",
        fields,
        storage_data,
        assignment_id,
        property_id,
        source_doc_id,
        conn,
        **record_metadata,
    )


def insert_source_artifact(
    data,
    assignment_id,
    property_id,
    source_doc_id,
    conn,
    **record_metadata,
):
    fields = [
        "artifact_kind",
        "title",
        "description",
        "artifact_filename",
        "container_filename",
        "media_type",
        "extension",
        "artifact_sha256",
        "artifact_size",
        "width_px",
        "height_px",
        "effective_date",
        "geography",
        "property_type",
        "comp_id",
        "lease_comp_id",
    ]
    return _insert_harvest_row(
        "source_artifacts",
        fields,
        data,
        assignment_id,
        property_id,
        source_doc_id,
        conn,
        **record_metadata,
    )


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_dimensions(path):
    try:
        from PIL import Image
    except ImportError:
        return None, None
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None, None


def _manual_photo_media_type(extension):
    ext = extension.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    return f"image/{ext}" if ext in {"jpeg", "png"} else "image"


def insert_manual_comp_photo(
    record_kind,
    record_id,
    image_path,
    conn=None,
    *,
    title=None,
    original_filename=None,
):
    """Attach a locally asserted photo artifact to one sale or lease comp.

    This is intentionally a direct confirmed insert rather than a staged
    extraction record: the appraiser is manually attaching the image to the
    selected comp in the Browse tab.
    """
    if record_kind not in {"sale", "lease"}:
        raise ValueError("record_kind must be 'sale' or 'lease'.")

    close_after = conn is None
    if conn is None:
        conn = get_conn()

    table = "comps" if record_kind == "sale" else "lease_comps"
    id_column = "comp_id" if record_kind == "sale" else "lease_comp_id"
    link_column = id_column
    row = conn.execute(
        f"""
        SELECT c.{id_column}, c.property_id, c.source_doc_id,
               p.address_street, p.address_city, p.property_type
        FROM {table} c
        LEFT JOIN properties p ON p.property_id = c.property_id
        WHERE c.{id_column} = ?
        """,
        (record_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No {record_kind} comp found with id {record_id}.")

    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"Photo file not found: {path}")

    sha256 = _sha256_file(path)
    identity_key = f"manual-{record_kind}-photo:{record_id}:{sha256}"
    existing = harvest_id_by_identity("artifact", identity_key, conn)
    if existing:
        if close_after:
            conn.close()
        return existing

    width_px, height_px = _image_dimensions(path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    address = row["address_street"] or f"{record_kind.title()} comp {record_id}"
    data = {
        "artifact_kind": "photo",
        "title": title or f"Comp photo - {address}",
        "description": "Manually attached comp photo.",
        "artifact_filename": str(path),
        "container_filename": original_filename,
        "media_type": _manual_photo_media_type(path.suffix),
        "extension": path.suffix.lower().lstrip("."),
        "artifact_sha256": sha256,
        "artifact_size": path.stat().st_size,
        "width_px": width_px,
        "height_px": height_px,
        "geography": row["address_city"],
        "property_type": row["property_type"],
        "comp_id": record_id if record_kind == "sale" else None,
        "lease_comp_id": record_id if record_kind == "lease" else None,
    }
    artifact_id = insert_source_artifact(
        data,
        None,
        row["property_id"],
        row["source_doc_id"],
        conn,
        identity_key=identity_key,
        confidence={
            "artifact_filename": "high",
            "artifact_sha256": "high",
            link_column: "high",
        },
        review={"status": "confirmed", "reviewed_at": now},
        source_record={
            "manual_attach": True,
            "record_kind": record_kind,
            "record_id": record_id,
            "original_filename": original_filename,
        },
    )
    if close_after:
        conn.commit()
        conn.close()
    return artifact_id


def comp_photo_artifacts(db_path=None, *, record_kind, record_id):
    """Return confirmed photo artifacts manually linked to one comp."""
    if record_kind not in {"sale", "lease"}:
        raise ValueError("record_kind must be 'sale' or 'lease'.")
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    column = "comp_id" if record_kind == "sale" else "lease_comp_id"
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT *
                FROM source_artifacts
                WHERE {column} = ?
                  AND review_status = 'confirmed'
                  AND lower(artifact_kind) = 'photo'
                ORDER BY artifact_id DESC
                """,
                (record_id,),
            ).fetchall()
        ]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def harvest_id_by_identity(record_kind, identity_key, conn):
    table, id_column = {
        "assignment": ("assignments", "assignment_id"),
        "income": ("income_snapshots", "snapshot_id"),
        "rent_roll": ("rent_roll_entries", "rent_roll_entry_id"),
        "expense": ("operating_expenses", "expense_id"),
        "observation": ("market_observations", "observation_id"),
        "artifact": ("source_artifacts", "artifact_id"),
    }[record_kind]
    row = conn.execute(
        f"SELECT {id_column} FROM {table} WHERE identity_key = ?",
        (identity_key,),
    ).fetchone()
    return row[id_column] if row else None


def search_rent_roll_entries(
    db_path=None,
    *,
    tenant_contains=None,
    as_of_date=None,
    include_unreviewed=False,
):
    """Return reviewed historical rent-roll rows."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT r.*, a.file_no, p.address_street, p.address_city,
               sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM rent_roll_entries r
        LEFT JOIN assignments a ON a.assignment_id = r.assignment_id
        LEFT JOIN properties p ON p.property_id = r.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = r.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND r.review_status = 'confirmed'"
    if tenant_contains:
        sql += " AND lower(r.tenant_name) LIKE lower(?)"
        params.append(f"%{tenant_contains}%")
    if as_of_date:
        sql += " AND r.as_of_date = ?"
        params.append(as_of_date)
    sql += " ORDER BY r.as_of_date DESC, r.rent_roll_entry_id"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def search_operating_expenses(
    db_path=None,
    *,
    period_year=None,
    category_contains=None,
    include_unreviewed=False,
):
    """Return reviewed historical operating-expense lines."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT e.*, a.file_no, p.address_street, p.address_city,
               sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM operating_expenses e
        LEFT JOIN assignments a ON a.assignment_id = e.assignment_id
        LEFT JOIN properties p ON p.property_id = e.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = e.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND e.review_status = 'confirmed'"
    if period_year is not None:
        sql += " AND e.period_year = ?"
        params.append(period_year)
    if category_contains:
        sql += " AND lower(e.category) LIKE lower(?)"
        params.append(f"%{category_contains}%")
    sql += " ORDER BY e.period_year DESC, e.category, e.expense_id"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def search_market_observations(
    db_path=None,
    *,
    category=None,
    geography=None,
    property_type=None,
    text_contains=None,
    effective_date_from=None,
    effective_date_to=None,
    include_unreviewed=False,
):
    """Return reviewed, source-traceable market observations."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT o.*, a.file_no, p.address_street, p.address_city,
               sd.filename AS source_filename,
               sd.content_sha256 AS source_sha256
        FROM market_observations o
        LEFT JOIN assignments a ON a.assignment_id = o.assignment_id
        LEFT JOIN properties p ON p.property_id = o.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = o.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND o.review_status = 'confirmed'"
    if category:
        sql += " AND lower(o.category) = lower(?)"
        params.append(category)
    if geography:
        sql += " AND lower(o.geography) LIKE lower(?)"
        params.append(f"%{geography}%")
    if property_type:
        sql += " AND lower(o.property_type) = lower(?)"
        params.append(property_type)
    if text_contains:
        sql += " AND lower(o.observation_text) LIKE lower(?)"
        params.append(f"%{text_contains}%")
    if effective_date_from:
        sql += " AND o.effective_date >= ?"
        params.append(effective_date_from)
    if effective_date_to:
        sql += " AND o.effective_date <= ?"
        params.append(effective_date_to)
    sql += " ORDER BY o.effective_date DESC, o.observation_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


def search_source_artifacts(
    db_path=None,
    *,
    artifact_kind=None,
    title_contains=None,
    geography=None,
    property_type=None,
    artifact_sha256=None,
    comp_id=None,
    lease_comp_id=None,
    include_unreviewed=False,
):
    """Return reviewed external and container-embedded source artifacts."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    init_db(path, quiet=True)
    conn = get_conn(path)
    sql = """
        SELECT s.*, a.file_no, p.address_street, p.address_city,
               sd.filename AS source_filename,
               sd.filepath AS source_path,
               sd.content_sha256 AS source_sha256
        FROM source_artifacts s
        LEFT JOIN assignments a ON a.assignment_id = s.assignment_id
        LEFT JOIN properties p ON p.property_id = s.property_id
        LEFT JOIN source_documents sd ON sd.doc_id = s.source_doc_id
        WHERE 1=1
    """
    params = []
    if not include_unreviewed:
        sql += " AND s.review_status = 'confirmed'"
    if artifact_kind:
        sql += " AND lower(s.artifact_kind) = lower(?)"
        params.append(artifact_kind)
    if title_contains:
        sql += " AND lower(s.title) LIKE lower(?)"
        params.append(f"%{title_contains}%")
    if geography:
        sql += " AND lower(s.geography) LIKE lower(?)"
        params.append(f"%{geography}%")
    if property_type:
        sql += " AND lower(s.property_type) = lower(?)"
        params.append(property_type)
    if artifact_sha256:
        sql += " AND s.artifact_sha256 = ?"
        params.append(artifact_sha256)
    if comp_id is not None:
        sql += " AND s.comp_id = ?"
        params.append(comp_id)
    if lease_comp_id is not None:
        sql += " AND s.lease_comp_id = ?"
        params.append(lease_comp_id)
    sql += " ORDER BY s.effective_date DESC, s.artifact_id DESC"
    try:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    for row in rows:
        row["confidence"] = json.loads(row.get("confidence") or "{}")
    return rows


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
