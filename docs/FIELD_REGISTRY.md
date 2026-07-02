# Axiom Field Registry

`schemas/field_registry.v1.json` is the authoritative contract between the
assignment workbook, exported JSON, Python pipeline, and document templates.
Word templates consume registered fields; they do not define the data model.

## Registry structure

- `schema_version`: semantic version of the contract.
- `load_order`: runtime producer order. Later nonblank values win.
- `fields`: ordinary scalar values available to documents and application code.
- `blocks`: media, tables, comparable pages, and generated narratives.

Each field records:

- `value_kind`: current transport/display type. The initial contract uses text
  variants because Intake JSON and report-ready workbook outputs are formatted
  strings.
- `source_of_truth`: the producer that owns the final value.
- `producers`: every current location that can provide the key.
- `used_in`: workflow stages whose configured templates consume the key.
- `description`: Intake guidance when available.

When a key exists in both Intake and workbook Outputs, `workbook_output` is the
source of truth because `fill_engine.load_variables()` loads JSON first and
then applies the last nonblank workbook output.

## Versioning

- Patch: descriptions or metadata corrections that do not alter accepted data.
- Minor: backward-compatible fields or blocks.
- Major: removed/renamed fields, changed meaning, changed ownership, or changed
  value representation that requires assignment/template migration.

Assignments record the application and schema versions when created. Delivery
also records the delivery-template filename and SHA-256 hash.

## Change workflow

1. Decide the field name, meaning, value kind, and source of truth.
2. Add it to the registry before adding it to Excel, JSON, or Word.
3. Update the producer and any consuming templates or handlers.
4. Increment `schema_version`.
5. Run `python axiom.py contract`.
6. Run `python -m unittest discover -s tests -v`.
7. Commit the registry and implementation together.

`scripts/build_field_registry.py` created the initial verified baseline. It is
a bootstrap tool, not the normal way to evolve the contract; routine changes
should be deliberate registry edits following the steps above.
