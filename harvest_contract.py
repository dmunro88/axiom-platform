"""Canonical contracts for historical assignment and financial harvesting."""

import copy
import datetime
import hashlib
import json
import re
from pathlib import Path

from comparable_contract import source_metadata


SCHEMA_VERSION = "1.0.0"
ASSIGNMENT_CONTRACT_ID = "axiom.assignment.conclusion"
INCOME_CONTRACT_ID = "axiom.income.snapshot"
RENT_ROLL_CONTRACT_ID = "axiom.rent_roll.entry"
EXPENSE_CONTRACT_ID = "axiom.operating_expense.line"
OBSERVATION_CONTRACT_ID = "axiom.market.observation"
ARTIFACT_CONTRACT_ID = "axiom.source.artifact"
REVIEW_STATUSES = frozenset({"unreviewed", "confirmed", "rejected"})
CONFIDENCE_VALUES = frozenset({"high", "medium", "low", "unknown"})

ASSIGNMENT_MONEY_FIELDS = {
    "sca_value",
    "ia_value",
    "ca_value",
    "reconciled_value",
}
INCOME_MONEY_FIELDS = {
    "pgi",
    "egi",
    "total_expenses",
    "noi",
}
INCOME_RATE_FIELDS = {
    "vacancy_pct",
    "expense_ratio",
    "cap_rate_applied",
    "market_cap_rate_low",
    "market_cap_rate_high",
}
RENT_ROLL_NUMBER_FIELDS = {
    "sf_leased",
    "monthly_rent",
    "annual_rent",
    "rent_psf",
}
RENT_ROLL_DATE_FIELDS = {"lease_start", "lease_end", "as_of_date"}
EXPENSE_NUMBER_FIELDS = {"amount", "amount_per_sf"}


def _text(value):
    if value is None:
        return None
    result = " ".join(str(value).strip().split())
    return result or None


