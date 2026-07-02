# Historical Assignment and Financial Harvesting

## Scope

Historical reports now produce two reusable record types in addition to sale
and lease comparables, plus two row-level financial record types:

- assignment conclusions (`axiom.assignment.conclusion` v1.0.0);
- income snapshots (`axiom.income.snapshot` v1.0.0);
- rent-roll entries (`axiom.rent_roll.entry` v1.0.0);
- operating-expense lines (`axiom.operating_expense.line` v1.0.0).

The machine-readable descriptor is
`schemas/historical_harvest.v1.json`.

## Assignment conclusions

The record retains the file number, subject identity, client, report and
effective dates, approaches used, individual approach values, and reconciled
value. Its identity combines file number, subject address, effective date, and
reconciled value. This keeps a copied or moved report idempotent without
collapsing distinct valuation dates or conclusions.

## Income snapshots

The extractor recognizes compact report labels for period year/type, potential
gross income, vacancy, effective gross income, expenses, expense ratio, NOI,
and applied capitalization rate. Standalone Word files named as income charts
are now processed; previously they were classified and then ignored.

Rates are stored as decimal fractions and money as decimal dollars. Snapshot
identity combines the parent assignment identity, period, period type, and NOI.

## Safety and review

All four record types use the comparable pipeline's controls:

- immutable source SHA-256, path, filename, size, and modification metadata;
- per-field confidence and validation findings;
- explicit unreviewed/confirmed/rejected state;
- reviewer, review timestamp, and edit history;
- changed-source rejection between extraction and commit;
- reviewed-only search;
- unique database identities and transactional commit.

The Streamlit review surface displays and edits all four record types. CLI review shows
the report conclusion, income summary, rent roll, and expenses before
confirmation.

## Rent rolls and operating expenses

Rent-roll workbooks are stored as subject-property occupancy evidence, not
market lease comparables. Each row can retain unit/suite, tenant, use, area,
lease dates, monthly/annual rent, rent per square foot, reimbursement
structure, occupancy status, and rent-roll date.

Operating expenses use normalized long-form rows with period year/type,
category, amount, amount per square foot, and notes. Total/subtotal rows are
excluded so downstream analysis does not double count detail and totals.

Both record identities include the parent assignment identity. Worksheet and
source-row locators make every database row traceable to its original cell
region. Exact duplicate source rows collapse before review.

Reviewed records can be queried through `db.search_rent_roll_entries()` and
`db.search_operating_expenses()`, or from the CLI:

```text
python axiom.py financial-search --tenant "Tenant Name" --as-of 2025-06-30
python axiom.py financial-search --expenses --year 2025 --category taxes
```

## Verified fictional slice

`tests/test_historical_harvest.py` builds a fictional old report and standalone
income chart. `tests/test_financial_harvest.py` adds fictional rent-roll and
expense workbooks. Together they prove scan, extraction, normalization,
staging, review edits, commit, duplicate recommit, reviewed search, rollback,
and database initialization/migration behavior.

## Deliberate limits

The expense extractor currently expects normalized long-form rows. Historical
workbooks with years spread across columns or custom subtotal layouts will
need layout adapters before archive-scale import. Neither rent-roll rows nor
expense lines are automatically treated as market evidence; that distinction
requires a later analytical promotion step.
