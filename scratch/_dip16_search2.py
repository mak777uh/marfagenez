import json, subprocess, pathlib
exec(open("_dip16_search.py").read().split("QUERIES=")[0])
pool=json.load(open("_dip16_pool.json"))
Q2=["oleic acid vesicle membrane permeability nutrients measured",
"permeability of fatty acid vesicles to nucleotides and sugars",
"protopcell division retention of encapsulated contents daughters",
"vesicle growth rate micelle addition measured kinetics",
"coacervate microdroplet division fuel concentration enzymatic",
"competition between vesicles for fatty acids selection growth rate",
"osmotic pressure threshold giant vesicle division measured",
"membrane lipid synthesis energy cost per lipid molecule",
"fatty acid vesicle encapsulation leakage small molecules",
"protocell division asymmetry daughter size distribution measured",
"thermodynamics of fatty acid vesicle growth entropy micelle",
"coacervate protocell growth division fuel driven non-equilibrium"]
new=0
for q in Q2:
    for page in (1,2):
        d=get("https://api.openalex.org/works",{"search":q,"per_page":"25","page":str(page),
          "select":"id,doi,title,publication_year,abstract_inverted_index","api_key":KEY})
        if "__err" in d: print("ERR",q,d["__err"][:150]); continue
        for w in d.get("results",[]):
            doi=(w.get("doi") or "").replace("https://doi.org/","").lower()
            a=absx(w.get("abstract_inverted_index"))
            if not doi or not a or doi in pool: continue
            pool[doi]={"doi":doi,"title":w.get("title"),"year":w.get("publication_year"),"abstract":a,"queries":[q]}
            new+=1
print("NEW",new,"POOL",len(pool))
pathlib.Path("_dip16_pool.json").write_text(json.dumps(pool,ensure_ascii=False,indent=1))
