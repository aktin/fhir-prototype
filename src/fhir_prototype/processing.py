from dataclasses import replace

import pandas as pd

from fhir_prototype.frames import BundleFrames


def process(frames: BundleFrames) -> BundleFrames:
    df_observations = frames.observations.copy()
    df_observations["start"] = pd.to_datetime(df_observations["start"], utc=True)
    df_observations["end"] = pd.to_datetime(df_observations["end"], utc=True)
    return replace(frames, observations=df_observations)
