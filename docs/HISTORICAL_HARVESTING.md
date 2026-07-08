# Historical Assignment and Financial Harvesting

## Scope

Historical reports now produce six reusable record types in addition to sale
and lease comparables:

- assignment conclusions (`axiom.assignment.conclusion` v1.0.0);
- income snapshots (`axiom.income.snapshot` v1.0.0);
- rent-roll entries (`axiom.rent_roll.entry` v1.0.0);
- operating-expense lines (`axiom.operating_expense.line` v1.0.0);
- market observations (`axiom.market.observation` v1.0.0);
- source artifacts (`axiom.source.artifact` v1.0.0).

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

All six record types use the comparable pipeline's controls:

- immutable source SHA-256, path, filename, size, and modification metadata;
- per-field confidence and validation findings;
- explicit unreviewed/confirmed/rejected state;
- reviewer, review timestamp, and edit history;
- changed-source rejection between extraction and commit;
- reviewed-only search;
- unique database identities and transactional commit.

The Streamlit review surface displays and edits all six record types. CLI
review shows the report conclusion, income summary, rent roll, expenses, and
market observations and source artifacts before confirmation.

## Source artifacts

The artifact index covers external PNG/JPEG/TIFF/WebP/GIF/BMP images and PDFs,
Word-embedded drawing images, Excel-embedded images, and native Excel chart
objects. It records likely kind (map, chart, photo, sketch, exhibit, or
decorative), title, media type, binary SHA-256, size, pixel dimensions when
available, effective date, geography, property type, container filename, and
exact file/package locator.

The binary artifact hash is distinct from its source-container hash. Therefore
an embedded map can be verified independently while a changed Word or Excel
container still fails the pre-commit source check. Identical binaries of the
same kind within an assignment collapse to one canonical record; their other
locations remain in `alternate_provenance`.

The index does not copy, rename, render, OCR, or otherwise alter source files.
Reviewed search is available through `db.search_source_artifacts()` and:

```text
python axiom.py artifact-search --kind map --geography "Demo City"
python axiom.py artifact-search --kind chart --title vacancy
python axiom.py artifact-search --sha256 <artifact-sha256>
```

## Market observations

The report extractor recognizes bounded sections under headings such as market
area analysis, regional/economic overview, neighborhood analysis,
property-market analysis, and supply/demand. A recognized heading starts an
observation and the next heading ends it. Sections shorter than 80 characters
are discarded; sections longer than 12,000 characters are explicitly marked
as truncated.

Each observation stores category, original heading, reviewed text, effective
date, geography, property type, source hash, and exact paragraph range. This
is intentionally not a whole-report text dump: valuation reconciliation and
unrelated report sections stay outside the observation unless explicitly
recognized and reviewed.

Search is available through `db.search_market_observations()` and:

```text
python axiom.py observation-search --category market_area --geography "Demo City"
python axiom.py observation-search --type Office --text vacancy --from 2024-01-01
```

## Rent rolls and operating expenses

Rent-roll workbooks are stored as subject-property occupancy evidence, not
market lease comparables. Each row can retain unit/suite, tenant, use, area,
lease dates, monthly/annual rent, rent per square foot, reimbursement
structure, occupancy status, and rent-roll date.

The Excel rent-roll adapter recognizes standard commercial rows plus common
specialty-property variants from archive examples: mini-storage unit lists,
mobile-home lot rolls, apartment room/unit rolls, and RV-site rolls. Site,
lot, room, apartment, and unit identifiers normalize to the same canonical
`unit_id` field. Resident/name, move-in, lease-expiration, rent, status,
discount, and note-style columns are normalized where possible while retaining
the original source record for review. Duplicate master-list/category-sheet
rows collapse before review, with alternate worksheet provenance retained.

Native PDF rent-roll tables are parsed when the PDF contains extractable table
structure. Rows normalize into the same `axiom.rent_roll.entry` contract and
retain page/table/row locators such as `pdf:page:1:table:1:row:3`. Image-only
or scanned PDFs are intentionally not OCRed in this lane; they remain queued
for a separate OCR workflow.

Operating expenses use period year/type, category, amount, amount per square
foot, and notes. The extractor supports normalized long-form rows as well as
basic wide multi-year statements where year/scenario columns are spread across
the worksheet, including two-row headers such as year above `Actual` and
`$/SF`. Wide rows are exploded into the same canonical expense-line contract.
Total/subtotal rows are excluded so downstream analysis does not double count
detail and totals.

Native text-position accounting PDFs are also parsed when the PDF exposes
selectable words but not a clean table grid. The adapter looks for recognized
expense sections, takes the rightmost money value on each detail line, excludes
totals/subtotals and income/NOI/net-income rows, infers period year/type from
statement text and filename, and records locators such as
`pdf:page:1:line:7`.

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
income chart. `tests/test_financial_harvest.py` adds fictional standard and
specialty rent-roll workbooks, native PDF rent-roll tables, native
text-position accounting PDFs, normalized expense workbooks, and wide
multi-year operating-statement workbooks, while
`tests/test_observation_harvest.py` proves bounded heading-based narrative
sections. `tests/test_artifact_harvest.py` adds external files, duplicate
paths, Word-embedded images, and a native Excel chart. Together they prove
scan, extraction, normalization, staging, review edits, commit, duplicate
recommit, reviewed search, changed-source rejection, rollback, and database
initialization/migration behavior.

## Deliberate limits

The rent-roll extractor handles common Excel specialty-property layouts and
native PDF rent-roll tables, but does not OCR scanned/image-only rent rolls.
The expense extractor handles normalized long-form rows, basic wide multi-year
operating statements, and native text-position accounting PDFs. It does not
OCR scanned/image-only statements. Highly customized statements with stacked
sections, inconsistent subtotal bands, multi-column side-by-side periods, or
non-year scenario columns will need additional layout adapters before
archive-scale import. Neither rent-roll rows nor expense lines are
automatically treated as market evidence; that distinction requires a later
analytical promotion step.

PDFs are currently indexed as whole-file exhibits rather than page-level
artifacts. Embedded media classification uses filenames, container names, and
available alt text; ambiguous items remain reviewable instead of being treated
as authoritative automatically.
