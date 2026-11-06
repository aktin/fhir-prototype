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