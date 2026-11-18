import copy
from dataclasses import dataclass
from typing import Any

import pandas as pd
from fhirpathpy import evaluate

from fhir_prototype.bundle_index import BundleIndex, Resource
from fhir_prototype.dates import to_datetime


@dataclass
class MappingResult:
    facts: pd.DataFrame
    unmapped: pd.DataFrame


FACT_COLUMNS = [
    "resource_type",
    "resource_id",
    "patient_id",
    "encounter_id",
    "concept_cd",
    "modifier_cd",
    "start_date",
    "end_date",
    "valtype_cd",
    "tval_char",
    "nval_num",
    "units_cd",
]
FACT_RESOURCE_TYPES = ["Observation", "Procedure"]
EXCLUDED_STATUS = {"entered-in-error", "cancelled", "not-done"}
ALT_CODE_MODIFIER = "altCode"


def _device_category(resource: Resource, index: BundleIndex) -> str | None:
    if "device" not in resource:
        return None
    device = index.resolve(resource["device"]["reference"])
    return device.get("category")


def _profile(resource: Resource) -> str | None:
    return (resource.get("meta", {}).get("profile") or [None])[0]


def _first(resource: Resource, path: str | None) -> Any:
    """Return the first result of a FHIRPath expression, or None without path or match."""
    if not path:
        return None
    # evaluate adds type information to its input, so it works on a copy
    return next(iter(evaluate(copy.deepcopy(resource), path)), None)


def _row(resource: Resource, index: BundleIndex, rule: dict) -> dict:
    """Translate one resource into one fact row using its mapping rule."""
    return {
        "resource_type": resource["resourceType"],
        "resource_id": resource["id"],
        "patient_id": index.resolve(resource["subject"]["reference"])["id"],
        "encounter_id": index.resolve(resource["encounter"]["reference"])["id"],
        "concept_cd": rule.get("concept_cd"),
        "modifier_cd": "@",
        "start_date": _first(resource, rule.get("start")),
        "end_date": _first(resource, rule.get("end")),
        "valtype_cd": rule.get("valtype_cd"),
        "tval_char": None,
        "nval_num": _first(resource, rule.get("value")),
        "units_cd": _first(resource, rule.get("unit")),
        "expected_unit": rule.get("expected_unit"),
        "alt_codes": rule.get("alt_codes") or [],
    }


def _alt_code_facts(facts: pd.DataFrame) -> pd.DataFrame:
    """Return one modifier row per alternative code of each fact, without the value of the fact."""
    rows = facts.explode("alt_codes").dropna(subset="alt_codes")
    return rows.assign(
        modifier_cd=ALT_CODE_MODIFIER,
        valtype_cd="T",
        tval_char=rows["alt_codes"],
        nval_num=float("nan"),
        units_cd=None,
    )


def _split(facts: pd.DataFrame) -> MappingResult:
    """Separate the rows that cannot be imported and name the reason for each."""
    reason = pd.Series(None, index=facts.index, dtype=object)
    differs = facts["units_cd"].notna() & facts["expected_unit"].notna() & (facts["units_cd"] != facts["expected_unit"])
    reason[differs] = "unit differs from expected_unit"
    reason[(facts["valtype_cd"] == "N") & facts["nval_num"].isna()] = "no numeric value"
    reason[facts["concept_cd"].isna()] = "no concept in mapping"
    rejected = reason.notna()
    accepted = facts[~rejected]
    return MappingResult(
        facts=pd.concat([accepted, _alt_code_facts(accepted)], ignore_index=True)[FACT_COLUMNS],
        unmapped=facts.loc[rejected, FACT_COLUMNS].assign(reason=reason[rejected]),
    )


def build_facts(index: BundleIndex, mapping: list[dict]) -> MappingResult:
    """Translate the resources of a bundle into i2b2 facts as defined by the mapping."""
    rules = {(rule["profile"], rule.get("device_category")): rule for rule in mapping}
    rows = [
        _row(resource, index, rules.get((_profile(resource), _device_category(resource, index)), {}))
        for resource_type in FACT_RESOURCE_TYPES
        for resource in index.of_type(resource_type)
        if resource.get("status") not in EXCLUDED_STATUS
    ]
    facts = pd.DataFrame(rows, columns=FACT_COLUMNS + ["expected_unit", "alt_codes"])
    numeric = facts["valtype_cd"] == "N"
    facts["nval_num"] = pd.to_numeric(facts["nval_num"], errors="coerce").where(numeric)
    return _split(to_datetime(facts, ["start_date", "end_date"]))


def _resolve(resource: Resource, value: Any) -> Any:
    """Return a constant as is, or evaluate it as FHIRPath when it starts with @."""
    if isinstance(value, str) and value.startswith("@"):
        return _first(resource, value[1:])
    return value


def _values(resource: Resource, spec: dict) -> dict:
    """Resolve the value columns of one fact row from its part of the rule."""
    return {
        "valtype_cd": _resolve(resource, spec.get("valtype_cd")),
        "tval_char": _resolve(resource, spec.get("tval_char")),
        "nval_num": _resolve(resource, spec.get("nval_num")),
        "units_cd": _resolve(resource, spec.get("units_cd")),
    }


def _fact_rows(resource: Resource, index: BundleIndex, rule: dict) -> list[dict]:
    """Translate one resource into its main fact row and one row per modifier."""
    concept = rule["concept"]
    shared = {
        "resource_type": resource["resourceType"],
        "resource_id": resource["id"],
        "patient_id": index.resolve(resource["subject"]["reference"])["id"],
        "encounter_id": index.resolve(resource["encounter"]["reference"])["id"],
        "concept_cd": concept["concept_cd"],
        "start_date": _resolve(resource, concept.get("start_date")),
        "end_date": _resolve(resource, concept.get("end_date")),
    }
    main = {
        **shared,
        "modifier_cd": "@",
        **_values(resource, concept),
        "expected_unit": concept.get("expected_unit"),
    }
    modifiers = [
        {**shared, "modifier_cd": name, **_values(resource, spec), "expected_unit": None}
        for name, spec in rule.get("modifiers", {}).items()
    ]
    return [main] + [row for row in modifiers if row["tval_char"] is not None or row["nval_num"] is not None]
