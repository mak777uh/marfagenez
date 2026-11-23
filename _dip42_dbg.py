import urllib.request,urllib.parse,json
KEY=open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
for filt in ["cites:10.1021/ja900919c","cites:https://doi.org/10.1021/ja900919c","cites:10.1021/ja900919c,has_abstract:true"]:
    for extra in [{"mailto":"dip@marfagenez.local","api_key":KEY},{"mailto":"dip@marfagenez.local"}]:
        url="https://api.openalex.org/works?"+urllib.parse.urlencode(dict(filter=filt,per_page=5,**extra))
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"m"})
            d=json.loads(urllib.request.urlopen(req,timeout=60).read())
            print("OK",filt,"key" if "api_key" in extra else "nokey",d["meta"]["count"])
        except Exception as e:
            print("ERR",filt,"key" if "api_key" in extra else "nokey",e)
