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

The fixture currently produces zero ordinary missing placeholders and 18
unresolved pipeline blocks. Those blocks are expected until their handlers are
implemented.
