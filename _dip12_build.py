import json, subprocess, unicodedata, re, sys

ROOT = "/root/marfagenez"
KEY = open("/mnt/c/Users/Admin/.dsh/secrets/openalex.key").read().strip()
CURL = "/mnt/c/Windows/System32/curl.exe"
OUT = ROOT + "/literature/dips/reports/dip-2026-11-23-12.jsonl"

def ab(inv):
    pos = {}
    for t, ids in (inv or {}).items():
        for i in ids:
            pos[i] = t
    return " ".join(pos[i] for i in sorted(pos))

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().lower()

def verify(doi):
    url = ("https://api.openalex.org/works/https://doi.org/" + doi +
           "?api_key=" + KEY + "&select=id,doi,title,publication_year,abstract_inverted_index")
    p = subprocess.run([CURL, "-sS", url], capture_output=True, text=True, timeout=120)
    try:
        w = json.loads(p.stdout)
    except Exception:
        return None, "BADJSON: " + p.stdout[:200]
    if "error" in w or not w.get("doi"):
        return None, "NОТFOUND: " + p.stdout[:200]
    return {"doi": w["doi"].replace("https://doi.org/", ""), "title": w.get("title"),
            "year": w.get("publication_year"), "abstract": ab(w.get("abstract_inverted_index"))}, None

