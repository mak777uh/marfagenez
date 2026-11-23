import json, subprocess, pathlib
KEY=pathlib.Path("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read_text().strip()
CURL="/mnt/c/Windows/System32/curl.exe"
def get(url,params):
    a=[CURL,"-sS","-G",url]
    for k,v in params.items(): a+=["--data-urlencode",f"{k}={v}"]
    r=subprocess.run(a,capture_output=True,text=True)
    return json.loads(r.stdout) if r.returncode==0 else {"__err":r.stderr[:200]}
def absx(inv):
    pos={}
    for w,idx in (inv or {}).items():
        for i in idx: pos[i]=w
    return " ".join(pos[i] for i in sorted(pos))
DOIS="""10.1021/ja202406v
10.1021/acs.jpcb.5b05057
10.1002/smll.202406241
10.1039/c9sc05195c
10.1002/anie.202014174
10.1038/s41467-021-24111-x
10.1038/s41467-020-18815-9
10.1038/s41557-021-00830-y
10.1073/pnas.2221064120
10.1038/s41598-017-02799-6
10.1021/ja310382d
10.1038/srep05675
10.1002/smll.202002529
10.1038/nphys3984
10.1021/jacs.4c08226
10.1016/j.bpj.2010.06.057
10.1021/la503933x
10.1021/acsnano.6c03241""".split()
out={}
for d in DOIS:
    w=get("https://api.openalex.org/works/https://doi.org/"+d,
          {"select":"id,doi,title,publication_year,abstract_inverted_index","api_key":KEY})
    a=absx(w.get("abstract_inverted_index"))
    ok=bool(w.get("title")) and bool(a)
    print("="*95)
    print(("OK " if ok else "FAIL ")+d,"|",w.get("publication_year"),"|",w.get("title"))
    if a: print(a)
    else: print("  [no abstract]", w.get("__err",""))
    if ok: out[d]={"doi":d,"title":w["title"],"year":w["publication_year"],"abstract":a}
pathlib.Path("_dip16_verified.json").write_text(json.dumps(out,ensure_ascii=False,indent=1))
print("\nVERIFIED",len(out),"of",len(DOIS))
