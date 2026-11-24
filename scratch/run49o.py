import json, re, sys, urllib.parse, urllib.request
sys.path.insert(0, "/root/marfagenez/scratch")

KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
UA = {"User-Agent": "marfagenez-dip/1.0 (mailto:marfagenez@proton.me)"}

DOIS = [
    "10.1038/bjc.1995.62",
    "10.3390/ijms21249488",
    "10.1186/s13059-018-1582-2",
    "10.1074/mcp.M111.011429",
    "10.1038/s41467-021-26842-3",
    "10.1083/jcb.96.1.1",
    "10.1083/jcb.131.6.1747",
    "10.1080/15548627.2022.2117515",
    "10.7554/eLife.50260",
    "10.1083/jcb.201512022",
]

print("### VERIFY via OpenAlex")
for d in DOIS:
    url = "https://api.openalex.org/works/https://doi.org/%s?api_key=%s&mailto=marfagenez@proton.me" % (d, KEY)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            w = json.load(r)
        print("OK", d, "|", w.get("title")[:90], "|", w.get("publication_year"), "|", ((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
    except Exception as e:
        print("FAIL", d, repr(e))
