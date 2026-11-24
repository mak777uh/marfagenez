import urllib.request,time
pmcs=['PMC3258602','PMC4813294','PMC5291838','PMC2709554','PMC4854554']
for pmc in pmcs:
    ok=False
    for attempt in range(2):
        for url in ['https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML'%pmc]:
            try:
                r=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
                t=urllib.request.urlopen(r,timeout=120).read().decode('utf-8','replace')
                open('scratch/dip59/%s.xml'%pmc,'w').write(t); print(pmc,'OK',len(t)); ok=True; break
            except Exception as e:
                print(pmc,'ERR',e)
        if ok: break
        time.sleep(2)