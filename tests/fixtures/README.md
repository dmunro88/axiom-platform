# Sanitized Demo Fixture

`DEMO-001/` is the approved regression fixture. Its people, companies,
addresses, tenants, legal description, FEMA identifier, and comparable
locations are intentionally fictional. The canonical identity is documented in
`demo_profile.json`.

The fixture was accepted only after all of the following were replaced or
removed:

- client, contact, owner, and appraiser identities;
- postal and email addresses and telephone numbers;
- parcel, deed, legal-description, and account identifiers;
- engagement, invoice, and signature identifiers;
- embedded document metadata and comments;
- subject and comparable property photographs;
- map images and coordinates that reveal the original property;
- hidden workbook sheets, cached values, formulas, names, comments, and links
  containing real assignment data.

The fixture contains three fully fictional comparable sales and eleven
conspicuously labeled synthetic QA images. Run
`scripts/build_demo_media.py` to reproduce the image assets. None of these
inputs are appraisal evidence.

Fixture validation produces zero ordinary missing placeholders and eight
unresolved pipeline blocks, all of which are intentionally local AI
narratives. Ten sales-comparison formula caches remain errors because the
fixture exercises report-page comp insertion, not the separate adjustment-grid
model. The ownership table is generated from the fixture's existing assignment
fields.

Presentation-only lowercase, title-case, and zoning-table aliases are omitted
from fixture JSON. `fill_engine.load_variables()` derives them from canonical
fields during every test and report generation.

The fixture workbook's Intake sheet mirrors its canonical JSON fields so
registry-aware freshness validation can run without special fixture bypasses.
