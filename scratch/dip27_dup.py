import json, os, glob
dois = ["10.1111/are.13621","10.3354/ab00626","10.1098/rsbl.2004.0171","10.1186/1471-2148-13-68",
"10.3389/fnmol.2017.00101","10.1111/j.1474-9726.2006.00261.x","10.1093/jmedent/47.5.769",
"10.1098/rspb.2005.3057","10.1371/journal.pone.0211605","10.1101/2025.07.09.663850",
"10.1111/j.1365-2435.2008.01507.x","10.1111/1365-2435.12130"]
base='/root/marfagenez'
files=[base+'/literature/map/atoms.jsonl']+glob.glob(base+'/literature/dips/reports/*.jsonl')
hits={d:[] for d in dois}
for f in files:
    try: txt=open(f, errors='replace').read()
    except: continue
    for d in dois:
        if d in txt:
            hits[d].append(os.path.basename(f))
for d,v in hits.items():
    print(d,'->',v if v else 'NEW')
