import json,sys
pool=json.load(open("_dip16_pool.json"))
todo=["10.1002/smll.202406241","10.1021/jacsau.0c00079","10.1021/ja202406v","10.1002/anie.202014174","10.1038/s41557-021-00830-y","10.1039/c9sc05195c","10.1038/s41598-018-36183-9","10.1073/pnas.1203212109","10.1021/ja310382d","10.1162/isal_a_00722","10.1021/acs.jpcb.5b05057","10.3390/life12101635","10.1016/j.isci.2020.101677","10.1021/acsnano.6c03241","10.26434/chemrxiv.15010013/v2","10.3390/life5010181","10.1021/acs.langmuir.2c02118","10.1002/anie.201710708"]
for d in todo:
    w=pool.get(d)
    if not w: print("== MISSING",d); continue
    print("="*100); print(d,"|",w["year"],"|",w["title"]); print(w["abstract"][:1600])
