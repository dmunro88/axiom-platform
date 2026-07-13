# Manual Comparable Entry Spec

## Purpose

This document is the working spec for making manual sale and lease comparable
entry useful enough for production appraisal work.

The goal is not just to add more fields to a Streamlit form. Manual comparable
entry should become a structured worksheet system that can:

- capture all facts needed for a usable sale or lease comp;
- calculate derived metrics consistently;
- distinguish draft records from confirmed evidence;
- support review, editing, attachments, and verification;
- feed search, report exports, adjustment grids, and future analysis tools.

## How Derek Should Add Notes

Write naturally, but try to tag each note so it is easy to turn into code.
Use one of these labels at the start of a bullet:

- `FIELD:` a field that should exist.
- `REQUIRED:` a field that must be filled before confirmation.
- `CALC:` a value the app should calculate.
- `VALIDATION:` a rule, warning, or error condition.
- `UI:` how the screen should behave or be organized.
- `WORKFLOW:` draft/confirm/edit/reject behavior.
- `SEARCH:` how comps should be found, filtered, sorted, or grouped.
- `EXPORT:` how comps should flow to Excel, Word, CSV, or reports.
- `QUESTION:` an open decision.
- `EXAMPLE:` a real-world example or edge case.

Best format:

```text
- FIELD: Sale condition. Should allow Arm's Length, REO, Portfolio, Related
  Party, Court Ordered, Partial Interest, and Other.
- CALC: Price/SF should use sale price divided by GBA when GBA exists, else
  NLA, and show which denominator was used.
- VALIDATION: Do not confirm a sale comp without address, sale date, sale
  price, property type, GBA or NLA, and verification source.
```

If you are unsure where something belongs, put it under "Inbox" at the bottom.
That is better than overthinking the structure.

## Implementation Principles

- Manual entry should use the same canonical comparable model as extracted
  historical comps.
- This field list is intentionally expandable. Derek's starter `db fields.docx`
  is a beginning inventory, not an exhaustive schema.
- Field applicability should be property-type-aware. Office, retail,
  industrial, multifamily, land, special-use, and mixed-use comps should not
  all be forced through the same required fields.
- Calculations should live in tested Python functions, not only in UI code.
- Stored raw facts and derived metrics should be clearly separated.
- The UI should show calculated values before save/confirm.
- The system should allow incomplete drafts but protect confirmed records.
- Confirmed records should be traceable to verification notes and attachments.
- Database fields, UI fields, search fields, exports, and report fields should
  be mapped intentionally instead of drifting apart.

## Starter Field Inventory From `db fields.docx`

Derek provided this as an initial field inventory. It should be treated as a
starter checklist for schema/UI planning, not a final list. Some fields apply
only to certain property types.

### Initial Property Types

Use these as the starting controlled property-type list:

- `office`
- `retail`
- `medical_office`
- `industrial`
- `multifamily`
- `hospitality`
- `self_storage`
- `land`
- `religious_facility`
- `special_purpose`

UI labels:

- Office
- Retail
- Medical Office
- Industrial
- Multifamily
- Hospitality
- Self-Storage
- Land
- Religious Facility
- Special Purpose

Implementation notes:

- FIELD: Property type should be selected from a controlled list first, with
  room for future expansion.
- UI: Property type should drive which sections and fields are shown, required,
  optional, or hidden.
- VALIDATION: Required-field rules should be property-type-specific. For
  example, multifamily can require unit metrics, land can require site/utility
  fields, and office/retail/industrial can emphasize building area, tenancy,
  income, and physical characteristics.
- VALIDATION: Self-storage should have its own unit, rentable-area, occupancy,
  and income indicator rules rather than using generic industrial defaults.
- VALIDATION: Religious facilities should have their own physical, seating,
  site/parking, and special-use considerations rather than being buried inside
  generic Special Purpose.
- QUESTION: Should Medical Office be stored as its own top-level property type,
  or as `office` with `property_subtype = Medical Office`? Derek's starter list
  treats it as top-level for now.
- QUESTION: Should mixed-use be added now, or handled as Special Purpose/Other
  until the schema is more mature?

### Property Identification

- `record_id`
- `property_type`
- `property_subtype`
- `street_address`
- `city`
- `county`
- `state`
- `parcel_numbers`
- `longitude`
- `latitude`

### Sale Data

- `grantor`
- `grantee`
- `sale_date`
- `deed_book_page`
- `verification`
- `sale_price`
- `cash_equivalent_price`
- `adjusted_sale_price`

