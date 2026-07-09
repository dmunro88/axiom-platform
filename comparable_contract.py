"""Versioned comparable-record normalization, validation, and identity."""

import copy
import datetime
import hashlib
import json
import re
from pathlib import Path


CONTRACT_ID = "axiom.comparable.record"
SCHEMA_VERSION = "1.0.0"
CONFIDENCE_VALUES = frozenset({"high", "medium", "low", "unknown"})
REVIEW_STATUSES = frozenset({"unreviewed", "confirmed", "rejected"})

SALE_REQUIRED = ("address_street", "sale_price")
SALE_RECOMMENDED = (
    "address_city",
    "sale_date",
    "gba_sf",
    "verification_source",
)
LEASE_REQUIRED = ("address_street", "base_rent_psf")
LEASE_RECOMMENDED = (
    "address_city",
    "tenant_name",
    "lease_date",
    "sf_leased",
    "rent_structure",
)

NUMERIC_FIELDS = frozenset({
    "gba_sf",
    "nla_sf",
    "site_area_sf",
    "year_built",
    "stories",
    "sale_price",
    "price_per_sf",
    "cap_rate",
    "noi",
    "noi_per_sf",
    "term_years",
    "sf_leased",
    "base_rent_psf",
    "base_rent_monthly",
    "expense_stop_psf",
    "ti_allowance_psf",
    "free_rent_months",
})
RATE_FIELDS = frozenset({"cap_rate"})
DATE_FIELDS = frozenset({"sale_date", "lease_date", "lease_expiration"})
STATE_FIELDS = frozenset({"address_state"})


