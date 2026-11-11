import pandas as pd


def observation_facts(observations: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    facts = observations.merge(mapping, on=["profile", "device_category"], how="left")
    facts["nval_num"] = facts["value_num"]
    from_text = facts["value_column"] == "value_text"
    facts.loc[from_text, "nval_num"] = pd.to_numeric(
        facts.loc[from_text, "value_text"], errors="coerce"
    )
    facts["units_cd"] = facts["value_unit"]
    return facts
