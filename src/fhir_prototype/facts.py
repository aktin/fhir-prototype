from dataclasses import dataclass

import pandas as pd

from fhir_prototype.frames import BundleFrames


@dataclass
class MappingResult:
    facts: pd.DataFrame
    unmapped: pd.DataFrame


FACT_COLUMNS = [
    "resource_type",
    "resource_id",
    "patient_id",
    "encounter_id",
    "concept_cd",
    "modifier_cd",
    "start_date",
    "end_date",
    "valtype_cd",
    "nval_num",
    "units_cd",
]


def split_unmapped(facts: pd.DataFrame) -> MappingResult:
    unmapped = facts["concept_cd"].isna()
    return MappingResult(facts=facts[~unmapped], unmapped=facts[unmapped])


def observation_facts(observations: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    facts = observations.merge(mapping, on=["profile", "device_category"], how="left")
    facts = facts.rename(columns={"observation_id": "resource_id", "start": "start_date", "end": "end_date"})
    facts["modifier_cd"] = "@"
    facts["nval_num"] = facts["value_num"]
    facts["resource_type"] = "Observation"
    from_text = facts["value_column"] == "value_text"
    facts.loc[from_text, "nval_num"] = pd.to_numeric(
        facts.loc[from_text, "value_text"], errors="coerce"
    )
    facts["units_cd"] = facts["value_unit"]
    return facts[FACT_COLUMNS]


def procedure_facts(procedures: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    mapping = mapping[mapping["resource_type"] == "Procedure"]
    facts = procedures.merge(mapping, on="profile", how="left")
    facts = facts.rename(columns={"procedure_id": "resource_id", "start": "start_date", "end": "end_date"})
    facts["resource_type"] = "Procedure"
    facts["modifier_cd"] = "@"
    facts["nval_num"] = None
    facts["units_cd"] = None
    return facts[FACT_COLUMNS]


def build_facts(frames: BundleFrames, mapping: pd.DataFrame) -> MappingResult:
    facts = pd.concat(
        [
            observation_facts(frames.observations, mapping),
            procedure_facts(frames.procedures, mapping),
        ],
        ignore_index=True,
    )
    return split_unmapped(facts)
