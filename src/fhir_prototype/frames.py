import pandas as pd

from fhir_prototype.bundle_index import BundleIndex, Resource

PATIENT_COLUMNS = [
    "patient_id",
    "identifier_system",
    "identifier_value",
    "gender",
    "birth_date",
]

ENCOUNTER_COLUMNS = [
    "encounter_id",
    "patient_id",
    "identifier_system",
    "identifier_value",
    "status",
    "class_code",
    "start",
    "end",
]


def patients_frame(index: BundleIndex) -> pd.DataFrame:
    rows = [_patient_row(p) for p in index.of_type("Patient")]
    return pd.DataFrame(rows, columns=PATIENT_COLUMNS)


def _patient_row(patient: Resource) -> dict:
    identifier = (patient.get("identifier") or [{}])[0]
    return {
        "patient_id": patient["id"],
        "identifier_system": identifier.get("system"),
        "identifier_value": identifier.get("value"),
        "gender": patient.get("gender"),
        "birth_date": patient.get("birthDate"),
    }


def encounters_frame(index: BundleIndex) -> pd.DataFrame:
    rows = [_encounter_row(e, index) for e in index.of_type("Encounter")]
    return pd.DataFrame(rows, columns=ENCOUNTER_COLUMNS)


def _encounter_row(encounter: Resource, index: BundleIndex) -> dict:
    identifier = (encounter.get("identifier") or [{}])[0]
    patient = index.resolve(encounter["subject"]["reference"])
    period = encounter.get("period", {})
    return {
        "encounter_id": encounter["id"],
        "patient_id": patient["id"],
        "identifier_system": identifier.get("system"),
        "identifier_value": identifier.get("value"),
        "status": encounter.get("status"),
        "class_code": encounter.get("class", {}).get("code"),
        "start": period.get("start"),
        "end": period.get("end"),
    }
