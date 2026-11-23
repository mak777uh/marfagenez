import urllib.request, pathlib, re

UA = {"User-Agent": "marfagenez-research/1.0 (mailto:research@example.org)"}
OUT = pathlib.Path("/root/marfagenez/_dip26_txt")
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"

ids = ["PMC13591397", "PMC7618562"]
for pid in ids:
    try:
        req = urllib.request.Request(BASE + pid + "/fullTextXML", headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            xml = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(pid, "FAIL", str(e)[:80])
        continue
    (OUT / (pid + ".xml")).write_text(xml, encoding="utf-8")
    txt = re.sub(r"<[^>]+>", " ", xml)
    txt = re.sub(r"[ \t]+", " ", txt)
    (OUT / (pid + ".txt")).write_text(txt, encoding="utf-8")
    print("=" * 20, pid, len(txt))
    for pat in [r"cost per unit time", r"optimal", r"turnover rate", r"model", r"per day"]:
        ms = list(re.finditer(pat, txt, re.I))[:3]
        for m in ms:
            s = max(0, m.start() - 160)
            print(f"  [{pat}]", txt[s:m.end() + 240].replace("\n", " ")[:400])
