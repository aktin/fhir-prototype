from typing import Mapping

import pandas as pd


def observation_facts(observations: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    return observations.merge(mapping, on=["profile", "device_category"], how="left")