"""Manual comparable normalization, calculations, and validation."""

import datetime
import re

from comparable_contract import normalize_data


PROPERTY_TYPES = (
    ("office", "Office"),
    ("retail", "Retail"),
    ("retail_service", "Retail-Service"),
    ("medical_office", "Medical Office"),
    ("industrial", "Industrial"),
    ("multifamily", "Multifamily"),
    ("hospitality", "Hospitality"),
    ("self_storage", "Self-Storage"),
    ("land", "Land"),
    ("religious_facility", "Religious Facility"),
    ("special_purpose", "Special Purpose"),
)
PROPERTY_TYPE_VALUES = frozenset(value for value, _label in PROPERTY_TYPES)
PROPERTY_TYPE_LABELS = {value: label for value, label in PROPERTY_TYPES}
PROPERTY_TYPE_BY_LABEL = {label.casefold(): value for value, label in PROPERTY_TYPES}

DROPDOWNS = {
    "condition": (
        "Excellent",
        "Good",
        "Average",
        "Fair",
        "Poor",
        "Shell",
        "Proposed / Under Construction",
        "Other",
    ),
    "quality": (
        "Class A",
        "Class B",
        "Class C",
        "Economy",
        "Special Purpose",
        "Other",
    ),
    "verification_source": (
        "Buyer",
        "Seller",
        "Broker",
        "Appraiser Files",
        "Public Records",
        "Deed / Recorded Instrument",
        "Costar / Third-Party Database",
        "MLS / Listing",
        "Property Manager",
        "Owner",
        "Confidential Source",
        "Other",
    ),
    "sale_status": (
        "Closed",
        "Under Contract",
        "Listing",
        "Pending",
        "Expired Listing",
        "Withdrawn",
        "Not Applicable",
    ),
    "property_rights": (
        "Fee Simple",
        "Leased Fee",
        "Leasehold",
        "Partial Interest",
        "Easement / Encumbered",
        "Other",
    ),
    "conditions_of_sale": (
        "Arm's Length",
        "REO / Distressed",
        "Related Party",
        "Portfolio Sale",
        "Court Ordered",
        "1031 Exchange",
        "Sale-Leaseback",
        "Assemblage",
        "Partial Interest",
        "Other",
    ),
    "financing_terms": (
        "Cash Equivalent",
        "Conventional",
        "Seller Financing",
        "Assumed Debt",
        "Below-Market Financing",
        "Above-Market Financing",
        "Unknown",
        "Other",
    ),
    "rent_structure": (
        "NNN",
        "Modified Gross",
        "Full Service",
        "Gross",
        "Industrial Gross",
        "Percentage Rent",
        "Ground Lease",
        "Other",
    ),
    "tenant_use": (
        "Office",
        "Medical",
        "Retail",
        "Restaurant",
        "Service Retail",
        "Warehouse",
        "Manufacturing",
        "Flex",
        "Residential",
        "Storage",
        "Hospitality",
        "Religious / Assembly",
        "Other",
    ),
}

NUMERIC_FIELDS = frozenset({
    "adjusted_sale_price",
    "adr",
    "base_rent_annual",
    "base_rent_monthly",
    "base_rent_psf",
    "cap_rate",
    "cash_equivalent_price",
    "climate_controlled_sf",
    "economic_occupancy",
    "effective_gross_income",
    "egi",
    "expense_ratio",
    "expense_stop_psf",
    "expenses",
    "free_rent_months",
    "gba_sf",
    "land_size",
    "nla_sf",
    "noi",
    "noi_per_sf",
    "non_climate_sf",
    "number_of_units",
    "occupancy",
    "occupancy_at_sale",
    "parking_spaces",
    "physical_occupancy",
    "pgi",
    "potential_gross_income",
    "price_per_sf",
    "rentable_sf",
    "revpar",
    "room_count",
    "room_revenue",
    "sale_price",
    "seating_capacity",
    "sf_leased",
    "site_area_acres",
    "site_area_sf",
    "stories",
    "term_months",
    "term_years",
    "ti_allowance_psf",
    "total_expenses",
    "usable_land_area",
    "vacancy",
    "year_built",
    "year_renovated",
})
RATE_FIELDS = frozenset({
    "cap_rate",
    "economic_occupancy",
    "expense_ratio",
    "occupancy",
    "occupancy_at_sale",
    "physical_occupancy",
    "vacancy",
})
DATE_FIELDS = frozenset({
    "commencement_date",
    "lease_date",
    "lease_expiration",
    "recording_date",
    "sale_date",
    "verification_date",
})
STATE_FIELDS = frozenset({"address_state"})
DENOMINATOR_FIELDS = (
    "gba_sf",
    "nla_sf",
    "rentable_sf",
    "sf_leased",
    "site_area_sf",
    "site_area_acres",
    "number_of_units",
    "room_count",
    "seating_capacity",
)


