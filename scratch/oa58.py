"""OpenAlex lookups via Windows-side curl (WSL has no egress)."""
import json, pathlib, subprocess, sys, time, urllib.parse

CURL = "/mnt/c/Windows/System32/curl.exe"
KEY = pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()


def curl(url: str) -> str:
    out = subprocess.run([CURL, "-sS", "-L", "--compressed", "-m", "90", url],
                         capture_output=True, text=True, timeout=150)
    return out.stdout


def search(q: str, n: int = 8):
    u = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
         + f"&per-page={n}&select=doi,title,publication_year,cited_by_count&api_key={KEY}"
         + "&mailto=research@marfagenez.local")
    d = json.loads(curl(u))
    for w in d.get("results", []):
        print(f"  {w.get('publication_year')} | {w.get('doi')} | {w.get('title')}")


def work(doi: str):
    enc = urllib.parse.quote("https://doi.org/" + doi, safe="")
    u = (f"https://api.openalex.org/works/{enc}?api_key={KEY}"
         "&mailto=research@marfagenez.local")
    w = json.loads(curl(u))
    inv = w.get("abstract_inverted_index") or {}
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    ab = " ".join(wd for _, wd in sorted(pos))
    print(f"=== {doi} | {w.get('publication_year')} | "
          f"pmcid={w.get('ids', {}).get('pmcid')} | oa={w.get('open_access', {}).get('oa_status')}"
          f" | cited={w.get('cited_by_count')}")
    print("TITLE:", w.get("title"))
    print("ABS:", ab)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "search":
        for q in sys.argv[2:]:
            print("===", q)
            search(q)
            time.sleep(0.5)
    else:
        for doi in sys.argv[2:]:
            try:
                work(doi)
            except Exception as e:
                print("=== ERR", doi, e)
            time.sleep(0.4)
