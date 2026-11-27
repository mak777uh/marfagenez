#!/usr/bin/env python3
"""Create a non-destructive role/phase sidecar for historic experiment results.

This does not edit result JSON. Absence of an independent external dataset is
not validation, and absence of a timestamped preregistration with a primary
outcome is not confirmatory.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "_markup-legacy.json"


def classify(record: dict) -> dict:
    validation = record.get("validation") or {}
    independent = (
        isinstance(validation, dict)
        and validation.get("independent") is True
        and bool(validation.get("dataset") or validation.get("source"))
    )
    role = "validation" if independent else "verification"

    prereg = record.get("preregistration") or {}
    confirmatory = False
    if isinstance(prereg, dict):
        registered = prereg.get("registered_at")
        primary = prereg.get("primary_outcome")
        analysis = prereg.get("analysis")
        created = record.get("created_at")
        if registered and primary and analysis and created:
            try:
                confirmatory = datetime.fromisoformat(
                    str(registered).replace("Z", "+00:00")
                ) <= datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                confirmatory = False

    phase = "confirmatory" if confirmatory and role == "verification" else "exploratory"
    if record.get("schema") == "marfagenez.experiment-result.v2":
        rule = "legacy-v2-conservative"
        reason = (
            "v2 carries neither a declared independent validation dataset nor "
            "a verifiable preregistration/primary-outcome/analysis timestamp; "
            "classified as exploratory verification without modifying source"
        )
    else:
        rule = "explicit-metadata"
        reason = "classification follows explicit validation and preregistration metadata"
    return {"role": role, "phase": phase, "rule": rule, "reason": reason}


def build_mapping() -> dict:
    records = {}
    for path in sorted(RESULTS.glob("*/run-*.json")):
        if path.parts[-2] == "_archive":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        exp = str(data.get("experiment_id") or path.parent.name)
        run = str(data.get("run_id") or path.stem)
        records[f"{exp}/{run}"] = classify(data)
    return {
        "schema": "marfagenez.legacy-role-phase.v1",
        "rulebook": {
            "validation": "Only explicit independent external dataset/source metadata qualifies",
            "confirmatory": "Only timestamped preregistration with primary_outcome and analysis before created_at qualifies; validation-confirmatory is prohibited",
            "legacy_v2": "Default to verification/exploratory when the v2 record does not carry both proofs",
        },
        "count": len(records),
        "records": records,
    }


def main() -> int:
    mapping = build_mapping()
    OUTPUT.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {mapping['count']} records")
    print("source results unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
