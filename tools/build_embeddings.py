"""Build the local embedding index of the knowledge graph.

Why this runs on Windows: the model and fastembed live in the Windows venv (`/mnt/c/.../sci-venv`); WSL has
no network and no model. The output is two files that the gate can read offline:

    kg/embeddings.bin         float32 matrix, rows in the order of `ids`
    kg/embeddings.meta.json   model, dim, count, ids, sha256(nodes.jsonl), built_at

The model is **multilingual** on purpose: node texts are Russian, most abstracts are English, and an
English-only encoder maps those two languages into different neighbourhoods.

Usage (Windows venv python, from the repository root):
    python.exe tools/build_embeddings.py --out <dir>
    python.exe tools/build_embeddings.py --model Qdrant/bge-small-en-v1.5-onnx-Q --out <dir>
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

# fastembed 0.9.1 does not ship multilingual-e5-small; of the supported multilingual encoders this
# is the small one (384 dim, 50+ languages). e5-large exists here too but is an order of magnitude
# heavier for a 564-node index.
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
E5_PASSAGE = "passage: "


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else root / "kg"
    model_name = argv[argv.index("--model") + 1] if "--model" in argv else DEFAULT_MODEL
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0

    nodes_path = root / "kg" / "nodes.jsonl"
    rows = []
    for line in nodes_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        node = json.loads(line)
        rows.append(node)
    if limit:
        rows = rows[:limit]

    ids = [n["id"] for n in rows]
    texts = []
    for node in rows:
        context = node.get("context") or {}
        parts = [node.get("text") or ""]
        if isinstance(context, dict):
            parts.append(" ".join(str(v) for v in context.values() if v))
        texts.append((node.get("kind") or "") + ". " + " ".join(parts).strip())

    from fastembed import TextEmbedding  # noqa: PLC0415

    model = TextEmbedding(model_name=model_name)
    prefixed = [E5_PASSAGE + t for t in texts] if "e5-" in model_name.lower() else texts
    vectors = list(model.embed(prefixed))

    import numpy as np  # noqa: PLC0415

    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2:
        print("модель вернула не матрицу", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    (out / "embeddings.bin").write_bytes(matrix.tobytes())
    meta = {
        "model": model_name,
        "dim": int(matrix.shape[1]),
        "count": int(matrix.shape[0]),
        "ids": ids,
        "nodes_sha256": hashlib.sha256(nodes_path.read_bytes()).hexdigest(),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prefix": E5_PASSAGE if "e5-" in model_name.lower() else "",
    }
    (out / "embeddings.meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"модель: {model_name}; узлов: {meta['count']}; размерность: {meta['dim']}")
    print(f"файлы: {out / 'embeddings.bin'}, {out / 'embeddings.meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
