import json,re
pool=json.load(open("_dip16_pool.json"))
pat=re.compile("kinetic|permeab|nutrient|thermostab|micelle|deflation|coacervate|competition|surface area|energetic|cost|model protocell",re.I)
rows=[w for d,w in pool.items() if pat.search((w["title"] or ""))]
print("HITS",len(rows))
for w in rows[:40]:
    print(w["year"],"|",w["doi"],"|",(w["title"] or "")[:95])