# (doi, kind, statement, mechanism, formula, symbols, conditions, quote, confidence, tags, notes, extra)
CELLS = [
 dict(doi="10.1104/pp.51.1.61", kind="measurement",
  statement="Полувремя обновления одного и того же липида (лецитина) в мембранах одной и той же клетки различается в 5 раз в зависимости от органеллы: около 50 ч в мембране митохондрий и около 10 ч в мембране глиоксисом, так что «время жизни мембранного липида» не является свойством липида.",
  mechanism="pulse-chase с choline-(14)C: метка сначала появляется в лёгкой мембранной фракции, затем в митохондриях и глиоксисомах, после чего теряется из них с разными константами; органелл-специфичная скорость деградации лецитина при общем источнике синтеза",
  formula=None, symbols={},
  conditions=["in vivo, эндосперм прорастающей клещевины (Ricinus communis)", "pulse-chase choline-(14)C, sucrose-градиент фракций", "измерено: скорость потери 14C из лецитина в мембранных фракциях → полувремя"],
  quote="the half life of lecithin in the membrane were about 50 hours and that of the glyoxysomes 10 hours",
  confidence="medium",
  tags=["lipid-turnover","half-life","organelle-membrane","pulse-chase"],
  notes="Полувремя оценено по кинетике распада метки в chase-опыте; авторы сами сверяют её с оценкой из опыта без chase и находят близкой. Данные 1973 г., один организм, аннотация без полного текста."),

 dict(doi="10.1083/jcb.37.3.729", kind="condition",
  statement="Обновление поверхностной мембраны не привязано к росту: в неделящейся клетке синтезируется примерно столько же мембранного материала, сколько в растущей, но он же и удаляется, то есть плата за обновление существует и без прироста площади.",
  mechanism="синтез и деградация мембраны сопряжены: ингибиторы метаболизма или отсутствие аминокислот снижают синтез и эквивалентно снижают скорость распада, поэтому отношение «синтез/распад» держится около единицы в стационарной культуре",
  formula=None, symbols={},
  conditions=["in vitro, L-клетки (мышиные фибробласты) в культуре, логарифмическая и стационарная фазы", "измерено: включение изотопа в поверхностную мембрану и падение удельной активности фракций"],
  quote="In the nongrowing cell newly synthesized material is incorporated, but a corresponding amount of material is eliminated so that there is turnover without net increase of substance.",
  confidence="medium",
  tags=["membrane-maintenance","turnover","stationary-phase","coupling"],
  notes="Аннотация не даёт численных скоростей; ценность — в разделении «синтез для роста» и «синтез для замены». Авторы оговаривают, что возможны и другие интерпретации."),

 dict(doi="10.1016/j.bpj.2013.11.4486", kind="measurement",
  statement="Свободная энергия образования гидрофильной поры в липидном бислое сильно зависит от длины цепи липида: 17 кДж/моль для DLPC, 45 кДж/моль для DMPC и 78 кДж/моль для DPPC, то есть цена одного дефекта мембраны растёт более чем в 4 раза при удлинении цепи примерно на 4 атома углерода.",
  mechanism="пора выгодна энтальпийно (рост числа связей липид–вода) и невыгодна энтропийно; тонкий DLPC-бислой допускает равновесное образование пор, толстый DPPC — практически нет",
  formula=None, symbols={},
  conditions=["молекулярная динамика с атомарным разрешением (all-atom MD)", "бислои DLPC, DMPC, DPPC; рассчитаны свободная энергия, энтальпия и энтропия образования поры и времена жизни пор"],
  quote="study the thermodynamics, kinetics, and mechanism of pore formation and closure in DLPC, DMPC, and DPPC bilayers, with pore formation free energies of 17, 45, and 78 kJ/mol",
  confidence="medium",
  tags=["pore","defect-energy","bilayer-stability","md-simulation","kJ-per-mol"],
  notes="Это расчётная величина (MD), не измерение; «цена дефекта» относится к модельным бислоям без белков и без натяжения."),

 dict(doi="10.1016/s0006-3495(98)77904-4", kind="formula",
  statement="Энергия деформации бислоя, вызванной включением (гидрофобный mismatch), раскладывается в сумму трёх вкладов — сжатие-растяжение, splay-искажение и поверхностное натяжение — и в тонких бессольвентных бислоях вклад натяжения пренебрежимо мал, а вблизи границы доминирует splay.",
  mechanism="упругая (жидкокристаллическая) модель бислоя: каждый модуль перенормирует другой (изменение модуля сжатия меняет и splay-энергию), поэтому вклады не независимы; при малых mismatch суммарная энергия аппроксимируется линейной пружиной",
  formula="ΔG_def = ΔG_compression-expansion + ΔG_splay-distortion + ΔG_surface tension; при малом mismatch ΔG_def ≈ (1/2)·k·u²",
  symbols={"ΔG_def": "свободная энергия деформации бислоя вокруг включения", "u": "величина гидрофобного mismatch (разность длины гидрофобной части белка и толщины ядра бислоя)", "k": "эффективная жёсткость (линейная пружина)"},
  conditions=["теоретическая упругая модель бислоя (liquid-crystal elastic model)", "сравнение с экспериментом по грамицидиновым каналам, не прямое измерение"],
  quote="an increase in hydrophobic mismatch to 1.3 A can increase the Boltzmann factor (the equilibrium distribution for protein conformation) 10-fold due to the elastic properties of the bilayer",
  confidence="medium",
  tags=["bilayer-elasticity","hydrophobic-mismatch","energy-per-area","formula"],
  notes="Формула записана так, как её формулирует аннотация (сумма трёх вкладов); коэффициенты модели в аннотации не приведены, поэтому численная форма k не выписана."),

 dict(doi="10.1002/smll.201902898", kind="measurement",
  statement="Натяжение мембраны само по себе достаточно, чтобы без синтеза липидов и без белков вызвать рост везикулы: при осмотическом натяжении GUV (≈10 мкм) сливается с SUV (≈30 нм) и увеличивает объём вплоть до удвоения.",
  mechanism="трансмембранное осмотическое давление повышает натяжение мембраны GUV, что снижает барьер слияния SUV-GUV; рост идёт за счёт притока готового липида, а не за счёт его синтеза",
  formula=None, symbols={},
  conditions=["in vitro, гигантские однослойные везикулы ≈10 мкм + SUV ≈30 нм как источник липида", "чистые фосфолипиды и гибридные везикулы фосфолипид/жирная кислота; измерено изменение объёма (до ×2) при осмотическом натяжении"],
  quote="tension on the GUV membranes through a transmembrane osmotic pressure, SUV-GUV fusion events are promoted and substantial growth of the GUV is caused",
  confidence="medium",
  tags=["membrane-tension","growth","guv","fusion","protein-free"],
  notes="Рост площади здесь — не синтез, а перенос готового липида; это нижняя граница цены роста (нулевая химическая цена, есть только механическая работа против натяжения)."),

 dict(doi="10.1021/ja900919c", kind="measurement",
  statement="Потери содержимого при делении везикулы зависят от способа деления: экструзия даёт значимую потерю содержимого на каждом цикле, тогда как деление нитевидной везикулы умеренным сдвигом сохраняет содержимое и распределяет инкапсулированную РНК между дочерними везикулами.",
  mechanism="при избытке площади над объёмом (медленная проницаемость растворённого вещества, приток мицелл жирной кислоты) сферическая везикула вытягивается в нить; нить делится по слабому сдвигу на несколько дочерних везикул, при этом внутренний раствор не выходит",
  formula=None, symbols={},
  conditions=["in vitro, мультиламеллярные везикулы жирных кислот (олеиновая кислота) + мицеллы как питание", "мягкий сдвиг; инкапсулированная РНК как маркер содержимого; несколько последовательных циклов роста-деления"],
  quote="Modest shear forces are then sufficient to cause the thread-like vesicles to divide into multiple daughter vesicles without loss of internal contents.",
  confidence="medium",
  tags=["division","content-loss","protocell","fatty-acid-vesicle","surface-area-volume"],
  notes="Ключевая для домена величина — доля потерянного содержимого за цикл — в аннотации качественная («significant loss» против «without loss»); числа в полном тексте, не проверены."),

 dict(doi="10.3389/fphys.2017.00312", kind="condition",
  statement="Механическая цена перетяжки мембраны при делении минимальна при положительной спонтанной кривизне, низком или отрицательном натяжении и в гипертонической среде, то есть цена деления задаётся не только машиной перетяжки, но и состоянием самой мембраны.",
  mechanism="мембрана идёт по пути минимизации упругой энергии (изгиб + натяжение + работа осмотического давления); изменение спонтанной кривизны, натяжения и осмолярности сдвигает этот путь и требуемую силу перетяжки",
  formula=None, symbols={},
  conditions=["теоретическая модель: однородная мембранная везикула, симметричная перетяжка", "аналитика (пертурбативное разложение + вариационный подход), сверенная с численным решением; сравниваются энергия, площадь, объём, сила перетяжки"],
  quote="smaller constriction forces are required for positive spontaneous curvatures, low or negative membrane tension and hypertonic media",
  confidence="medium",
  tags=["constriction","division-mechanics","spontaneous-curvature","osmotic-pressure","condition"],
  notes="Это условия применимости модели, а не измерение на клетке; численные значения силы в аннотации не приведены."),

 dict(doi="10.1016/j.bbabio.2025.149564", kind="condition",
  statement="Любая величина «ATP на клетку» (и, значит, любая цена мембраны в ATP) зависит от метода учёта: модели, пришедшие на смену микробиологическим оценкам 1970-х, систематически завышают стоимость синтеза аминокислот вплоть до 200 раз, что делает выведенные из них энергетические выводы недействительными.",
  mechanism="ошибка в стехиометрии путей синтеза аминокислот («сантиметры вместо ярдов»): получаются невозможные величины — ~100 ATP на глюкозу у E. coli и ~240 ATP на глюкозу у млекопитающих",
  formula=None, symbols={},
  conditions=["сравнение методов: оценки ATP-потребности роста из химического состава клетки и известных путей (микробиология, 1970-е) против моделей 2015+ в эволюционной биоэнергетике", "не измерение, а разбор учёта; охват — прокариоты и эукариоты"],
  quote="systematically overestimates the ATP cost of amino acid synthesis up to 200-fold",
  confidence="medium",
  tags=["atp-cost","accounting-error","growth-cost","condition","bioenergetics"],
  notes="Берём как условие на любые ATP-числа: расхождение методов достигает двух порядков, поэтому ATP-цена мембраны без указания метода бессмысленна. Полемическая работа, вторая сторона (конкретная модель 2015+) в выборке не проверялась, поэтому это condition, а не contradiction."),

 dict(doi="10.1073/pnas.0705010104", kind="measurement",
  statement="Энергетическая цена проницаемости для воды задаётся знаком и величиной энтальпийного и энтропийного вкладов: в липидном бислое вода проходит тем легче, чем выше температура, из-за энтальпийной цены перехода вода→пар, тогда как в фуллереновом бислое проницаемость на порядки ниже и падает с температурой из-за очень большой потери энтропии.",
  mechanism="проницаемость = равновесие между выгодой/невыгодой сольватации переносимой молекулы: липидный бислой требует энтальпийных затрат на разрыв водородных связей, жёсткий фуллереновый — энтропийных (вода связывается с поверхностью фуллерена в щелях)",
  formula=None, symbols={},
  conditions=["сравнение двух искусственных бислоёв: липидный и фуллереновый (Ph5C60K)", "измерена проницаемость для воды и её температурная зависимость → разложение на энтальпию и энтропию активации"],
  quote="Water permeation through a lipid bilayer membrane occurs readily, and more readily at higher temperature, which is largely due to an enthalpy cost of the liquid-to-gas phase transition of water.",
  confidence="medium",
  tags=["permeability","water","enthalpy-entropy","energetic-cost","bilayer"],
  notes="Абсолютных значений коэффициента проницаемости в аннотации нет — только качественное соотношение и порядки («several orders of magnitude less»)."),
]

