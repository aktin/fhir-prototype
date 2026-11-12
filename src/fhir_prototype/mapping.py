import json
from pathlib import Path

import pandas as pd

CSV_MAPPING_PATH = Path(__file__).parent / "icu_mapping.csv"

MAPPING_PATH = Path(__file__).parent / "icu_mapping.json"


def load_mapping() -> list[dict]:
    """Load the rules that translate FHIR profiles into i2b2 facts."""
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

def load_csv_mapping() -> pd.DataFrame:
    return pd.read_csv(CSV_MAPPING_PATH)