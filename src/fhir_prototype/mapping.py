from pathlib import Path

import pandas as pd

MAPPING_PATH = Path(__file__).parent / "icu_mapping.csv"


def load_mapping() -> pd.DataFrame:
    return pd.read_csv(MAPPING_PATH)