def _number(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[$,%]", "", str(value)).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = _text(value)
    for date_format in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return text


def normalize_assignment_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in ASSIGNMENT_MONEY_FIELDS:
            normalized[key] = _number(value)
        elif key in {"report_date", "effective_date"}:
            normalized[key] = _date(value)
        else:
            normalized[key] = _text(value)
    return normalized


def normalize_income_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in INCOME_MONEY_FIELDS:
            normalized[key] = _number(value)
        elif key in INCOME_RATE_FIELDS:
            parsed = _number(value)
            normalized[key] = parsed / 100 if parsed is not None and parsed > 1 else parsed
        elif key == "period_year":
            parsed = _number(value)
            normalized[key] = int(parsed) if parsed is not None else None
        elif key == "period_type":
            text = (_text(value) or "").casefold().replace("-", " ")
            normalized[key] = {
                "pro forma": "proforma",
                "projected": "proforma",
            }.get(text, text or None)
        else:
            normalized[key] = _text(value)
    return normalized


def normalize_rent_roll_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in RENT_ROLL_NUMBER_FIELDS:
            normalized[key] = _number(value)
        elif key in RENT_ROLL_DATE_FIELDS:
            normalized[key] = _date(value)
        else:
            normalized[key] = _text(value)
    return normalized


def normalize_expense_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in EXPENSE_NUMBER_FIELDS:
            normalized[key] = _number(value)
        elif key == "period_year":
            parsed = _number(value)
            normalized[key] = int(parsed) if parsed is not None else None
        elif key == "period_type":
            text = (_text(value) or "").casefold().replace("-", " ")
            normalized[key] = {
                "pro forma": "proforma",
                "projected": "proforma",
            }.get(text, text or None)
        else:
            normalized[key] = _text(value)
    return normalized


def normalize_observation_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key == "effective_date":
            normalized[key] = _date(value)
        else:
            normalized[key] = _text(value)
    return normalized


def normalize_artifact_data(data):
    normalized = {}
    for key, value in dict(data or {}).items():
        if key in {"artifact_size", "width_px", "height_px"}:
            parsed = _number(value)
            normalized[key] = int(parsed) if parsed is not None else None
        elif key == "effective_date":
            normalized[key] = _date(value)
        else:
            normalized[key] = _text(value)
    return normalized


def _identity_text(value):
    return re.sub(r"[^a-z0-9]+", " ", (_text(value) or "").casefold()).strip()


def _digest(values):
    payload = json.dumps(values, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assignment_identity(data, source_sha256=None):
    data = normalize_assignment_data(data)
    values = (
        _identity_text(data.get("file_no")),
        _identity_text(data.get("address_street")),
        data.get("effective_date") or "",
        data.get("reconciled_value"),
    )
    if not any(value not in ("", None) for value in values):
        values = ("source", source_sha256 or "")
    return _digest(values)


def income_identity(data, assignment_identity_key=None, source_sha256=None):
    data = normalize_income_data(data)
    return _digest((
        assignment_identity_key or source_sha256 or "",
        data.get("period_year"),
        data.get("period_type") or "",
        data.get("noi"),
    ))


def rent_roll_identity(data, assignment_identity_key=None, source_sha256=None):
    data = normalize_rent_roll_data(data)
    return _digest((
        assignment_identity_key or source_sha256 or "",
        data.get("as_of_date") or "",
        _identity_text(data.get("unit_id")),
        _identity_text(data.get("suite")),
        _identity_text(data.get("tenant_name")),
        data.get("lease_start") or "",
        data.get("lease_end") or "",
        data.get("sf_leased"),
    ))


def expense_identity(data, assignment_identity_key=None, source_sha256=None):
    data = normalize_expense_data(data)
    return _digest((
        assignment_identity_key or source_sha256 or "",
        data.get("period_year"),
        data.get("period_type") or "",
        _identity_text(data.get("category")),
        data.get("amount"),
    ))


def observation_identity(data, assignment_identity_key=None, source_sha256=None):
    data = normalize_observation_data(data)
    text_hash = hashlib.sha256(
        (data.get("text") or "").encode("utf-8")
    ).hexdigest()
    return _digest((
        assignment_identity_key or source_sha256 or "",
        data.get("effective_date") or "",
        _identity_text(data.get("category")),
        _identity_text(data.get("geography")),
        text_hash,
    ))


def artifact_identity(data, assignment_identity_key=None, source_sha256=None):
    data = normalize_artifact_data(data)
    return _digest((
        assignment_identity_key or source_sha256 or "",
        _identity_text(data.get("artifact_kind")),
        data.get("artifact_sha256") or "",
    ))


def _provenance(source_path, existing=None):
    provenance = dict(existing or {})
    if source_path and Path(source_path).is_file() and not provenance.get("source_sha256"):
        provenance.update(source_metadata(source_path))
    elif source_path:
        provenance.setdefault("source_path", str(source_path))
        provenance.setdefault("source_filename", Path(source_path).name)
    provenance.setdefault("extraction_method", "historical_report_extractor")
    return provenance


def validate_harvest_record(record):
    errors = []
    warnings = []
    kind = record.get("record_kind")
    data = record.get("data", {})
    if kind == "assignment":
        if not data.get("file_no") and not data.get("address_street"):
            warnings.append("file_no or address_street is recommended.")
        if not any(data.get(field) is not None for field in ASSIGNMENT_MONEY_FIELDS):
            warnings.append("At least one value conclusion is recommended.")
    elif kind == "income":
        if data.get("period_year") is None:
            warnings.append("period_year is recommended.")
        if data.get("noi") is None:
            warnings.append("noi is recommended.")
    elif kind == "rent_roll":
        if not any(data.get(field) for field in ("tenant_name", "unit_id", "suite")):
            errors.append("tenant_name, unit_id, or suite is required.")
        if data.get("sf_leased") is None:
            warnings.append("sf_leased is recommended.")
    elif kind == "expense":
        if not data.get("category"):
            errors.append("category is required.")
        if data.get("amount") is None:
            errors.append("amount is required.")
    elif kind == "observation":
        if not data.get("category"):
            errors.append("category is required.")
        if not data.get("title"):
            errors.append("title is required.")
        if len(data.get("text") or "") < 80:
            errors.append("text must contain at least 80 characters.")
        if not data.get("effective_date"):
            warnings.append("effective_date is recommended.")
    elif kind == "artifact":
        if not data.get("artifact_kind"):
            errors.append("artifact_kind is required.")
        if not re.fullmatch(r"[0-9a-f]{64}", data.get("artifact_sha256") or ""):
            errors.append("artifact_sha256 must be a SHA-256 hex digest.")
        if data.get("artifact_size") is None:
            errors.append("artifact_size is required.")
    else:
        errors.append(f"Unsupported harvest record_kind: {kind!r}.")
    for field in ("source_path", "source_sha256"):
        if not record.get("provenance", {}).get(field):
            errors.append(f"provenance.{field} is required.")
    status = record.get("review", {}).get("status", "unreviewed")
    if status not in REVIEW_STATUSES:
        errors.append(f"Invalid review status: {status!r}.")
    for field, confidence in record.get("confidence", {}).items():
        if confidence not in CONFIDENCE_VALUES:
            errors.append(f"confidence[{field}] has invalid value {confidence!r}.")
    return {"errors": errors, "warnings": warnings}


def _record(data, confidence, kind, source_path, existing=None, assignment_key=None):
    record = copy.deepcopy(existing or {})
    record["contract_id"] = {
        "assignment": ASSIGNMENT_CONTRACT_ID,
        "income": INCOME_CONTRACT_ID,
        "rent_roll": RENT_ROLL_CONTRACT_ID,
        "expense": EXPENSE_CONTRACT_ID,
        "observation": OBSERVATION_CONTRACT_ID,
        "artifact": ARTIFACT_CONTRACT_ID,
    }[kind]
    record["schema_version"] = SCHEMA_VERSION
    record["record_kind"] = kind
    normalizers = {
        "assignment": normalize_assignment_data,
        "income": normalize_income_data,
        "rent_roll": normalize_rent_roll_data,
        "expense": normalize_expense_data,
        "observation": normalize_observation_data,
        "artifact": normalize_artifact_data,
    }
    record["data"] = normalizers[kind](data)
    record["confidence"] = {
        key: value if value in CONFIDENCE_VALUES else "unknown"
        for key, value in dict(confidence or {}).items()
    }
    record["provenance"] = _provenance(
        source_path or record.get("provenance", {}).get("source_path"),
        record.get("provenance"),
    )
    if record.get("sheet"):
        locator = f"worksheet:{record['sheet']}"
        if record.get("source_row"):
            locator += f":row:{record['source_row']}"
        record["provenance"].setdefault("source_locator", locator)
    elif record.get("source_locator"):
        record["provenance"].setdefault(
            "source_locator",
            record["source_locator"],
        )
    identity_functions = {
        "assignment": lambda: assignment_identity(
            record["data"],
            record["provenance"].get("source_sha256"),
        ),
        "income": lambda: income_identity(
            record["data"],
            assignment_key,
            record["provenance"].get("source_sha256"),
        ),
        "rent_roll": lambda: rent_roll_identity(
            record["data"],
            assignment_key,
            record["provenance"].get("source_sha256"),
        ),
        "expense": lambda: expense_identity(
            record["data"],
            assignment_key,
            record["provenance"].get("source_sha256"),
        ),
        "observation": lambda: observation_identity(
            record["data"],
            assignment_key,
            record["provenance"].get("source_sha256"),
        ),
        "artifact": lambda: artifact_identity(
            record["data"],
            assignment_key,
            record["provenance"].get("source_sha256"),
        ),
    }
    record["identity_key"] = identity_functions[kind]()
    review = dict(record.get("review", {}))
    review.setdefault(
        "status",
        "confirmed" if record.get("reviewed") else "unreviewed",
    )
    record["review"] = review
    record["reviewed"] = review["status"] == "confirmed"
    record["validation"] = validate_harvest_record(record)
    return record


def canonicalize_harvest_records(result):
    """Attach canonical assignment/income envelopes to an extraction batch."""
    canonical = copy.deepcopy(result)
    narrative = canonical.get("narrative", {})
    narrative_data = dict(narrative.get("data", {}))
    narrative_confidence = dict(narrative.get("confidence", {}))
    metadata = canonical.get("folder_meta", {})
    existing_assignment = canonical.get("assignment_record")
    assignment_data = dict(
        (existing_assignment or {}).get("data", narrative_data)
    )
    if existing_assignment:
        narrative_confidence = existing_assignment.get(
            "confidence",
            narrative_confidence,
        )
    assignment_data["file_no"] = (
        assignment_data.get("file_no") or metadata.get("file_no")
    )
    if not assignment_data.get("address_city"):
        assignment_data["address_city"] = metadata.get("city")
    if not assignment_data.get("property_type"):
        assignment_data["property_type"] = metadata.get("property_type")
    approaches = [
        label
        for label, field in (
            ("SCA", "sca_value"),
            ("IA", "ia_value"),
            ("CA", "ca_value"),
        )
        if assignment_data.get(field) is not None
    ]
    if approaches:
        assignment_data["approaches"] = ",".join(approaches)

    assignment_source = (
        (existing_assignment or {}).get("provenance", {}).get("source_path")
        or canonical.get("assignment_source")
        or next(iter(canonical.get("sources", [])), None)
    )
    has_assignment = any(
        assignment_data.get(field) not in (None, "")
        for field in (
            "file_no",
            "address_street",
            "client",
            "effective_date",
            "report_date",
            "sca_value",
            "ia_value",
            "ca_value",
            "reconciled_value",
        )
    )
    canonical["assignment_record"] = (
        _record(
            assignment_data,
            narrative_confidence,
            "assignment",
            assignment_source,
            existing_assignment,
        )
        if has_assignment and assignment_source
        else None
    )

    raw_income = canonical.get("income_data") or {}
    existing_income = canonical.get("income_snapshot")
    if existing_income:
        income_data = dict(existing_income.get("data", {}))
        income_confidence = existing_income.get("confidence", {})
        income_source = existing_income.get("provenance", {}).get("source_path")
    elif "data" in raw_income:
        income_data = raw_income.get("data", {})
        income_confidence = raw_income.get("confidence", {})
        income_source = raw_income.get("source")
    else:
        income_data = raw_income
        income_confidence = {}
        income_source = None
    for field in ("market_cap_rate_low", "market_cap_rate_high"):
        if income_data and income_data.get(field) is None:
            income_data[field] = narrative_data.get(field)
    income_source = (
        (existing_income or {}).get("provenance", {}).get("source_path")
        or income_source
        or canonical.get("income_source")
        or assignment_source
    )
    canonical["income_snapshot"] = (
        _record(
            income_data,
            income_confidence,
            "income",
            income_source,
            existing_income,
            (
                canonical["assignment_record"]["identity_key"]
                if canonical.get("assignment_record")
                else None
            ),
        )
        if income_data and income_source
        else None
    )
    assignment_key = (
        canonical["assignment_record"]["identity_key"]
        if canonical.get("assignment_record")
        else None
    )
    for key, kind in (
        ("rent_roll_entries", "rent_roll"),
        ("expense_records", "expense"),
        ("market_observations", "observation"),
        ("artifacts", "artifact"),
    ):
        records = []
        identities = set()
        for raw_record in canonical.get(key, []):
            raw_data = dict(raw_record.get("data", {}))
            if kind == "observation":
                raw_data.setdefault(
                    "effective_date",
                    assignment_data.get("effective_date"),
                )
                raw_data.setdefault(
                    "geography",
                    assignment_data.get("address_city"),
                )
                raw_data.setdefault(
                    "property_type",
                    assignment_data.get("property_type"),
                )
            elif kind == "artifact":
                raw_data.setdefault(
                    "effective_date",
                    assignment_data.get("effective_date"),
                )
                raw_data.setdefault(
                    "geography",
                    assignment_data.get("address_city"),
                )
                raw_data.setdefault(
                    "property_type",
                    assignment_data.get("property_type"),
                )
            record = _record(
                raw_data,
                raw_record.get("confidence", {}),
                kind,
                (
                    raw_record.get("provenance", {}).get("source_path")
                    or raw_record.get("source")
                ),
                raw_record,
                assignment_key,
            )
            if record["identity_key"] in identities:
                existing = next(
                    item
                    for item in records
                    if item["identity_key"] == record["identity_key"]
                )
                alternate = {
                    "source_path": record.get("provenance", {}).get("source_path"),
                    "source_locator": record.get("provenance", {}).get("source_locator"),
                    "source_sha256": record.get("provenance", {}).get("source_sha256"),
                }
                existing.setdefault("alternate_provenance", []).append(alternate)
                continue
            records.append(record)
            identities.add(record["identity_key"])
        canonical[key] = records
    return canonical


def confirm_harvest_records(result, reviewer, reviewed_at):
    confirmed = canonicalize_harvest_records(result)
    records = [
        confirmed.get("assignment_record"),
        confirmed.get("income_snapshot"),
        *confirmed.get("rent_roll_entries", []),
        *confirmed.get("expense_records", []),
        *confirmed.get("market_observations", []),
        *confirmed.get("artifacts", []),
    ]
    for record in records:
        if not record:
            continue
        record["review"] = {
            "status": "confirmed",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "edits": record.get("review_edits", []),
        }
        record["reviewed"] = True
        record["validation"] = validate_harvest_record(record)
    return confirmed
