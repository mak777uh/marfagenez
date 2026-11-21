"""Local semantic search over scholarly metadata. No API keys, no cloud embeddings.

Why this exists
---------------
Semantic Scholar returns 403 without a key, so the "semantic" channel had nothing
behind it: every other source we use ranks lexically. This tool builds the channel
ourselves:

  1. fetch a candidate pool from OpenAlex (key optional, raises the daily budget),
  2. rebuild each abstract from `abstract_inverted_index`,
  3. embed the query and every abstract locally with FastEmbed/ONNX (BGE-small),
  4. rank by cosine and print the top matches with provenance.

The point is not to beat OpenAlex relevance; it is to find papers whose *wording*
differs from the query (the case where lexical search returns nothing relevant).

Usage:
    python semantic_search.py "a system that produces the components that produce it"
    python semantic_search.py "closure of constraints" --seeds "autopoiesis;organisational closure;constraints" --top 15
    python semantic_search.py --from-file results.json --query "self-producing system"

Exit codes: 0 ok, 2 no candidate abstracts, 3 embedding model unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np
import requests

OPENALEX = "https://api.openalex.org/works"
UA = "dsh-semantic-search/1.0 (local research tool)"
MAILTO = os.environ.get("OPENALEX_EMAIL", "")
MODEL = "BAAI/bge-small-en-v1.5"
# bge-en-v1.5 expects an instruction on the *query* side; encoding the question as a
# passage (what we did before) is the documented way to lose accuracy silently.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def rebuild_abstract(inv: dict | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; invert it back to text."""
    if not inv:
        return ""
    slots: list[tuple[int, str]] = []
    for word, positions in inv.items():
        for pos in positions:
            slots.append((int(pos), word))
    slots.sort()
    return " ".join(word for _, word in slots)


def fetch_openalex(seeds: list[str], per_page: int, key: str | None) -> list[dict]:
    out: list[dict] = []
    for seed in seeds:
        params = {
            "search": seed,
            "per_page": per_page,
            "select": "id,doi,title,publication_year,abstract_inverted_index,cited_by_count",
        }
        if key:
            params["api_key"] = key
        if MAILTO:
            params["mailto"] = MAILTO
        try:
            r = requests.get(OPENALEX, params=params, headers={"User-Agent": UA}, timeout=40)
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"  openalex '{seed}': {type(exc).__name__}", file=sys.stderr)
            continue
        payload = r.json()
        print(f"  openalex '{seed}': {payload.get('meta', {}).get('count', '?')} matches", file=sys.stderr)
        for w in payload.get("results", []):
            out.append(
                {
                    "title": w.get("title") or "",
                    "year": w.get("publication_year"),
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
                    "citations": w.get("cited_by_count"),
                    "source": "openalex",
                }
            )
        time.sleep(0.2)
    return out


def dedupe(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = (row.get("doi") or row.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def embed(texts: list[str]):
    from fastembed import TextEmbedding  # imported late: model download is the slow part

    model = TextEmbedding(MODEL)
    return np.array(list(model.embed(texts)), dtype=np.float32)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Local semantic search over OpenAlex abstracts")
    ap.add_argument("query", help="concept description, not keywords")
    ap.add_argument("--seeds", default="", help="semicolon-separated lexical seeds for the candidate pool")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--per-seed", type=int, default=50)
    ap.add_argument("--from-file", default="", help="rank a JSON list instead of fetching")
    args = ap.parse_args(argv)

    key = os.environ.get("OPENALEX_API_KEY")
    if args.from_file:
        rows = json.loads(pathlib.Path(args.from_file).read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("results") or rows.get("papers") or []
        print(f"pool: {len(rows)} records from {args.from_file}", file=sys.stderr)
    else:
        seeds = [s.strip() for s in args.seeds.split(";") if s.strip()] or [args.query]
        print(f"pool: fetching from OpenAlex for {len(seeds)} seed(s)", file=sys.stderr)
        rows = fetch_openalex(seeds, args.per_seed, key)

    rows = [r for r in dedupe(rows) if (r.get("abstract") or "").strip()]
    if not rows:
        print("no candidate abstracts", file=sys.stderr)
        return 2
    print(f"pool: {len(rows)} records with abstracts", file=sys.stderr)

    try:
        query_text = BGE_QUERY_INSTRUCTION + args.query
        vectors = embed([query_text] + [f"{r.get('title','')}. {r['abstract']}" for r in rows])
    except Exception as exc:  # noqa: BLE001
        print(f"embedding unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    q = vectors[0]
    q = q / (np.linalg.norm(q) + 1e-9)
    m = vectors[1:]
    m = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    scores = m @ q

    order = np.argsort(-scores, kind="stable")[: args.top]
    print(f"\nsemantic ranking ({MODEL})")
    for rank, i in enumerate(order, 1):
        r = rows[int(i)]
        print(f"{rank:2d}. {scores[i]:.3f}  [{r.get('year')}] {(r.get('title') or '')[:96]}")
        print(f"        doi={r.get('doi') or '—'}  cites={r.get('citations')}  {r.get('source')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