### Land Data

- `land_size`
- `zoning`
- `topography`
- `utilities`
- `shape`
- `flood_hazard`
- `access`
- `visibility`

### General Physical Data

- `building_type`
- `single_tenant`
- `multi_tenant`
- `construction_type`
- `roof_type`
- `foundation`
- `electrical`
- `hvac`
- `stories`
- `year_built`
- `condition`
- `unit_type`
- `number_of_units`
- `unit_size`
- `unit_amenities`

### Indicators

- `sale_price_per_sf`
- `sale_price_per_acre`
- `floor_area_ratio`
- `land_to_building_ratio`
- `average_unit_size`
- `total_number_of_units`
- `sale_price_per_unit`
- `occupancy_at_sale`
- `pgim`
- `egim`
- `expenses_per_sf`
- `expenses_per_unit`
- `expenses_as_pct_of_pgi`
- `expenses_as_pct_of_egi`
- `overall_cap_rate`
- `noi_per_sf`
- `noi_per_unit`

### Income Data

- `potential_gross_income`
- `vacancy`
- `effective_gross_income`
- `expenses`
- `net_operating_income`

### Property-Type Applicability Notes

- FIELD: Unit type, number of units, unit size, unit amenities, average unit
  size, sale price per unit, expenses per unit, and NOI per unit are most
  relevant to multifamily, self-storage, hospitality, mobile home parks, or
  other unit-based properties.
- FIELD: Land size, zoning, topography, utilities, shape, flood hazard, access,
  and visibility are relevant across many types but become primary fields for
  land comps.
- FIELD: Single-tenant and multi-tenant should probably be occupancy or tenancy
  structure fields, not separate unrelated booleans.
- FIELD: Cash equivalent price and adjusted sale price should be preserved
  separately from raw sale price.
- CALC: Indicator fields should generally be calculated from raw facts where
  possible, while still allowing an appraiser-entered override or reconciled
  value when the source reports a different figure.
- QUESTION: Should `record_id` be an internal database ID only, or should the
  UI also support a human comp number such as Sale 1, Sale 2, or an appraiser
  file/reference ID?
- QUESTION: Which property types should control which fields are required,
  optional, hidden, or merely warned?

## Record Status

Manual comps should support these statuses:

- `draft`: incomplete or still being researched; excluded from formal reviewed
  search and report use.
- `confirmed`: reviewed by the appraiser; included in reviewed comp search and
  report/export workflows.
- `rejected`: known bad, duplicate, or not useful; retained only if audit
  history is needed.
- `archived`: no longer commonly used but not wrong.

Open questions:

- QUESTION: Should a confirmed comp be directly editable, or should edits create
  a revision record?
- QUESTION: Should rejected manual comps be stored at all for v1?

## Sale Comp Fields

### Property Identity

Candidate fields:

- `address_street`
- `address_city`
- `address_county`
- `address_state`
- `address_zip`
- `latitude`
- `longitude`
- `parcel_id`
- `property_name`
- `property_type`
- `property_subtype`
- `submarket`
- `market_area`
- `record_id`

Required before confirmation:

- REQUIRED: Address or a clear property/location identifier.
- REQUIRED: City/state or market area.
- REQUIRED: Property type.

Derek notes:

- FIELD:

### Physical Characteristics

Candidate fields:

- `gba_sf`
- `nla_sf`
- `land_size`
- `site_area_sf`
- `site_area_acres`
- `year_built`
- `year_renovated`
- `building_age`
- `stories`
- `building_type`
- `construction_type`
- `roof_type`
- `foundation`
- `electrical`
- `hvac`
- `condition`
- `quality`
- `zoning`
- `flood_zone`
- `flood_hazard`
- `topography`
- `utilities`
- `shape`
- `access`
- `visibility`
- `parking_spaces`
- `parking_ratio`
- `occupancy_pct`
- `single_tenant`
- `multi_tenant`
- `unit_type`
- `number_of_units`
- `unit_size`
- `unit_amenities`

Potential calculations:

- CALC: `site_area_acres = site_area_sf / 43560`
- CALC: `building_age = effective_year - year_built`
- CALC: `land_to_building_ratio = site_area_sf / gba_sf`
- CALC: `floor_area_ratio = gba_sf / site_area_sf`
- CALC: `parking_ratio = parking_spaces / (gba_sf / 1000)`
- CALC: `average_unit_size = gba_sf / number_of_units`

