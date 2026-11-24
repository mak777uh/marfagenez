import json
p='literature/dips/reports/dip-2026-11-24-59.jsonl'
lines=open(p,encoding='utf-8').read().splitlines()
out=[]
for line in lines:
    d=json.loads(line)
    if d['atom']=='DIP59-0006':
        d['works'][0]['quote']=("cells treated with high (500 mGy, 2.7 +/- 0.8 h) and low (5 and 10 mGy, "
                                "3.1 +/- 0.5 and 3.5 +/- 0.7 h, respectively) dose gamma-radiation")
    out.append(json.dumps(d,ensure_ascii=False))
open(p,'w',encoding='utf-8').write('\n'.join(out)+'\n')
for line in out:
    d=json.loads(line)
    print(d['atom'],len(d['works'][0]['quote'].split()))