import json
import re
from collections import deque
from pathlib import Path


def _references(resource: dict) -> set[str]:
    found: set[str] = set()
    if resource.get("baseDefinition"):
        found.add(resource["baseDefinition"])
    elements = resource.get("differential", {}).get("element", []) + resource.get("snapshot", {}).get("element", [])
    for element in elements:
        for element_type in element.get("type", []):
            found.update(element_type.get("profile", []))
        if element.get("binding", {}).get("valueSet"):
            found.add(element["binding"]["valueSet"])
    compose = resource.get("compose", {})
    for part in compose.get("include", []) + compose.get("exclude", []):
        if part.get("system"):
            found.add(part["system"])
        found.update(part.get("valueSet", []))
    return {url.split("|")[0] for url in found}


def collect(roots: list[str], source: dict[str, dict], known: set[str]) -> tuple[dict[str, dict], list[str]]:
    """Return (collected resources by URL, URLs not found in source or known)."""
    collected: dict[str, dict] = {}
    missing: list[str] = []
    todo = deque(roots)
    seen: set[str] = set()
    while todo:
        url = todo.popleft()
        if url in seen:
            continue
        seen.add(url)
        if url in known:
            continue
        if url not in source:
            missing.append(url)
            continue
        resource = source[url]
        collected[url] = resource
        todo.extend(_references(resource))
    return collected, sorted(missing)


def package_tree(packages_dir: Path, root: str) -> list[str]:
    """Return the package ids of root and its dependencies, nearest first."""
    tree: list[str] = []
    todo = deque([root])
    while todo:
        package_id = todo.popleft()
        if package_id in tree:
            continue
        tree.append(package_id)
        manifest_path = packages_dir / package_id / "package" / "package.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, version in manifest.get("dependencies", {}).items():
            dependency = _resolve(packages_dir, name, version)
            if dependency is not None:
                todo.append(dependency)
    return tree


def _resolve(packages_dir: Path, name: str, version: str) -> str | None:
    """Return the cached package id for a dependency, or None for FHIR core."""
    if re.fullmatch(r"hl7\.fhir\.r\d+\.core", name):
        return None
    if not version.endswith(".x"):
        return f"{name}#{version}"
    prefix = version.removesuffix("x")
    candidates = [path.name.split("#", 1)[1] for path in packages_dir.glob(f"{name}#{prefix}*")]
    latest = max(candidates, key=lambda v: tuple(int(part) for part in v.split(".")))
    return f"{name}#{latest}"


def load_resources(packages_dir: Path, package_ids: list[str]) -> dict[str, dict]:
    """Index the resources of the packages by URL, the first package wins."""
    resources: dict[str, dict] = {}
    for package_id in package_ids:
        for path in sorted((packages_dir / package_id / "package").glob("*.json")):
            if path.name == "package.json":
                continue
            resource = json.loads(path.read_text(encoding="utf-8"))
            url = resource.get("url")
            if url:
                resources.setdefault(url, resource)
    return resources


def write_profiles(collected: dict[str, dict], out_dir: Path) -> None:
    """Replace the JSON files in out_dir with the collected resources."""
    files: dict[str, dict] = {}
    for url, resource in collected.items():
        name = f"{resource['resourceType']}-{resource['id']}.json"
        if name in files:
            raise ValueError(f"duplicate file name {name}: {files[name]['url']} and {url}")
        files[name] = resource
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    for name, resource in files.items():
        (out_dir / name).write_text(json.dumps(resource), encoding="utf-8")