def _blank(value):
    return value in (None, "")


def _number(value):
    if _blank(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    text = re.sub(r"[$,%]", "", text)
    text = re.sub(
        r"\s*(sf|sqft|sq\.?\s*ft\.?|acres?|units?|rooms?|spaces?)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _date(value):
    if _blank(value):
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = " ".join(str(value).strip().split())
    if text.casefold() in {"n/a", "na", "none", "not applicable", "-"}:
        return None
    for date_format in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return text


def _ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _round(value, digits=4):
    return round(value, digits) if value is not None else None


def _coalesce(data, *fields):
    for field in fields:
        value = data.get(field)
        if value not in (None, ""):
            return value
    return None


def _months_between(start, end):
    if not start or not end:
        return None
    try:
        start_date = datetime.date.fromisoformat(start)
        end_date = datetime.date.fromisoformat(end)
    except ValueError:
        return None
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month


def normalize_manual_comp_data(data):
    """Normalize manual comp values beyond the narrow extraction contract."""
    normalized = normalize_data(data or {})
    for key, value in dict(data or {}).items():
        if key in NUMERIC_FIELDS:
            parsed = _number(value)
            if key in RATE_FIELDS and parsed is not None and parsed > 1:
                parsed /= 100
            normalized[key] = parsed
        elif key in DATE_FIELDS:
            normalized[key] = _date(value)
        elif key in STATE_FIELDS:
            text = " ".join(str(value).strip().split()) if value is not None else ""
            normalized[key] = text.upper() if text else None
        elif value is not None:
            text = " ".join(str(value).strip().split())
            normalized[key] = text or None
    property_type = normalized.get("property_type")
    if property_type:
        normalized["property_type"] = normalize_property_type(property_type)
    return normalized


def normalize_property_type(value):
    if not value:
        return None
    text = str(value).strip()
    key = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return PROPERTY_TYPE_BY_LABEL.get(text.casefold(), key)


def calculate_sale_indicators(data, effective_date=None):
    """Return calculated sale indicators from normalized manual comp data."""
    data = normalize_manual_comp_data(data)
    calc = {}
    sale_price = data.get("adjusted_sale_price") or data.get("sale_price")
    gba_sf = data.get("gba_sf")
    nla_sf = data.get("nla_sf")
    site_area_sf = data.get("site_area_sf")
    site_area_acres = data.get("site_area_acres")
    units = data.get("number_of_units")
    pgi = _coalesce(data, "potential_gross_income", "pgi")
    egi = _coalesce(data, "effective_gross_income", "egi")
    expenses = _coalesce(data, "expenses", "total_expenses")
    noi = data.get("noi")
    cap_rate = data.get("cap_rate")

    if site_area_sf is None and site_area_acres:
        site_area_sf = site_area_acres * 43560
        calc["site_area_sf"] = _round(site_area_sf, 2)
    if site_area_acres is None and site_area_sf:
        site_area_acres = site_area_sf / 43560
        calc["site_area_acres"] = _round(site_area_acres, 4)

    calc["price_per_gba_sf"] = _round(_ratio(sale_price, gba_sf), 2)
    calc["price_per_nla_sf"] = _round(_ratio(sale_price, nla_sf), 2)
    calc["price_per_site_sf"] = _round(_ratio(sale_price, site_area_sf), 2)
    calc["price_per_acre"] = _round(_ratio(sale_price, site_area_acres), 2)
    calc["sale_price_per_unit"] = _round(_ratio(sale_price, units), 2)
    calc["land_to_building_ratio"] = _round(_ratio(site_area_sf, gba_sf), 4)
    calc["floor_area_ratio"] = _round(_ratio(gba_sf, site_area_sf), 4)
    calc["average_unit_size"] = _round(_ratio(gba_sf, units), 2)

    if calc["price_per_gba_sf"] is not None:
        calc["price_per_sf"] = calc["price_per_gba_sf"]
        calc["price_per_sf_basis"] = "gba_sf"
    elif calc["price_per_nla_sf"] is not None:
        calc["price_per_sf"] = calc["price_per_nla_sf"]
        calc["price_per_sf_basis"] = "nla_sf"
    elif calc["price_per_site_sf"] is not None:
        calc["price_per_sf"] = calc["price_per_site_sf"]
        calc["price_per_sf_basis"] = "site_area_sf"

    if noi is None and sale_price and cap_rate is not None:
        noi = sale_price * cap_rate
        calc["noi"] = _round(noi, 2)
    if cap_rate is None and noi is not None and sale_price:
        cap_rate = noi / sale_price
        calc["cap_rate"] = _round(cap_rate, 6)

    calc["noi_per_sf"] = _round(_ratio(noi, gba_sf or nla_sf), 2)
    calc["noi_per_unit"] = _round(_ratio(noi, units), 2)
    calc["pgim"] = _round(_ratio(sale_price, pgi), 4)
    calc["egim"] = _round(_ratio(sale_price, egi), 4)
    calc["expenses_per_sf"] = _round(_ratio(expenses, gba_sf or nla_sf), 2)
    calc["expenses_per_unit"] = _round(_ratio(expenses, units), 2)
    calc["expenses_as_pct_of_pgi"] = _round(_ratio(expenses, pgi), 6)
    calc["expenses_as_pct_of_egi"] = _round(_ratio(expenses, egi), 6)
    calc["expense_ratio"] = calc["expenses_as_pct_of_egi"]

    normalized_effective = _date(effective_date) if effective_date else None
    months = _months_between(data.get("sale_date"), normalized_effective)
    if months is not None:
        calc["months_since_sale"] = months

    return {key: value for key, value in calc.items() if value is not None}


def calculate_lease_indicators(data):
    """Return calculated lease indicators from normalized manual lease data."""
    data = normalize_manual_comp_data(data)
    calc = {}
    sf_leased = data.get("sf_leased")
    rent_psf = data.get("base_rent_psf")
    monthly = data.get("base_rent_monthly")
    annual = data.get("base_rent_annual")

    if annual is None and rent_psf is not None and sf_leased:
        annual = rent_psf * sf_leased
        calc["base_rent_annual"] = _round(annual, 2)
    if annual is None and monthly is not None:
        annual = monthly * 12
        calc["base_rent_annual"] = _round(annual, 2)
    if monthly is None and annual is not None:
        monthly = annual / 12
        calc["base_rent_monthly"] = _round(monthly, 2)
    if rent_psf is None and annual is not None and sf_leased:
        rent_psf = annual / sf_leased
        calc["base_rent_psf"] = _round(rent_psf, 2)

    calc["rent_psf_year"] = _round(rent_psf, 2)
    calc["rent_psf_month"] = _round(rent_psf / 12, 4) if rent_psf is not None else None

    term_months = data.get("term_months")
    if term_months is None:
        start_date = data.get("commencement_date") or data.get("lease_date")
        term_months = _months_between(start_date, data.get("lease_expiration"))
        if term_months is not None:
            calc["term_months"] = term_months
    term_years = data.get("term_years")
    if term_years is None and term_months:
        term_years = term_months / 12
        calc["term_years"] = _round(term_years, 4)

    free_rent_months = data.get("free_rent_months")
    free_rent_value = monthly * free_rent_months if monthly and free_rent_months else None
    calc["free_rent_value"] = _round(free_rent_value, 2)
    ti_total = (
        data.get("ti_allowance_psf") * sf_leased
        if data.get("ti_allowance_psf") is not None and sf_leased
        else None
    )
    calc["ti_allowance_total"] = _round(ti_total, 2)

    if annual is not None and term_years and sf_leased:
        gross_rent = annual * term_years
        concessions = (free_rent_value or 0) + (ti_total or 0)
        effective_total = max(gross_rent - concessions, 0)
        calc["effective_rent_psf"] = _round(effective_total / term_years / sf_leased, 2)

    return {key: value for key, value in calc.items() if value is not None}


def validate_manual_comp(record_kind, data, *, status="draft", effective_date=None):
    """Validate manual comp data for draft/confirmed workflow."""
    if record_kind not in {"sale", "lease"}:
        return {"errors": [f"Unsupported record_kind: {record_kind!r}."], "warnings": []}

    data = normalize_manual_comp_data(data)
    calculations = (
        calculate_sale_indicators(data, effective_date=effective_date)
        if record_kind == "sale"
        else calculate_lease_indicators(data)
    )
    errors = []
    warnings = []
    status = status or "draft"
    if status not in {"draft", "confirmed", "rejected", "archived"}:
        errors.append(f"Unsupported status: {status!r}.")

    property_type = data.get("property_type")
    if property_type and property_type not in PROPERTY_TYPE_VALUES:
        warnings.append(f"Unknown property_type: {property_type!r}.")

    for field in DATE_FIELDS & set(data):
        value = data.get(field)
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
            errors.append(f"{field} must be ISO YYYY-MM-DD, got {value!r}.")

    if status == "confirmed":
        if not property_type:
            errors.append("property_type is required to confirm.")
        if not _has_location(data):
            errors.append("address or usable location identifier is required to confirm.")
        if record_kind == "sale":
            _validate_confirmed_sale(data, errors)
        else:
            _validate_confirmed_lease(data, errors)

    _add_common_warnings(record_kind, data, calculations, warnings)
    return {
        "errors": errors,
        "warnings": warnings,
        "calculations": calculations,
        "data": data,
    }


def evaluate_manual_comp(record_kind, data, *, status="draft", effective_date=None):
    """Normalize, calculate, and validate a manual comp in one call."""
    return validate_manual_comp(
        record_kind,
        data,
        status=status,
        effective_date=effective_date,
    )


def _has_location(data):
    return any(
        not _blank(data.get(field))
        for field in (
            "address_street",
            "property_name",
            "parcel_id",
            "parcel_numbers",
            "latitude",
            "longitude",
            "market_area",
        )
    )


def _has_denominator(data):
    return any(data.get(field) not in (None, "", 0) for field in DENOMINATOR_FIELDS)


def _validate_confirmed_sale(data, errors):
    if data.get("sale_price") in (None, "", 0):
        errors.append("sale_price is required to confirm.")
    if not data.get("sale_date") and not data.get("sale_status"):
        errors.append("sale_date or sale_status is required to confirm.")
    if not data.get("verification_source"):
        errors.append("verification_source is required to confirm.")
    if not _has_denominator(data):
        errors.append("At least one usable comparison denominator is required to confirm.")


def _validate_confirmed_lease(data, errors):
    if data.get("sf_leased") in (None, "", 0):
        errors.append("sf_leased is required to confirm a lease comp.")
    if not any(data.get(field) not in (None, "", 0) for field in (
        "base_rent_psf",
        "base_rent_monthly",
        "base_rent_annual",
    )):
        errors.append("base rent is required to confirm a lease comp.")
    if not data.get("rent_structure"):
        errors.append("rent_structure is required to confirm a lease comp.")
    if not data.get("lease_date") and not data.get("commencement_date"):
        errors.append("lease_date or commencement_date is required to confirm a lease comp.")


def _add_common_warnings(record_kind, data, calculations, warnings):
    if not data.get("verification_notes"):
        warnings.append("verification_notes are recommended.")
    if not any(data.get(field) for field in ("source_attachment", "source_url", "has_attachment")):
        warnings.append("A source attachment or source URL is recommended.")
    if not _has_denominator(data):
        warnings.append("No usable comparison denominator is present.")

    cap_rate = data.get("cap_rate") or calculations.get("cap_rate")
    if cap_rate is not None and (cap_rate < 0 or cap_rate > 0.20):
        warnings.append("cap_rate is outside the typical 0% to 20% review range.")

    income_present = any(data.get(field) not in (None, "", 0) for field in (
        "noi",
        "potential_gross_income",
        "effective_gross_income",
        "expenses",
        "pgi",
        "egi",
    ))
    if income_present and data.get("occupancy_at_sale") in (None, ""):
        warnings.append("occupancy_at_sale is recommended when income data is present.")

    if record_kind == "sale":
        _warn_if_mismatch(data, calculations, "price_per_sf", warnings)
        _warn_if_mismatch(data, calculations, "cap_rate", warnings, tolerance=0.0005)
        _warn_if_mismatch(data, calculations, "noi_per_sf", warnings)
    else:
        _warn_if_mismatch(data, calculations, "base_rent_psf", warnings)
        _warn_if_mismatch(data, calculations, "base_rent_monthly", warnings)


def _warn_if_mismatch(data, calculations, field, warnings, tolerance=0.01):
    entered = data.get(field)
    calculated = calculations.get(field)
    if entered is None or calculated is None:
        return
    if abs(entered - calculated) > tolerance:
        warnings.append(f"{field} differs from the calculated value.")
