#!/usr/bin/env python3
"""eval_verdict.py -- does the exam say INVALID/FAIL where it must?

Three cases, each with an expected verdict:

1. the demo runs (4 answers, 3 deliberate errors) -> INVALID: coverage is 4/84.
2. a complete but empty run set (all 84 answered, nothing cited) -> FAIL, not INVALID.
3. the same complete set with one duplicate -> INVALID (a duplicate is not a smaller exam).

Exit 0 when every verdict matches; 1 otherwise. Diagnostic, not a gate check: it writes a temp file.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC = json.loads((ROOT / 'kg' / 'eval' / 'questions.json').read_text(encoding='utf-8'))


def score(runs):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as fh:
        json.dump(runs, fh, ensure_ascii=False)
        path = fh.name
    r = subprocess.run(['python3', str(ROOT / 'kg' / 'eval' / 'score.py'), path, '--report-only'],
                       capture_output=True, text=True)
    pathlib.Path(path).unlink()
    out = r.stdout
    verdict = json.loads(out[:out.rindex('}') + 1]).get('verdict')
    return verdict


def complete_empty():
    return [{"id": q["id"], "seed": s, "cited": [], "answer": "", "map_tokens": 0,
             "expand_tokens": 0, "answer_tokens": 0, "files_opened": 0, "tools": []}
            for q in SPEC["questions"] for s in range(1, 4)]


def main():
    demo = json.loads((ROOT / 'kg' / 'eval' / 'demo-runs.json').read_text(encoding='utf-8'))
    cases = [
        ("демо-прогоны (4 ответа из 84)", demo, "INVALID"),
        ("полный, но пустой набор", complete_empty(), "FAIL"),
        ("полный набор + дубль", complete_empty() + complete_empty()[:1], "INVALID"),
    ]
    bad = 0
    for name, runs, want in cases:
        got = score(runs)
        ok = got == want
        print("  %-34s ожидалось %-8s получено %-8s %s" % (name, want, got, "ok" if ok else "ПРОВАЛ"))
        bad += 0 if ok else 1
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