Derek notes:

- FIELD:
- CALC:

### Transaction Details

Candidate fields:

- `sale_price`
- `cash_equivalent_price`
- `adjusted_sale_price`
- `sale_date`
- `recording_date`
- `deed_ref`
- `deed_book_page`
- `instrument_number`
- `grantor`
- `grantee`
- `buyer_type`
- `seller_type`
- `property_rights`
- `financing_terms`
- `conditions_of_sale`
- `sale_status`
- `verification_source`
- `verification_date`
- `verification_notes`

Required before confirmation:

- REQUIRED: Sale price.
- REQUIRED: Sale date or clearly marked pending/under-contract status.
- REQUIRED: Verification source.

Potential calculations:

- CALC: `price_per_gba_sf = sale_price / gba_sf`
- CALC: `price_per_nla_sf = sale_price / nla_sf`
- CALC: `price_per_site_sf = sale_price / site_area_sf`
- CALC: `price_per_acre = sale_price / site_area_acres`
- CALC: `sale_price_per_unit = sale_price / number_of_units`
- CALC: `months_since_sale = months_between(effective_date, sale_date)`

Derek notes:

- FIELD:
- CALC:

### Income and Capitalization

Candidate fields:

- `noi`
- `potential_gross_income`
- `vacancy`
- `effective_gross_income`
- `expenses`
- `noi_source`
- `noi_period`
- `noi_per_sf`
- `noi_per_unit`
- `cap_rate`
- `occupancy_at_sale`
- `expense_ratio`
- `pgi`
- `egi`
- `total_expenses`
- `expenses_per_sf`
- `expenses_per_unit`
- `expenses_as_pct_of_pgi`
- `expenses_as_pct_of_egi`
- `pgim`
- `egim`

Potential calculations:

- CALC: `cap_rate = noi / sale_price`
- CALC: `noi = sale_price * cap_rate`
- CALC: `noi_per_sf = noi / gba_sf` or `noi / nla_sf`
- CALC: `noi_per_unit = noi / number_of_units`
- CALC: `expense_ratio = total_expenses / egi`
- CALC: `pgim = sale_price / potential_gross_income`
- CALC: `egim = sale_price / effective_gross_income`
- CALC: `expenses_per_sf = expenses / gba_sf` or `expenses / nla_sf`
- CALC: `expenses_per_unit = expenses / number_of_units`
- CALC: `expenses_as_pct_of_pgi = expenses / potential_gross_income`
- CALC: `expenses_as_pct_of_egi = expenses / effective_gross_income`

Open questions:

- QUESTION: When both entered and calculated values disagree, should the UI warn
  or preserve both?

Derek notes:

- FIELD:
- CALC:

### Adjustments and Analysis

Candidate fields:

- `location_adjustment`
- `property_rights_adjustment`
- `financing_adjustment`
- `conditions_of_sale_adjustment`
- `market_conditions_adjustment`
- `size_adjustment`
- `age_condition_adjustment`
- `quality_adjustment`
- `economic_characteristics_adjustment`
- `other_adjustments`
- `net_adjustment`
- `gross_adjustment`
- `adjusted_price`
- `adjusted_price_per_sf`

Potential calculations:

- CALC: `adjusted_price = sale_price * (1 + net_adjustment)`
- CALC: `adjusted_price_per_sf = adjusted_price / selected_area`
- CALC: `gross_adjustment = sum(abs(each_adjustment))`

Derek notes:

- FIELD:
- CALC:

## Lease Comp Fields

### Property and Suite Identity

Candidate fields:

- `address_street`
- `address_city`
- `address_county`
- `address_state`
- `address_zip`
- `property_name`
- `property_type`
- `property_subtype`
- `submarket`
- `suite`
- `floor`
- `space_type`
- `tenant_name`
- `tenant_use`

Required before confirmation:

- REQUIRED: Address or property identifier.
- REQUIRED: Tenant or anonymous tenant label.
- REQUIRED: Property type.

Derek notes:

- FIELD:

### Lease Terms

Candidate fields:

- `lease_date`
- `commencement_date`
- `lease_expiration`
- `term_months`
- `term_years`
- `sf_leased`
- `base_rent_psf`
- `base_rent_monthly`
- `base_rent_annual`
- `rent_structure`
- `expense_stop_psf`
- `reimbursement_structure`
- `lease_type`
- `renewal_options`
- `escalations`
- `free_rent_months`
- `ti_allowance_psf`
- `tenant_improvement_notes`
- `landlord_work`

