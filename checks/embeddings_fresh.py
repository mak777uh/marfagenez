"""The embedding index must describe the graph that exists now, not the one it was built from.

A stale index is worse than no index: `kg.py similar` would return neighbours from a previous state of the
graph and look perfectly confident. So the index carries `nodes_sha256` and this check recomputes it.

Rules:
  E1 `kg/embeddings.meta.json` exists and parses; model, dim, count, ids, nodes_sha256 present;
  E2 `nodes_sha256` equals sha256 of the current `kg/nodes.jsonl` (otherwise: rebuild);
  E3 `count` equals the number of nodes and `ids` equals their ids in order;
  E4 `kg/embeddings.bin` size is exactly count * dim * 4 bytes;
  E5 dim is positive and the model name is not empty.

Usage:
    python3 checks/embeddings_fresh.py
    python3 checks/embeddings_fresh.py --selftest
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
META = ROOT / "kg" / "embeddings.meta.json"
BIN = ROOT / "kg" / "embeddings.bin"
NODES = ROOT / "kg" / "nodes.jsonl"


def node_ids(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    return [json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(meta_path: pathlib.Path, bin_path: pathlib.Path, nodes_path: pathlib.Path) -> list[str]:
    errs: list[str] = []
    if not meta_path.exists():
        return [f"E1 нет {meta_path.name}: индекс не собран (см. tools/build_embeddings.py)"]
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"E1 meta не JSON: {exc}"]
    for field in ("model", "dim", "count", "ids", "nodes_sha256"):
        if field not in meta:
            errs.append(f"E1 в meta нет поля `{field}`")
    if errs:
        return errs
    if not meta.get("model"):
        errs.append("E5 пустое имя модели")
    dim = int(meta.get("dim") or 0)
    count = int(meta.get("count") or 0)
    if dim <= 0:
        errs.append("E5 размерность не положительна")

    digest = hashlib.sha256(nodes_path.read_bytes()).hexdigest() if nodes_path.exists() else ""
    if meta.get("nodes_sha256") != digest:
        errs.append("E2 индекс собран из другой версии графа: пересоберите "
                    "(python3 tools/build_embeddings.py)")

    ids = node_ids(nodes_path)
    if count != len(ids):
        errs.append(f"E3 count={count}, а узлов {len(ids)}")
    if list(meta.get("ids") or []) != ids:
        errs.append("E3 порядок `ids` в meta не совпадает с порядком узлов в nodes.jsonl")

    if bin_path.exists():
        size = bin_path.stat().st_size
        want = count * dim * 4
        if size != want:
            errs.append(f"E4 размер embeddings.bin {size}, ожидался {want} ({count}×{dim}×4)")
    else:
        errs.append(f"E4 нет {bin_path.name}")
    return errs


def selftest() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="embeddings-"))
    nodes = tmp / "nodes.jsonl"
    nodes.write_text('{"id": "A"}\n{"id": "B"}\n', encoding="utf-8")
    digest = hashlib.sha256(nodes.read_bytes()).hexdigest()

    counter = {"n": 0}

    def write(meta: dict, size: int) -> tuple[pathlib.Path, pathlib.Path]:
        counter["n"] += 1
        mp = tmp / f"m{counter['n']}.json"
        bp = tmp / f"b{counter['n']}.bin"
        mp.write_text(json.dumps(meta), encoding="utf-8")
        bp.write_bytes(b"\0" * size)
        return mp, bp

    good = write({"model": "m", "dim": 2, "count": 2, "ids": ["A", "B"], "nodes_sha256": digest}, 16)
    stale = write({"model": "m", "dim": 2, "count": 2, "ids": ["A", "B"], "nodes_sha256": "0" * 64}, 16)
    wrong_order = write({"model": "m", "dim": 2, "count": 2, "ids": ["B", "A"], "nodes_sha256": digest}, 16)
    wrong_size = write({"model": "m", "dim": 2, "count": 2, "ids": ["A", "B"], "nodes_sha256": digest}, 8)

    cases = [
        ("свежий индекс", check(good[0], good[1], nodes), []),
        ("индекс от другой версии графа", check(stale[0], stale[1], nodes), ["E2"]),
        ("другой порядок id", check(wrong_order[0], wrong_order[1], nodes), ["E3"]),
        ("неверный размер матрицы", check(wrong_size[0], wrong_size[1], nodes), ["E4"]),
    ]
    total, bad = 0, 0
    for name, got, want in cases:
        total += 1
        ok = all(any(w in e for e in got) for w in want) if want else not got
        if not ok:
            bad += 1
            print(f"  FAIL {name}: ждали {want or 'чисто'}, получили {got}")
        else:
            print(f"  ok   {name}")
    print(f"selftest: {total - bad}/{total}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errs = check(META, BIN, NODES)
    if errs:
        print(f"ИНДЕКС ЭМБЕДДИНГОВ: {len(errs)} нарушений")
        for e in errs[:12]:
            print("  " + e)
        return 1
    meta = json.loads(META.read_text(encoding="utf-8"))
    print(f"индекс эмбеддингов свежий: {meta['count']} узлов, {meta['dim']} измерений, модель {meta['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
