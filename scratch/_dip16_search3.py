import json, subprocess, pathlib
exec(open("_dip16_search.py").read().split("QUERIES=")[0])
pool=json.load(open("_dip16_pool.json"))
Q3=["kinetic study of the growth of fatty acid vesicles",
"physical effects underlying the transition from primitive to modern cell membranes",
"thermostability of model protocell membranes",
"permeability of oleic acid vesicles to ribose glycine sugars",
"nutrient uptake by model protocells myristoleic acid membrane",
"growth and shape transformations of giant phospholipid vesicles upon interaction with micelles",
"osmotic deflation division giant unilamellar vesicles threshold",
"active coacervate droplets fuel driven division ATP",
"protocell competition growth rate fatty acid vesicles selection experiment",
"concentration of fatty acid needed for vesicle growth critical aggregate concentration",
"division threshold surface area to volume ratio fatty acid vesicle",
"energy cost of phospholipid synthesis per molecule cells"]
new=0
for q in Q3:
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
