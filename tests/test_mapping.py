from fhir_prototype.mapping import load_mapping


def test_load_mapping_has_expected_columns():
    mapping = load_mapping()

    assert list(mapping.columns) == [
        "resource_type",
        "profile",
        "device_category",
        "concept_cd",
        "valtype_cd",
        "value_column",
        "units_cd",
        "status",
        "open_question",
        "note",
    ]


def test_mapping_has_unique_profile_and_device_category():
    mapping = load_mapping()

    assert not mapping.duplicated(subset=["profile", "device_category"]).any()