import sys
sys.path.insert(0, "/root/marfagenez/scratch")
from oa_probe49 import search

QUERIES = [
    "mitophagy rate mt-Keima quantification per hour neurons",
    "protein degradation flux molecules per cell per minute proteasome",
    "8-oxoguanine steady state level repair capacity human cells measurement",
    "plasma membrane lipid internalization rate per minute endocytosis quantified",
    "membrane wound repair lipid addition rate micrometres squared seconds",
]
for q in QUERIES:
    print("=" * 15, q)
    try:
        d = search(q, 8)
    except Exception as e:
        print("ERR", e); continue
    for w in d.get("results", []):
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
        print(w.get("publication_year"), "|", (w.get("title") or "")[:100], "|", w.get("doi"), "|", src, "|", w.get("cited_by_count"))