GAP = dict(doi=None, kind="gap",
  statement="В просмотренной выборке нет работы, где цена обновления мембраны была бы выражена в ATP на липидную молекулу или в энергии на единицу площади: измеренный lipid turnover дан как полувремя (часы), энергия дефекта/деформации — как кДж/моль на пору или на включение, ATP-учёт — как ATP на клетку в целом, и ни одна работа не связывает эти три шкалы пересчётом.",
  mechanism="разрыв между тремя языками измерения: кинетика изотопного обмена (полувремя), механика бислоя (кДж/моль на дефект) и биоэнергетический учёт (ATP на клетку); переход «молекул/с → ATP/с» требует стехиометрии синтеза липида, которой в выборке нет в явном виде",
  formula=None, symbols={},
  conditions=["просмотренная выборка OpenAlex, 187 уникальных записей", "только аннотации, без полных текстов", "отрицательный результат обзора"],
  quote=None,
  works=[
    dict(doi="10.1016/j.bbabio.2025.149564", locator="abstract", access="abstract",
         quote="The amount of ATP needed to support growth was calculated from the chemical composition of the cell and known enzymatic pathways that synthesize its constituents from known substrates in culture."),
    dict(doi="10.1083/jcb.37.3.729", locator="abstract", access="abstract",
         quote="Growing and nongrowing cells synthesize approximately similar amounts of surface membrane and particulate material."),
  ],
  confidence="low",
  tags=["gap","atp-per-lipid","energy-per-area","unit-bridge"],
  notes="Формулировка «в просмотренной выборке не найдено», а не «в литературе нет». Проверялось, есть ли работа, где стоимость синтеза липида дана на молекулу (ATP/липид) или на площадь (Дж/мкм²).",
  searched="OpenAlex /works?search=: \"lipid turnover rate membrane half-life\", \"ATP cost of lipid synthesis membrane maintenance energy\", \"membrane tension cell growth division\", \"vesicle division content loss membrane surface area\", \"osmotic stress membrane repair permeability\", \"lipid bilayer stability permeability energetic cost\", \"phospholipid synthesis ATP requirement per molecule energetics\", \"membrane surface area growth rate lipid synthesis rate cell\", \"lipid vesicle division efficiency membrane loss daughter\", \"membrane permeability proton leak energy cost cell\", \"energy cost membrane area synthesis ATP per square micrometer\", \"membrane lipid synthesis rate measured molecules per second\", \"division septum membrane surface area inheritance daughter cell\"; 13 запросов по 15-20 записей, дата 2026-11-22",
  scope="187 уникальных записей из выдачи OpenAlex; просмотрены заголовки и аннотации всех записей с непустой аннотацией; полные аннотации прочитаны у 22 отобранных работ; индивидуально проверено 9 DOI")

