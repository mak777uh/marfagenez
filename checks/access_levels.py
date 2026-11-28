"""Canonical literature access levels shared by map and literature checks.

Legacy spellings are normalized for validation only; this module never edits
corpus files. Unknown labels are invalid and must be adjudicated explicitly.
"""
from __future__ import annotations

import sys

ACCESS_LEVELS = (
    "metadata_only",
    "abstract_read",
    "fragment_read",
    "full_text_examined",
    "secondary_only",
)
ACCESS_LEVEL_ORDER = {name: index for index, name in enumerate(ACCESS_LEVELS)}

# Conservative, explicit migration table. In particular, an Europe PMC
# fullTextXML retrieval label is only treated as a quoted fragment: it does
# not prove that the entire paper was examined.
_ALIASES = {
    "metadata_only": "metadata_only",
    "metadata": "metadata_only",
    "abstract": "abstract_read",
    "abstract_read": "abstract_read",
    "fragment": "fragment_read",
    "fragment_read": "fragment_read",
    "partial": "fragment_read",
    "open-access (europe pmc fulltextxml)": "fragment_read",
    "full": "full_text_examined",
    "fulltext": "full_text_examined",
    "full_text": "full_text_examined",
    "full text": "full_text_examined",
    "full_text_read": "full_text_examined",
    "full_text_examined": "full_text_examined",
    "derived": "secondary_only",
    "secondary": "secondary_only",
    "secondary_only": "secondary_only",
}


def normalize_access_level(value: object) -> str | None:
    """Normalize a known legacy spelling; return None for absent/unknown."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    key = " ".join(value.strip().lower().split())
    if not key:
        return None
    return _ALIASES.get(key)


def selftest() -> int:
    cases = {
        "metadata_only": "metadata_only",
        "abstract": "abstract_read",
        "fragment": "fragment_read",
        "partial": "fragment_read",
        "full": "full_text_examined",
        "fulltext": "full_text_examined",
        "full_text": "full_text_examined",
        "full text": "full_text_examined",
        "full_text_read": "full_text_examined",
        "full_text_examined": "full_text_examined",
        "derived": "secondary_only",
        "open-access (Europe PMC fullTextXML)": "fragment_read",
    }
    failures = []
    for raw, expected in cases.items():
        actual = normalize_access_level(raw)
        if actual != expected:
            failures.append(f"{raw!r}: {actual!r} != {expected!r}")
    for raw in ("", "unknown", "open-access", 7, []):
        if normalize_access_level(raw) is not None:
            failures.append(f"unknown value was accepted: {raw!r}")
    if normalize_access_level(None) is not None:
        failures.append("None must remain absent")
    if failures:
        print("access-level selftest: FAIL")
        for item in failures:
            print("  " + item)
        return 1
    print(f"access-level selftest: {len(cases) + 6}/{len(cases) + 6}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())
    print("usage: python3 checks/access_levels.py --selftest")
    raise SystemExit(2)

