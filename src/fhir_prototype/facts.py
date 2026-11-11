import pandas as pd


def observation_facts(observations: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    facts = observations.merge(mapping, on=["profile", "device_category"], how="left")
    facts["nval_num"] = facts["value_num"]
    facts["units_cd"] = facts["value_unit"]
    return facts
