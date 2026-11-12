"""Mark the two pre-contract observe-vs-act results as `void` with a reason.

They were written on 2026-11-11 under schema v1, before PROTOCOL.md §1-§6
existed.  The measurements are real and the files are kept; what they lack is
the envelope the contract requires.  Rewriting them as if they had been done
properly would be inventing evidence, so the envelope says plainly that they
were not.

The `series` and `conditions` blocks are left exactly as recorded.
"""
import json

ROOT = "/mnt/c/Users/Admin/Documents/Qoder/2026-10-18/82ab86cd/marfagenez/results"
FILES = [
    f"{ROOT}/observe-vs-act/run-2026-11-11T07-46-13.json",
    f"{ROOT}/observe-vs-act/run-2026-11-11T18-03-07.json",
]

REASON = (
    "EXPLAINED: this run predates PROTOCOL.md. It records no arithmetic "
    "written before the run, no control tests, no dynamics hash and no verdict, "
    "so there is no way to tell from the file whether the comparison it reports "
    "would survive a control. The numbers are kept because they are what was "
    "measured, but they are not evidence for or against anything. Marking it "
    "void is the honest reading; rewriting the envelope to look compliant would "
    "be inventing the missing work."
)

for path in FILES:
    d = json.load(open(path))
    d["schema"] = "marfagenez.experiment-result.v2"
    d["name"] = "observe-vs-act"
    d["question"] = (
        "Does an observer that only writes to a log change the field it observes?"
    )
    d["arithmetic"] = {
        "note": (
            "Not recorded at the time. The contract requires the arithmetic to "
            "be written BEFORE the run; writing it now would be a reconstruction, "
            "so it is left absent and the verdict is `void`."
        )
    }
    # Keep the recorded measurements; the contract wants them under `rows`.
    d["rows"] = [
        {"condition": k, **v} for k, v in (d.get("conditions") or {}).items()
    ]
    d["hashes"] = {
        "recorded": d.get("series_hash")
        or (d.get("series") or {}).get("hash")
        or "none-recorded",
    }
    d["controls"] = {
        "fires": {"passed": False, "detail": "not run: predates the contract"},
        "silent": {"passed": False, "detail": "not run: predates the contract"},
        "specific": {"passed": False, "detail": "not run: predates the contract"},
    }
    d["verdict"] = {"kind": "void", "reason": REASON}
    lim = d.get("limitations")
    if isinstance(lim, str):
        lim = [lim]
    d["limitations"] = (lim or []) + [
        "Recorded before PROTOCOL.md: no arithmetic, no controls, no hash.",
        "Kept as a record of what was measured, not as evidence.",
    ]
    d["what_this_does_not_prove"] = (
        "It does not show that observation is free or that it costs. It shows "
        "only that this run cannot answer the question."
    )
    json.dump(d, open(path, "w"), ensure_ascii=False, indent=1)
    print("marked void:", path)
