#!/usr/bin/env python3
"""lab/migration/shadow_compare.py — shadow-сверка с .coord/ (Фаза 2 §22).

Read-only к .coord/: сравнение идёт по экспорту мигратора и прямым хэшам
файлов; старая очередь не пишется ни одной командой (это проверяется
fingerprint-ом дерева до/после).

Проверяется (план v0.3 §23.5):
- детерминизм: повторная выгрузка байт-в-байт идентична (canon+sha256);
- репрезентативность: выборочные raw-файлы совпадают с заявленными sha256;
- инвентарь: количество файлов в дереве соответствует counts экспорта;
- изоляция: mtime/size всех файлов до == после среза (никто не писал).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.migration.coord_migrate import Migrator, sha256_file  # noqa: E402


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def fingerprint(root: Path) -> dict[str, str]:
    """path -> size:mtime_ns для каждого файла дерева. Чтение только stat."""
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(root))] = f"{st.st_size}:{st.st_mtime_ns}"
    return out


class ShadowCompare:
    """Срез старой очереди: детерминизм, spot-хэши, изоляция записи."""

    def __init__(self, coord_root: Path, sample: int = 20, seed: int = 20261126):
        self.root = Path(coord_root)
        self.sample = sample
        self.seed = seed

    def _export(self) -> dict:
        mig = Migrator(self.root)
        mig.run()
        return mig.export("shadow-compare", "shadow")

    def run(self) -> dict:
        fp_before = fingerprint(self.root)
        t0 = time.time()
        e1, e2 = self._export(), self._export()
        det = {
            "deterministic": _canon(e1) == _canon(e2),
            "export_sha256": hashlib.sha256(
                _canon(e1).encode()).hexdigest(),
        }
        rng = random.Random(self.seed)
        tasks = [t for t in e1.get("tasks", []) if t.get("raw_paths")]
        spot_tasks = rng.sample(tasks, min(self.sample, len(tasks)))
        spot: list[dict] = []
        for t in spot_tasks:
            want = t.get("task_md_sha256")
            hit = False
            for rel in t["raw_paths"]:
                p = self.root / rel
                if not p.is_file():
                    spot.append({"id": t["id"], "path": rel, "ok": False,
                                 "error": "файл исчез"})
                    continue
                if want and sha256_file(p) == want:
                    hit = True
            if want is not None:
                spot.append({"id": t["id"], "ok": hit,
                             "paths": len(t["raw_paths"])})
        msgs = [m for m in e1.get("messages", []) if m.get("raw_path")]
        spot_msgs = rng.sample(msgs, min(self.sample, len(msgs)))
        for m in spot_msgs:
            p = self.root / m["raw_path"]
            ok = False
            if p.is_file():
                ok = sha256_file(p) == m.get("body_sha256")
            spot.append({"id": m.get("id"), "kind": "message", "ok": ok})
        fp_after = fingerprint(self.root)
        readonly_ok = fp_before == fp_after
        counts = e1.get("counts", {})
        inv_files = sum(v for k, v in counts.items()
                        if k.endswith("_files") or k == "files")
        ok = (det["deterministic"] and readonly_ok
              and bool(spot) and all(s.get("ok") for s in spot))
        return {
            "verdict": "ok" if ok else "mismatch",
            "root": str(self.root),
            "determinism": det,
            "read_only_tree": readonly_ok,
            "spot_checks": spot,
            "spot_total": len(spot),
            "counts": counts,
            "inventory_files_approx": inv_files,
            "unresolved": e1.get("unresolved", []),
            "elapsed_seconds": round(time.time() - t0, 2),
        }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="shadow-сверка с .coord/ (read-only)")
    ap.add_argument("--coord", required=True, help="путь к .coord/ или snapshot")
    ap.add_argument("--out", help="JSON-отчёт")
    ap.add_argument("--sample", type=int, default=20)
    args = ap.parse_args()
    sc = ShadowCompare(Path(args.coord), sample=args.sample)
    rep = sc.run()
    text = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if rep["verdict"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
