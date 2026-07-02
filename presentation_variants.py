"""Deterministic report-facing variants derived from canonical assignment facts."""


VARIANT_RULES = {
    "PROPERTY_CLASS_LOWER": {
        "source": "PROPERTY_CLASS",
        "transform": "lowercase",
    },
    "PROPERTY_SUBTYPE_LOWER": {
        "source": "PROPERTY_SUBTYPE_FULL",
        "transform": "lowercase",
    },
    "VALUE_INTEREST_LOWER": {
        "source": "VALUE_INTEREST",
        "transform": "lowercase",
    },
    "VALUE_WORDS_FORMAL": {
        "source": "VALUE_WORDS",
        "transform": "title_case",
    },
    "ZONING_CLASS_TABLE": {
        "source": "ZONING_CLASS",
        "transform": "identity",
    },
    "ZONING_CODE_TABLE": {
        "source": "ZONING_CODE",
        "transform": "identity",
    },
}


def _transform(value, transform):
    text = str(value).strip()
    if transform == "lowercase":
        return text.lower()
    if transform == "title_case":
        return text.title()
    if transform == "identity":
        return text
    raise ValueError(f"Unsupported presentation transform: {transform}")


def derive_presentation_variants(variables):
    """
    Return assignment variables with presentation variants refreshed.

    Existing legacy variant values remain usable when their canonical source is
    absent. When the canonical source is present, its deterministic derivation
    always wins so stale duplicate input cannot reach a report.
    """
    derived = dict(variables)
    for target, rule in VARIANT_RULES.items():
        source_value = derived.get(rule["source"])
        if source_value in (None, "", "None"):
            continue
        derived[target] = _transform(source_value, rule["transform"])
    return derived
