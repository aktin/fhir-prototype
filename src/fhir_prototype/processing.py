from dataclasses import replace

import pandas as pd

from fhir_prototype.frames import BundleFrames


def parse_dates(df: pd.DataFrame, columns: list[str], *, utc=False) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        result[column] = pd.to_datetime(result[column], utc=utc)
    return result


def process(frames: BundleFrames) -> BundleFrames:
    return replace(
        frames,
        patients=parse_dates(frames.patients, ["birth_date"]),
        observations=parse_dates(frames.observations, ["start", "end"], utc=True),
        encounters=parse_dates(frames.encounters, ["start", "end"], utc=True),
        procedures=parse_dates(frames.procedures, ["start", "end"], utc=True),
    )
