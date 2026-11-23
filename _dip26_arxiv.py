import urllib.request, urllib.parse, json, re, time, pathlib

UA = {"User-Agent": "marfagenez-research/1.0 (mailto:research@example.org)"}
OUT = pathlib.Path("/root/marfagenez/_dip26_txt")


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


queries = [
    "all:\"age replacement policy\" AND all:cost",
    "all:\"repair cost limit\"",
    "all:\"preventive maintenance\" AND all:\"cost rate\"",
    "all:\"imperfect maintenance\" AND all:optimization",
    "all:\"replacement policy\" AND all:maintenance AND all:cost",
]
seen = {}
for q in queries:
    u = "http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&start=0&max_results=25"
    try:
        data = get(u).decode("utf-8", "replace")
    except Exception as e:
        print("ERR", q, e)
        continue
    entries = re.findall(r"<entry>(.*?)</entry>", data, re.S)
    print("===", q, len(entries))
    for e in entries:
        aid = re.search(r"<id>(.*?)</id>", e).group(1).strip()
        title = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
        pub = re.search(r"<published>(.*?)</published>", e).group(1)[:10]
        doi = re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", e)
        seen[aid] = {"id": aid, "title": title, "published": pub, "doi": doi.group(1) if doi else None}
        print(pub, aid.split("/abs/")[-1], "|", title[:90])
json.dump(seen, open("/root/marfagenez/_dip26_arxiv.json", "w"), indent=1)
print("TOTAL", len(seen))
