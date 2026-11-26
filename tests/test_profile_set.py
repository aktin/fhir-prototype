import json
from pathlib import Path

from fhir_prototype.profile_set import collect, load_resources, package_tree

OBSERVATION = "http://hl7.org/fhir/StructureDefinition/Observation"
EXTENSION = "http://hl7.org/fhir/StructureDefinition/Extension"
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


def test_collect_follows_extension():
    extension = make_profile("ext-device", parent=EXTENSION)
    profile = make_profile(
        "score-rass",
        elements=[
            {
                "path": "Observation.extension",
                "sliceName": "device",
                "type": [{"code": "Extension", "profile": [extension["url"] + "|1.0.0"]}],
            }
        ],
    )
    source = {r["url"]: r for r in (extension, profile)}

    collected, missing = collect([profile["url"]], source, known={OBSERVATION, EXTENSION})

    assert set(collected) == {profile["url"], extension["url"]}
    assert missing == []


def test_collect_follows_value_set_binding():
    code_system = {"resourceType": "CodeSystem", "url": "http://example.org/CodeSystem/rass"}
    value_set = {
        "resourceType": "ValueSet",
        "url": "http://example.org/ValueSet/rass",
        "compose": {"include": [{"system": code_system["url"]}]},
    }
    profile = make_profile(
        "score-rass",
        elements=[
            {
                "path": "Observation.value[x]",
                "binding": {"strength": "required", "valueSet": value_set["url"] + "|1.0.0"},
            }
        ],
    )
    source = {r["url"]: r for r in (code_system, value_set, profile)}

    collected, missing = collect([profile["url"]], source, known={OBSERVATION})

    assert set(collected) == {profile["url"], value_set["url"], code_system["url"]}
    assert missing == []


def test_collect_reports_missing_profile():
    profile = make_profile("score-rass")
    source = {profile["url"]: profile}
    old_peep = BASE + "vent-positiv-endexspiratorischer-druck"

    collected, missing = collect([profile["url"], old_peep], source, known={OBSERVATION})

    assert set(collected) == {profile["url"]}
    assert missing == [old_peep]


def write_package(packages_dir: Path, name: str, version: str, dependencies: dict[str, str]) -> None:
    package_dir = packages_dir / f"{name}#{version}" / "package"
    package_dir.mkdir(parents=True)
    manifest = {"name": name, "version": version, "dependencies": dependencies}
    (package_dir / "package.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_package_tree_lists_dependencies_nearest_first(tmp_path):
    write_package(tmp_path, "icu", "1.0.0", {"isik": "6.0.0", "base": "2.0.0"})
    write_package(tmp_path, "isik", "6.0.0", {"base": "1.0.0", "ti": "1.3.1"})
    write_package(tmp_path, "base", "2.0.0", {})
    write_package(tmp_path, "base", "1.0.0", {})
    write_package(tmp_path, "ti", "1.3.1", {"base": "2.0.0"})

    tree = package_tree(tmp_path, "icu#1.0.0")

    assert tree == ["icu#1.0.0", "isik#6.0.0", "base#2.0.0", "base#1.0.0", "ti#1.3.1"]


def test_package_tree_skips_fhir_core(tmp_path):
    write_package(tmp_path, "icu", "1.0.0", {"hl7.fhir.r4.core": "4.0.1", "backport": "1.1.0"})
    write_package(tmp_path, "backport", "1.1.0", {"hl7.fhir.r4.core": "4.0.0"})

    tree = package_tree(tmp_path, "icu#1.0.0")

    assert tree == ["icu#1.0.0", "backport#1.1.0"]


def test_package_tree_resolves_patch_wildcard_to_latest_cached(tmp_path):
    write_package(tmp_path, "icu", "1.0.0", {"base": "1.5.x"})
    write_package(tmp_path, "base", "1.5.4", {})
    write_package(tmp_path, "base", "1.5.10", {})
    write_package(tmp_path, "base", "1.6.0", {})

    tree = package_tree(tmp_path, "icu#1.0.0")

    assert tree == ["icu#1.0.0", "base#1.5.10"]


def write_resource(packages_dir: Path, package_id: str, file_name: str, resource: dict) -> None:
    path = packages_dir / package_id / "package" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resource), encoding="utf-8")


def test_load_resources_indexes_by_url_nearest_package_first(tmp_path):
    url = BASE + "score"
    write_resource(tmp_path, "icu#1.0.0", "StructureDefinition-score.json", make_profile("score") | {"version": "1"})
    write_resource(tmp_path, "base#1.0.0", "StructureDefinition-score.json", make_profile("score") | {"version": "0"})
    write_resource(tmp_path, "icu#1.0.0", "package.json", {"name": "icu", "url": "http://example.org/ig"})
    write_resource(tmp_path, "icu#1.0.0", "Bundle-no-url.json", {"resourceType": "Bundle"})
    write_resource(tmp_path, "icu#1.0.0", "example/StructureDefinition-x.json", make_profile("x"))

    resources = load_resources(tmp_path, ["icu#1.0.0", "base#1.0.0"])

    assert list(resources) == [url]
    assert resources[url]["version"] == "1"
