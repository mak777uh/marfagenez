import re

files = {
 "10.1038/bjc.1995.62": "PMC2033588",
 "10.3390/ijms21249488": "PMC7764904",
 "10.1186/s13059-018-1582-2": "PMC6284305",
 "10.1074/mcp.M111.011429": "PMC3316722",
 "10.1038/s41467-021-26842-3": "PMC8626426",
 "10.1083/jcb.96.1.1": "PMC2112240",
 "10.1080/15548627.2022.2117515": "PMC10012960",
 "10.1083/jcb.201512022": "PMC4915191",
 "10.7554/eLife.50260": "PMC6959996",
}

QUOTES = {
 "10.1038/bjc.1995.62": [
   "The half-time (t1/2) of rejoining ranged from 18.0 +/- 1.4 to 36.4 +/- 3.2 min (fast rejoining process)",
   "and from 1.5 +/- 0.2 to 5.1 +/- 0.2 h (slow rejoining process)",
 ],
 "10.3390/ijms21249488": [
   "with low linear energy transfer (LET) radiation (17.6 and 16.4 foci/Gy/cell, respectively)",
   "The repair of simple, i.e., single DSBs, is carried out very fast (15 min repair half-time)",
   "while the repair of complex DSBs, i.e., complicated by other lesions, performed slowly (10 to 15 h repair half-time)",
 ],
 "10.1186/s13059-018-1582-2": [
   "At background levels, a human cell is estimated to undergo 100 to 500 such modifications per day",
   "At steady state, up to 2400 8-oxoG sites per cell are reported",
   "Glycohydrolysis is highly efficient, with an 8-oxoG half-life of 11 min",
 ],
 "10.1074/mcp.M111.011429": [
   "The average turnover rate for HeLa proteins was",
   "it takes",
   "for 50% turnover of the total HeLa proteome",
 ],
 "10.1038/s41467-021-26842-3": [
   "The median half-life for each tissue ranged from 3.6 d for liver to 10 d for skeletal muscle",
 ],
 "10.1083/jcb.96.1.1": [
   "was being interiorized per minute",
   "0.9% of the cell surface pe",
   "corresponding to 3.1% of the",
 ],
 "10.1080/15548627.2022.2117515": [
   "This basal rate was estimated to be 0.90 puncta per cell per minute",
   "were estimated to be 0.685 puncta per cell per minute and 1.1 nM",
 ],
 "10.1083/jcb.201512022": [
   "were rapidly recruited to the site of laser wounding and were seen between 4 and 14 s",
 ],
 "10.7554/eLife.50260": [
   "we see on average ~1-5 events per cell",
   "remained in non-acidified organelles for hours to days",
 ],
}

for doi, pmc in files.items():
    txt = open("/root/marfagenez/scratch/ft49_%s.txt" % pmc).read() if pmc not in ("PMC6959996",) else open("/root/marfagenez/scratch/PMC6959996.txt").read()
    print("###", doi, pmc)
    for q in QUOTES[doi]:
        ok = q in txt
        print("  ", "OK " if ok else "MISS", repr(q[:70]))
        if not ok:
            # fuzzy: find similar
            key = q[:25]
            m = re.search(re.escape(key[:18]), txt)
            if m:
                print("      near:", repr(txt[max(0,m.start()-60):m.start()+240]))
