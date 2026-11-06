from dataclasses import replace

import pandas as pd

from fhir_prototype.frames import BundleFrames


def _to_utc(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        result[column] = pd.to_datetime(result[column], utc=True)
    return result


def process(frames: BundleFrames) -> BundleFrames:
    return replace(
        frames,
        observations=_to_utc(frames.observations, ["start", "end"]),
        encounters=_to_utc(frames.encounters, ["start", "end"]),
    )