Required before confirmation:

- REQUIRED: Leased area.
- REQUIRED: Base rent or enough rent data to calculate it.
- REQUIRED: Rent structure.
- REQUIRED: Lease date or commencement date.

Potential calculations:

- CALC: `base_rent_annual = base_rent_psf * sf_leased`
- CALC: `base_rent_monthly = base_rent_annual / 12`
- CALC: `base_rent_psf = base_rent_annual / sf_leased`
- CALC: `term_months = months_between(commencement_date, lease_expiration)`
- CALC: `term_years = term_months / 12`
- CALC: `free_rent_value = base_rent_monthly * free_rent_months`
- CALC: `effective_rent_psf = adjusted_total_rent / term_years / sf_leased`

Derek notes:

- FIELD:
- CALC:

### Lease Verification

Candidate fields:

- `verification_source`
- `verification_date`
- `verification_notes`
- `source_document`
- `broker_contact`
- `confidentiality_level`

Derek notes:

- FIELD:

## Shared Attachment Requirements

Manual comps should support:

- property photos;
- aerials or maps;
- broker flyers;
- deed/recording screenshots;
- rent roll pages;
- lease abstracts;
- verification notes;
- source URLs;
- PDF/image attachments.

Open questions:

- QUESTION: Should attachments be stored only as local file links, copied into
  `.local`, or both?
- QUESTION: Should every confirmed comp require at least one verification note
  or attachment?

Derek notes:

- WORKFLOW:

## UI/UX Requirements

The manual comp UI should eventually include:

- top-level Sale/Lease selector;
- clear sections rather than one long undifferentiated form;
- calculated summary panel that updates before save;
- required-field indicators;
- warnings for suspicious values;
- duplicate detection before save;
- Save Draft and Confirm buttons;
- edit existing comp workflow;
- attach photo/source workflow from the same detail view;
- search/select existing property to avoid duplicate property rows;
- compact table view for browse/search;
- detail panel for review/edit.

Preferred sale comp layout:

1. Property
2. Physical
3. Transaction
4. Income
5. Adjustments
6. Verification
7. Attachments
8. Calculated Summary

Preferred lease comp layout:

1. Property/Suite
2. Tenant
3. Lease Terms
4. Economics
5. Concessions/Escalations
6. Verification
7. Attachments
8. Calculated Summary

Derek notes:

- UI:
- WORKFLOW:

## Validation Rules

Potential validation rules:

- VALIDATION: Dates should be valid ISO dates after normalization.
- VALIDATION: Money and area fields should be positive numbers.
- VALIDATION: Cap rates should usually be between 0% and 20%, with warnings
  outside that range rather than automatic rejection.
- VALIDATION: Sale price with no area should warn because price/SF cannot be
  calculated.
- VALIDATION: Lease rent with no area should warn because rent/SF cannot be
  calculated.
- VALIDATION: Confirmed records should require verification source or notes.
- VALIDATION: Potential duplicates should show before save.

Derek notes:

- VALIDATION:

## Search and Browse Requirements

Search should eventually support:

- sale vs lease;
- property type/subtype;
- city/county/submarket;
- sale or lease date range;
- price/rent range;
- size range;
- cap rate range;
- tenant/use;
- verification/source type;
- draft vs confirmed status;
- attached photos yes/no;
- text search across address, parties, tenant, notes.

Derek notes:

- SEARCH:

## Export and Report Requirements

Manual comps should feed:

- reviewed comp database search;
- CSV export;
- `comp_data` workbook export;
- sales comparison adjustment grid;
- lease/rent analysis workflows;
- Word report comp pages;
- future dashboards and market analysis.

Open questions:

- QUESTION: Which calculated fields should be stored in SQLite vs recalculated
  on demand?
- QUESTION: Which fields need to map directly to current workbook/report
  columns?

Derek notes:

- EXPORT:

## Implementation Slices

Recommended build order:

1. Sale comp field/calculation contract.
2. Pure calculation module with tests.
3. Database support for draft vs confirmed manual comps.
4. Redesigned sale comp entry UI.
5. Sale comp browse/edit/detail UI.
6. Lease comp field/calculation contract.
7. Lease calculation module with tests.
8. Redesigned lease comp entry UI.
9. Better duplicate/property matching.
10. Attachment workflow inside comp detail pages.

## Inbox

Add anything here if you are not sure where it belongs.

- 
