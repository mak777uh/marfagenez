import importlib.util, json, pathlib
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

Q = {
 "Bi2": '("Biot number") AND (cryopreservation OR tissue OR organ OR insect OR tumor OR skin OR "heat transfer") AND OPEN_ACCESS:y',
 "Kn2": '("Knudsen number") AND (insect OR trachea OR leaf OR xylem OR "gas exchange" OR respiration) AND OPEN_ACCESS:y',
 "De2": '("Deborah number") AND (blood OR mucus OR saliva OR sputum OR plasma OR thrombus) AND OPEN_ACCESS:y',
 "Pe3": '("Peclet number" OR "Péclet number") AND (embryo OR "limb bud" OR somite OR zebrafish OR xenopus) AND OPEN_ACCESS:y',
}
for k, q in Q.items():
    res = e.epmc_search(q, 100)
    print("=====", k, len(res))
    for i, r in enumerate(res[:60]):
        print(f"{i:3d} {r.get('pubYear')} {str(r.get('pmcid')):12s} {str(r.get('doi'))[:30]:30s} {(r.get('title') or '')[:88]}")
