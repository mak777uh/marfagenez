import urllib.request,sys,re
def ft(pmc):
    u='https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML'%pmc
    r=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
    return urllib.request.urlopen(r,timeout=120).read().decode('utf-8','replace')
for pmc in ['PMC13182976','PMC5546504','PMC4854554']:
    try:
        t=ft(pmc); open('scratch/dip59/%s.xml'%pmc,'w').write(t); print(pmc,'OK',len(t))
    except Exception as e:
        print(pmc,'ERR',e)