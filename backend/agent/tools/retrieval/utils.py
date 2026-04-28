import os
import re
from typing import Dict, Iterable, List, Sequence, Set, Tuple


def iter_code_files(
    repo_path: str,
    supported_extensions: Tuple[str, ...],
    skip_dirs: Set[str],
) -> Iterable[str]:
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith(supported_extensions):
                full = os.path.join(root, file)
                yield os.path.relpath(full, repo_path)


def dedup_list(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def expand_terms(
    points: List[str],
    synonym_map: Dict[str, List[str]],
    zh_map: Dict[str, List[str]],
) -> List[str]:
    terms: List[str] = []
    for point in points:
        if not point:
            continue
        lowered = point.lower()
        terms.append(lowered)

        chunks = re.split(r"[\\s,，。;；、:/|()\\[\\]{}]+", lowered)
        for c in chunks:
            c = c.strip()
            if len(c) >= 2:
                terms.append(c)

    extra: List[str] = []
    for t in terms:
        for k, vals in synonym_map.items():
            if k in t:
                extra.extend(vals)
        for k, vals in zh_map.items():
            if k in t:
                extra.extend(vals)

    terms.extend(extra)
    return dedup_list([t for t in terms if t])