def _normalized_text(value):
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _number(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[$,%]", "", str(value))
    text = re.sub(
        r"\s*(sf|sqft|sq\.?\s*ft\.?)\s*$",
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
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = _normalized_text(value)
    if text and text.casefold() in {"n/a", "na", "none", "not applicable", "-"}:
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


def normalize_data(data):
    """Normalize extracted values into canonical storage semantics."""
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in NUMERIC_FIELDS:
            parsed = _number(value)
            if key in RATE_FIELDS and parsed is not None and parsed > 1:
                parsed /= 100
            normalized[key] = parsed
        elif key in DATE_FIELDS:
            normalized[key] = _date(value)
        elif key in STATE_FIELDS:
            text = _normalized_text(value)
            normalized[key] = text.upper() if text else None
        else:
            normalized[key] = _normalized_text(value)
    return normalized


def _identity_text(value):
    text = _normalized_text(value) or ""
    text = text.casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def comparable_identity(record_kind, data):
    """Return a stable identity hash used to deduplicate across sources."""
    data = normalize_data(data)
    if record_kind == "sale":
        values = (
            _identity_text(data.get("address_street")),
            _identity_text(data.get("address_city")),
            data.get("sale_date") or "",
            data.get("sale_price"),
        )
    elif record_kind == "lease":
        values = (
            _identity_text(data.get("address_street")),
            _identity_text(data.get("address_city")),
            _identity_text(data.get("tenant_name")),
            data.get("lease_date") or "",
            data.get("sf_leased"),
            data.get("base_rent_psf"),
        )
    else:
        raise ValueError(f"Unsupported comparable record kind: {record_kind}")
    payload = json.dumps(values, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_metadata(source_path):
    """Return immutable provenance metadata for a source file."""
    path = Path(source_path)
    digest = hashlib.sha256()
    with open(path, "rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "source_path": str(path.resolve()),
        "source_filename": path.name,
        "source_sha256": digest.hexdigest(),
        "source_size": stat.st_size,
        "source_modified_ns": stat.st_mtime_ns,
    }


def validate_record(record):
    """Return ``{"errors": [], "warnings": []}`` for a record envelope."""
    errors = []
    warnings = []
    kind = record.get("record_kind")
    data = record.get("data", {})
    required = SALE_REQUIRED if kind == "sale" else LEASE_REQUIRED
    recommended = SALE_RECOMMENDED if kind == "sale" else LEASE_RECOMMENDED
    if kind not in {"sale", "lease"}:
        errors.append(f"Unsupported record_kind: {kind!r}.")
        return {"errors": errors, "warnings": warnings}

    for field in required:
        if data.get(field) in (None, ""):
            errors.append(f"{field} is required.")
    for field in recommended:
        if data.get(field) in (None, ""):
            warnings.append(f"{field} is recommended.")
    for field in DATE_FIELDS & set(data):
        value = data.get(field)
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
            errors.append(f"{field} must be ISO YYYY-MM-DD, got {value!r}.")
    for field, confidence in record.get("confidence", {}).items():
        if confidence not in CONFIDENCE_VALUES:
            errors.append(
                f"confidence[{field}] has invalid value {confidence!r}."
            )
    review_status = record.get("review", {}).get("status", "unreviewed")
    if review_status not in REVIEW_STATUSES:
        errors.append(f"Invalid review status: {review_status!r}.")
    provenance = record.get("provenance", {})
    for field in ("source_path", "source_sha256"):
        if not provenance.get(field):
            errors.append(f"provenance.{field} is required.")
    return {"errors": errors, "warnings": warnings}


def canonicalize_record(
    record,
    record_kind,
    source_path=None,
    review_status=None,
):
    """Upgrade a legacy extractor record to the versioned record envelope."""
    canonical = copy.deepcopy(record)
    canonical["contract_id"] = CONTRACT_ID
    canonical["schema_version"] = SCHEMA_VERSION
    canonical["record_kind"] = record_kind
    canonical["data"] = normalize_data(canonical.get("data", {}))
    canonical["confidence"] = {
        key: value if value in CONFIDENCE_VALUES else "unknown"
        for key, value in canonical.get("confidence", {}).items()
    }
    resolved_source = source_path or canonical.get("source")
    provenance = dict(canonical.get("provenance", {}))
    if (
        resolved_source
        and Path(resolved_source).is_file()
        and not provenance.get("source_sha256")
    ):
        provenance.update(source_metadata(resolved_source))
    elif resolved_source:
        provenance.setdefault("source_path", str(resolved_source))
    canonical["provenance"] = provenance
    if canonical.get("sheet"):
        canonical["provenance"].setdefault(
            "source_locator",
            f"worksheet:{canonical['sheet']}",
        )
    if canonical.get("confidence_source"):
        canonical["provenance"].setdefault(
            "extraction_method",
            canonical["confidence_source"],
        )
    else:
        canonical["provenance"].setdefault(
            "extraction_method",
            "structured_extractor",
        )
    canonical["source"] = provenance.get("source_path", resolved_source)
    canonical["identity_key"] = comparable_identity(
        record_kind,
        canonical["data"],
    )
    review = dict(canonical.get("review", {}))
    review["status"] = (
        review_status
        or review.get("status")
        or ("confirmed" if canonical.get("reviewed") else "unreviewed")
    )
    canonical["review"] = review
    canonical["reviewed"] = review["status"] == "confirmed"
    canonical["validation"] = validate_record(canonical)
    return canonical


def canonicalize_extraction_result(result):
    """Canonicalize every comp in an extracted assignment batch."""
    from harvest_contract import canonicalize_harvest_records

    canonical = copy.deepcopy(result)
    canonical["contract_id"] = "axiom.comparable.extraction_batch"
    canonical["schema_version"] = SCHEMA_VERSION
    canonical["comps"] = [
        canonicalize_record(
            record,
            "sale",
            source_path=record.get("source"),
        )
        for record in canonical.get("comps", [])
    ]
    canonical["lease_comps"] = [
        canonicalize_record(
            record,
            "lease",
            source_path=record.get("source"),
        )
        for record in canonical.get("lease_comps", [])
    ]
    return canonicalize_harvest_records(canonical)


def confirm_extraction_result(result, reviewer="user", reviewed_at=None):
    """Return a canonical batch with every retained record confirmed."""
    from harvest_contract import confirm_harvest_records

    confirmed = canonicalize_extraction_result(result)
    timestamp = reviewed_at or datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()
    for record in confirmed["comps"] + confirmed["lease_comps"]:
        edits = record.get("review_edits", [])
        record["review"] = {
            "status": "confirmed",
            "reviewer": reviewer,
            "reviewed_at": timestamp,
            "edits": edits,
        }
        record["reviewed"] = True
        record["validation"] = validate_record(record)
    confirmed = confirm_harvest_records(confirmed, reviewer, timestamp)
    confirmed["reviewed"] = True
    confirmed["review"] = {
        "status": "confirmed",
        "reviewer": reviewer,
        "reviewed_at": timestamp,
    }
    return confirmed