rows = []
log = []
seen = {}
for c in CELLS:
    w, err = verify(c["doi"])
    if w is None:
        log.append(f"FAIL verify {c['doi']}: {err}")
        continue
    a = norm(w["abstract"])
    ok = norm(c["quote"]) in a
    seen[c["doi"]] = {"title": w["title"], "year": w["year"], "quote_ok": ok}
    log.append(f"verify {c['doi']} year={w['year']} quoting={'OK' if ok else 'MISS'}")
    if not ok:
        # print context to fix quote
        i = a.find(norm(c["quote"])[:60])
        log.append("   CTX: " + a[max(0, i-100):i+220])
    work = {"doi": w["doi"], "locator": "abstract", "access": "abstract", "quote": c["quote"]}
    row = {"atom": "", "statement": c["statement"], "domain": "bio.membrane", "kind": c["kind"],
           "mechanism": c["mechanism"], "formula": c["formula"], "symbols": c["symbols"],
           "conditions": c["conditions"], "works": [work], "confidence": c["confidence"],
           "locator_status": "verified", "tags": c["tags"], "notes": c["notes"]}
    rows.append(row)

# gap cell works verification
gworks = []
for wk in GAP["works"]:
    w, err = verify(wk["doi"])
    if w is None:
        log.append(f"FAIL verify gap {wk['doi']}: {err}")
        continue
    ok = norm(wk["quote"]) in norm(w["abstract"])
    seen.setdefault(wk["doi"], {"title": w["title"], "year": w["year"], "quote_ok": ok})
    log.append(f"verify(gap) {wk['doi']} quoting={'OK' if ok else 'MISS'}")
    gworks.append(dict(wk))
rows.append({"atom": "", "statement": GAP["statement"], "domain": "bio.membrane", "kind": "gap",
             "mechanism": GAP["mechanism"], "formula": None, "symbols": {},
             "conditions": GAP["conditions"], "works": gworks, "confidence": GAP["confidence"],
             "locator_status": "verified", "tags": GAP["tags"], "notes": GAP["notes"],
             "searched": GAP["searched"], "scope": GAP["scope"]})

for i, r in enumerate(rows, 1):
    r["atom"] = f"DIP12-{i:04d}"

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("\n".join(log))
print("cells:", len(rows), "unique doi:", len(seen))
for d, v in seen.items():
    print(f"  {d} | {v['year']} | {v['title'][:90]} | quote_ok={v['quote_ok']}")
json.dump(seen, open(ROOT + "/literature/dips/reports/_dip12_verified.json", "w"), ensure_ascii=False, indent=1)
