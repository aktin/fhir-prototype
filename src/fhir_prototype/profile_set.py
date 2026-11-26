import json
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
            todo.append(f"{name}#{version}")
    return tree
