from collections import deque


def _references(resource: dict) -> set[str]:
    found: set[str] = set()
    if resource.get("baseDefinition"):
        found.add(resource["baseDefinition"])
    elements = resource.get("differential", {}).get("element", []) + resource.get("snapshot", {}).get("element", [])
    for element in elements:
        for element_type in element.get("type", []):
            found.update(element_type.get("profile", []))
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
