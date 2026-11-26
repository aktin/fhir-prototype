from fhir_prototype.profile_set import collect

OBSERVATION = "http://hl7.org/fhir/StructureDefinition/Observation"
BASE = "http://example.org/StructureDefinition/"


def make_profile(name: str, parent: str = OBSERVATION, elements: list[dict] | None = None) -> dict:
    return {
        "resourceType": "StructureDefinition",
        "url": BASE + name,
        "baseDefinition": parent,
        "differential": {"element": elements or []},
    }


def test_collect_follows_parent_profile():
    parent = make_profile("score")
    child = make_profile("score-rass", parent=parent["url"])
    source = {r["url"]: r for r in (parent, child)}

    collected, missing = collect([child["url"]], source, known={OBSERVATION})

    assert set(collected) == {child["url"], parent["url"]}
    assert missing == []
