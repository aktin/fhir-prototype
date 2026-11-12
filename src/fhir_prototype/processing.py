from dataclasses import replace

import pandas as pd

from fhir_prototype.frames import BundleFrames


def to_datetime(df: pd.DataFrame, columns: list[str], *, utc=True) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        result[column] = pd.to_datetime(result[column], utc=utc)
    return result


def process(frames: BundleFrames) -> BundleFrames:
    return replace(
        frames,
        patients=to_datetime(frames.patients, ["birth_date"], utc=False),
        encounters=to_datetime(frames.encounters, ["start", "end"]),
    )
