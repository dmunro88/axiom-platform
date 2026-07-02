# Comparable Intelligence Architecture

## Purpose

The comparable library is a shared evidence system, not a report-template
feature. It converts historical source files into reviewed, traceable records
that can be searched, exported, and reused by assignments and reports.

```text
historical folders
    -> scan and classify
    -> extract structured records
    -> canonicalize and fingerprint
    -> stage
    -> human review/edit/reject
    -> transactional commit
    -> reviewed database
    -> search / CSV / workbook comp_data
```

## Canonical record

`schemas/comparable_record.v1.json` defines contract
`axiom.comparable.record` v1.0.0 for sale and lease comps.

Each staged record carries:

- normalized `data`;
- per-field `confidence`;
- stable `identity_key`;
- immutable source path, filename, SHA-256, size, and modified timestamp;
- source locator/extraction method;
- explicit review status, reviewer, timestamp, and edits;
- validation errors and warnings.

Storage semantics are explicit:

- money is decimal dollars;
- area is square feet;
- rates are decimal fractions (`0.085` means 8.5%);
- dates are ISO `YYYY-MM-DD`.

## Identity and duplicate handling

Sale identity uses normalized address, city, sale date, and sale price. Lease
identity uses normalized address, city, tenant, lease date, leased area, and
base rent. This prevents the old failure where unrelated sales at the same
price collapsed into one record.

Source documents are identified by content SHA-256, not only filepath. Moving
or renaming an unchanged source does not duplicate it. A source that changes
after extraction is rejected at commit and must be re-extracted.

SQLite unique indexes enforce source-content and comp-identity idempotency.

## Review and commit rules

- Unreviewed batches cannot commit.
- Only records with `review.status = confirmed` enter searchable comp tables.
- UI and CLI edits are retained in record provenance.
- Each confirmed file commits in one SQLite transaction.
- A malformed record rolls the transaction back and leaves the confirmed JSON
  available for correction.
- Recommitting the same reviewed evidence is safe and reports duplicates
  skipped.

## Search and export

`db.search_sale_comps()` and `db.search_lease_comps()` return reviewed records
with source lineage. Filters currently include city, property type, address,
and sale-date range.

`comp_library.py` exports reviewed sale results to:

- UTF-8 CSV;
- a copied assignment workbook's `comp_data` sheet using the existing
  `COMP_COLUMNS` report contract.

CLI entry points:

```text
python axiom.py comp-ingest <historical-projects-root>
python axiom.py review-staged
python axiom.py comp-commit
python axiom.py comp-search [--lease] [--city CITY] [--type TYPE]
```

The Streamlit Comp Library remains the primary visual review and browse
surface.

## Verified fictional vertical slice

The automated fixture creates an old-style market workbook and proves:

1. scan/classification;
2. extraction of two sales and one lease;
3. correct retention of two distinct sales sharing the same price;
4. decimal cap-rate normalization;
5. source hashing and per-record review provenance;
6. transactional commit and rollback;
7. idempotency after moving/renaming identical source content;
8. reviewed sale/lease search;
9. CSV export;
10. export into workbook `comp_data` and successful report-comp loading.
11. additive migration/backfill of legacy local database rows.

## Next harvesting lanes

The same batch/provenance/review pattern should next be extended to:

1. assignment conclusions and income snapshots;
2. rent rolls and expense comparables;
3. reusable narrative/market observations with effective dates;
4. charts, maps, and exhibits as separately indexed artifacts;
5. file classification, renaming, and assignment filing;
6. bid-log and appraisal-log synchronization through a canonical assignment
   event model.
