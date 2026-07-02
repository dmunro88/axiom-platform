# Historical Assignment and Income Harvesting

## Scope

Historical reports now produce two reusable record types in addition to sale
and lease comparables:

- assignment conclusions (`axiom.assignment.conclusion` v1.0.0);
- income snapshots (`axiom.income.snapshot` v1.0.0).

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

Both records use the comparable pipeline's controls:

- immutable source SHA-256, path, filename, size, and modification metadata;
- per-field confidence and validation findings;
- explicit unreviewed/confirmed/rejected state;
- reviewer, review timestamp, and edit history;
- changed-source rejection between extraction and commit;
- reviewed-only search;
- unique database identities and transactional commit.

The Streamlit review surface displays and edits both records. CLI review shows
the report conclusion and income summary before confirmation.

## Verified fictional slice

`tests/test_historical_harvest.py` builds a fictional old report and standalone
income chart, then proves scan, extraction, normalization, staging, review,
commit, duplicate recommit, reviewed search, rollback, and additive migration
of a legacy database.

## Deliberate limits

This is a compact summary extractor, not a full income-approach model parser.
The next layers should add row-level rent rolls and operating expenses, with
their own identities and source locators, before deriving reusable market
statistics.
