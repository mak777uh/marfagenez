import json, os, re, sys, time, urllib.request

OUTDIR = "/root/marfagenez/scratch/dip56_txt"
os.makedirs(OUTDIR, exist_ok=True)

targets = json.load(open(sys.argv[1]))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dip-researcher/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")

def xml2text(x):
    x = re.sub(r"<(ref-list|back|front)[^>]*>.*?</\1>", " ", x, flags=re.S)
    x = re.sub(r"<xref[^>]*>[^<]*</xref>", " ", x)
    x = re.sub(r"<[^>]+>", " ", x)
    x = x.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#x000a0;", " ")
    x = re.sub(r"[ \t]+", " ", x)
    return x

for t in targets:
    label, pmcid = t["label"], t["pmcid"]
    path = os.path.join(OUTDIR, label + ".txt")
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        print("cached", label, os.path.getsize(path)); continue
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid
    try:
        raw = fetch(url)
        txt = xml2text(raw)
        open(path, "w").write(txt)
        print("ok", label, pmcid, len(txt))
    except Exception as e:
        print("FAIL", label, pmcid, repr(e))
        open(path + ".err", "w").write(repr(e))
    time.sleep(1)
