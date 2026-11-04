import pandas as pd

from fhir_prototype.bundle_index import BundleIndex, Resource

PATIENT_COLUMNS = [
    "patient_id",
    "identifier_system",
    "identifier_value",
    "gender",
    "birth_date",
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