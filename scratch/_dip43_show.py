import json
m = json.load(open('/root/marfagenez/_dip43_meta.json'))
keep = ["10.1101/gr.969603","10.1214/09-aoas297","10.1186/s13100-019-0162-7","10.1371/journal.pgen.1000530",
        "10.1534/genetics.118.301456","10.1016/j.cell.2012.06.018","10.1371/journal.pgen.1003773",
        "10.1126/science.1212959","10.1186/1471-2229-2-11","10.1186/s13148-021-01132-3","10.1371/journal.pbio.1001075"]
for d in keep:
    v = m[d]
    print('=' * 100)
    print(d, '|', v['year'], '|', v['title'])
    print(v['abs'])
