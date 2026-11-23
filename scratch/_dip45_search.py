import json, subprocess, urllib.parse, sys

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()


def get(params, base="https://api.openalex.org/works"):
    p = dict(params)
    p["api_key"] = KEY
    url = base + "?" + urllib.parse.urlencode(p)
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": r.stdout[:300]}


def search(q, n=10):
    d = get({"search": q, "per_page": str(n),
             "select": "id,doi,display_name,publication_year,abstract_inverted_index"})
    if "_raw" in d:
        print("### %s -> PARSE FAIL %s" % (q, d["_raw"]))
        return
    print("### %s  -> count %s" % (q, d["meta"]["count"]))
    for w in d["results"]:
        ai = w.get("abstract_inverted_index")
        print("  ", w["publication_year"], w["doi"], "|", (w["display_name"] or "")[:100],
              "| abs=" + ("Y" if ai else "N"))
    print()


def abstract(doi):
    d = get({"select": "id,doi,display_name,publication_year,abstract_inverted_index"},
            base="https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe=""))
    if "_raw" in d or "error" in d:
        return None, None
    ai = d.get("abstract_inverted_index")
    if not ai:
        return None, None
    pos = {}
    for word, idxs in ai.items():
        for i in idxs:
            pos.setdefault(i, []).append(word)
    return d.get("display_name"), " ".join(" ".join(pos[i]) for i in sorted(pos))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "search":
        for q in sys.argv[2:]:
            search(q)
    elif mode == "abs":
        for doi in sys.argv[2:]:
            t, a = abstract(doi)
            print("=" * 20, doi)
            print("TITLE:", t)
            print("ABSTRACT:", a)
            print()
