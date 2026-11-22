import json, pathlib, re, sys, unicodedata

V = json.load(open("/root/marfagenez/_dip16_verified.json", encoding="utf-8"))

def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-")
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def w(doi, quote):
    return {"doi": doi, "locator": "abstract", "access": "abstract", "quote": quote,
            "title": V[doi]["title"], "year": V[doi]["year"]}

D = "bio.protocell"
ATOMS = [
 {
  "atom": "DIP16-0001",
  "statement": "При делении модельной клетки — гигантской липидной везикулы размером 10–30 мкм с внутренней двухфазной системой PEG/декстран — содержимое распределяется по границе водно-водной фазовой сепарации: одна дочерняя везикула получает PEG-богатую фазу, другая — декстран-богатую.",
  "domain": D, "kind": "measurement",
  "mechanism": "Разделение объёма идёт по границе уже существующей фазовой сепарации, поэтому состав дочерних везикул задан фазовой диаграммой полимеров, а не случайным разрывом мембраны: «потеря содержимого» здесь превращается в детерминированное разделение, а не в утечку.",
  "formula": None, "symbols": {},
  "conditions": ["гигантские липидные везикулы (GUV) 10–30 мкм", "внутренняя ATPS PEG/декстран", "трёхкомпонентная липидная смесь с сосуществующими доменами L(d)/L(o)", "осмотическое давление повышают добавлением сахарозы снаружи", "in vitro, флуоресцентная микроскопия"],
  "works": [w("10.1021/ja202406v", "one daughter vesicle contained the PEG-rich aqueous phase and the other contained the dextran-rich aqueous phase")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["division", "content-partitioning", "atps", "asymmetry", "giant-vesicles"],
  "notes": "Измерена не доля потерянного содержимого, а факт детерминированного разделения фаз; численные доли каждой фазы в дочерних везикулах в аннотации не приведены."
 },
 {
  "atom": "DIP16-0002",
  "statement": "Путь роста POPC-везикул при добавлении мицелл олеата переключается по молярной доле олеата: ниже 0,35 преобладает простое включение олеата в материнскую везикулу, а выше 0,35 из материнской POPC-везикулы образуются олеат-богатые и олеат-бедные дочерние везикулы.",
  "domain": D, "kind": "condition",
  "mechanism": "Кооперативное поглощение свежего олеата уже олеат-богатыми областями мембраны: как только доля олеата превышает порог, мембрана распадается на две популяции по составу, и рост превращается в деление.",
  "formula": None, "symbols": {},
  "conditions": ["POPC-везикулы + мицеллы олеата", "порог по молярной доле олеата ок. 0,35", "методы: free-flow electrophoresis (FFE) и cryo-TEM", "in vitro"],
  "works": [w("10.1021/acs.jpcb.5b05057", "oleate-rich and oleate-poor daughter vesicles are generated from parent POPC vesicles when the oleate molar fraction exceeds 0.35")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["growth", "division", "threshold", "oleate", "phase-separation"],
  "notes": "Порог 0,35 — измеренная величина, но она относится к системе POPC/олеат, а не к чистым жирнокислотным везикулам; перенос на протоклетку из олеиновой кислоты не проверен."
 },
 {
  "atom": "DIP16-0003",
  "statement": "При росте и делении везикул, заполненных ферритином, часть дочерних везикул содержит ферритин в повышенной концентрации, а часть оказывается пустой, то есть содержимое распределяется между дочерними везикулами неравномерно.",
  "domain": D, "kind": "measurement",
  "mechanism": "Растворённое вещество перераспределяется вместе с мембранными областями разного состава: при почковании олеат-богатых и олеат-бедных дочерних везикул полость делится не поровну, и в части дочерних везикул концентрация груза падает до нуля.",
  "formula": None, "symbols": {},
  "conditions": ["POPC/олеат везикулы, заполненные ферритином", "рост после добавления мицелл олеата, деление в тех же условиях", "cryo-TEM", "in vitro"],
  "works": [w("10.1021/acs.jpcb.5b05057", "some vesicles contain ferritin at increased concentrations, others are empty")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["content-loss", "division", "encapsulation", "ferritin", "asymmetry"],
  "notes": "Аннотация даёт качественную картину (часть пустых, часть с повышенной концентрацией), но не приводит долю потерянного содержимого в процентах — это главный недостающий для карты параметр."
 },
 {
  "atom": "DIP16-0004",
  "statement": "Жирнокислотные гигантские везикулы сохраняют содержимое после гипоосмотических шоков в десять раз сильнее предсказанного порога устойчивости, тогда как фосфолипидные везикулы в тех же условиях разрываются и выпускают содержимое.",
  "domain": D, "kind": "measurement",
  "mechanism": "Мембрана вбирает дополнительные амфифилы из мелких и менее напряжённых везикул той же популяции, поэтому площадь растёт под осмотической нагрузкой и разрыва не происходит; у фосфолипидов такого резерва нет.",
  "formula": None, "symbols": {},
  "conditions": ["наноразмерные и гигантские жирнокислотные везикулы", "без дополнительного источника липидов", "сравнение с фосфолипидными системами", "in vitro, гипоосмотический шок"],
  "works": [w("10.1002/smll.202406241", "the fatty acid giant vesicles retained contents following hypoosmotic shocks ten times higher than the predicted tolerance levels")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["osmotic-stress", "content-retention", "fatty-acid-vesicles", "division", "membrane-growth"],
  "notes": "«В десять раз выше предсказанного порога» — единственное число в аннотации; какой именно порог и какая доля содержимого сохранена, требует полного текста."
 },
 {
  "atom": "DIP16-0005",
  "statement": "Самоделение гигантской везикулы требует одновременного действия двух процессов — уменьшения площади внутреннего листка мембраны из-за ухода олеата в люмен и осмотической потери объёма; ни один из них по отдельности деления не вызывает.",
  "domain": D, "kind": "condition",
  "mechanism": "Ферментативная реакция в люмене повышает pH, меняет протонирование олеиновой кислоты во внутреннем листке, и мембранный материал уходит в люмен; вместе с осмотическим сжатием объёма это даёт деление материнской везикулы на две меньшие.",
  "formula": None, "symbols": {},
  "conditions": ["гигантские везикулы из фосфатидилхолина и олеиновой кислоты", "внутренняя ферментативная реакция, поднимающая pH люмена", "внешний осмотический стресс", "in vitro"],
  "works": [w("10.1039/c9sc05195c", "These two processes must act in synergy; none of them alone can induce the division.")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["division", "oleic-acid", "osmotic-stress", "synergy", "enzymatic"],
  "notes": "Условие «оба процесса нужны» — прямой аргумент против моделей, где достаточно одного осмоса или одного изменения площади листка."
 },
 {
  "atom": "DIP16-0006",
  "statement": "Порог отношения осмолярностей, при котором фазово-разделённая гигантская однослойная везикула делится, не зависит от размера везикулы, а асимметричное деление происходит при меньших отношениях осмолярностей.",
  "domain": D, "kind": "condition",
  "mechanism": "Геометрия везикулы задаёт критическое отношение осмолярностей через соотношение площади и объёма, а не через абсолютный размер, поэтому порог масштабно-инвариантен; при меньшем отношении делится только асимметрично.",
  "formula": None, "symbols": {},
  "conditions": ["фазово-разделённые GUV", "аналитическая геометрическая модель с четырьмя количественными предсказаниями, проверенными экспериментально", "изменение осмолярности испарением воды, ферментативным разложением сахарозы или световым uncaging", "in vitro"],
  "works": [w("10.1002/anie.202014174", "independent of the GUV size, while asymmetric division happens at lower osmolarity ratios")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["division", "osmolarity", "size-scaling", "asymmetric-division", "guv"],
  "notes": "Численное значение порога в аннотации выпало при извлечении текста (фраза «is , independent»), поэтому в statement его нет: воспроизводить число из памяти было бы выдумкой. Нужен полный текст для конкретной величины."
 },
 {
  "atom": "DIP16-0007",
  "statement": "Активные коацерватные капли растут за счёт топливного синтеза нового коацерватного материала, а скорость их роста отражает концентрации субстрата, фермента и белка.",
  "domain": D, "kind": "mechanism",
  "mechanism": "Химическая реакция постоянно обновляет компоненты капли, удерживая её вне равновесия; приток нового материала задаёт рост, поэтому скорость роста управляется составом топливной смеси, а не свойствами мембраны — мембраны у такой протоклетки нет.",
  "formula": None, "symbols": {},
  "conditions": ["нуклеотид-содержащие комплексные коацерваты", "топливный цикл с ферментом", "in vitro, наблюдение на уровне одиночной капли"],
  "works": [w("10.1038/s41467-021-24111-x", "coacervate droplets form and grow by the fuel-driven synthesis of new coacervate material")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["coacervate", "fuel-driven", "growth-rate", "active-matter", "protocell"],
  "notes": "Та же работа сообщает, что капли не подвержены оствальдовскому созреванию и что добавление РНК меняет скорость роста и «fitness» капли; это отдельные утверждения, в эту ячейку не включены."
 },
 {
  "atom": "DIP16-0008",
  "statement": "Без топлива активная коацерватная капля распадается, и на пути распада она разваливается на множество мелких фрагментов.",
  "domain": D, "kind": "mechanism",
  "mechanism": "Существование капли поддерживается только топливным циклом; при прекращении топлива материал уходит из капли, и распад идёт через множественное дробление, а не через постепенное растворение — содержимое рассеивается по фрагментам.",
  "formula": None, "symbols": {},
  "conditions": ["РНК-содержащие активные коацерватные капли", "топливный цикл реакции", "in vitro, флуоресцентная микроскопия"],
  "works": [w("10.1038/s41467-020-18815-9", "in their pathway towards decay, these droplets break apart in multiple droplet fragments")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["coacervate", "decay", "fragmentation", "fuel-driven", "content-loss"],
  "notes": "Это обратная сторона топливного роста: без мембраны «деление» и «распад» — один и тот же процесс дробления, поэтому цена деления здесь равна цене полного рассеивания содержимого."
 },
 {
  "atom": "DIP16-0009",
  "statement": "Молекулы, слишком непроницаемые для пассивного поглощения, втягиваются в модельную протоклетку за секунды процессом, подобным пассивному эндоцитозу, и затем медленно выпускаются в основной люмен за часы.",
  "domain": D, "kind": "measurement",
  "mechanism": "Полупроницаемая мембрана не пропускает часть питательных веществ, но деформация мембраны затягивает порцию внешнего раствора внутрь; образовавшийся эндоцитозный пузырёк затем медленно отдаёт груз в люмен, обходя симметрию пассивной проницаемости.",
  "formula": None, "symbols": {},
  "conditions": ["модельные примитивные клетки с полупроницаемой мембраной", "эксперименты и симуляции", "питательная среда, молекулы слишком непроницаемые для пассивного поглощения"],
  "works": [w("10.1073/pnas.2221064120", "Molecules that are too impermeable to be absorbed can be taken up in a matter of seconds in an endocytic vesicle")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["permeability", "nutrient-uptake", "endocytosis", "timescale", "protocell"],
  "notes": "Времена «секунды на поглощение, часы на выход» — единственные числа в аннотации; они задают верхнюю границу скорости питания, если мембрана непроницаема для субстрата."
 },
 {
  "atom": "DIP16-0010",
  "statement": "Пребиотические везикулы могут отбирать липиды друг у друга, и при ограниченном липидном ресурсе это прямо превращается в конкуренцию между везикулами, то есть в зачаточную форму отбора на уровне клетки.",
  "domain": D, "kind": "mechanism",
  "mechanism": "Перенос липидов движется асимметрией физического состояния или состава мембран, а не работой; когда липида мало, выигрыш одной везикулы — это буквально проигрыш другой, поэтому рост одной популяции идёт за счёт другой.",
  "formula": None, "symbols": {},
  "conditions": ["теоретическая крупнозернистая (coarse-grain) модель популяции везикул", "воспроизводит, часто количественно, результаты ключевых экспериментов по конкуренции везикул", "ограниченный липидный ресурс"],
  "works": [w("10.1038/srep05675", "when lipid resource is limited, translates directly into competition amongst the vesicles")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["competition", "lipid-transfer", "selection", "model", "population"],
  "notes": "Это модель, а не измерение: «количественное воспроизведение» относится к экспериментам других работ, собственных новых чисел аннотация не даёт."
 },
 {
  "atom": "DIP16-0011",
  "statement": "В просмотренной выборке работ по протоклеткам не найдено измерения энергетической цены синтеза мембранного липида (в ATP-эквивалентах или кДж на липид) как отдельной статьи бюджета протоклетки, которую можно сопоставить со скоростью роста.",
  "domain": D, "kind": "gap",
  "mechanism": "Работы по росту мембран измеряют концентрации амфифилов, доли олеата и осмолярность, а работы по топливным коацерватам — концентрации субстрата и фермента; величина «сколько энергии стоит единица новой мембранной площади» в этих выборках не операционализирована.",
  "formula": None, "symbols": {},
  "conditions": ["обзор литературы, а не эксперимент", "только аннотации работ из OpenAlex"],
  "works": [w("10.1021/ja310382d", "the micelle-vesicle equilibrium can be used to drive the growth of pre-existing vesicles upon an increase in amphiphile concentration")],
  "confidence": "medium", "locator_status": "verified",
  "tags": ["gap", "membrane-cost", "energetics", "lipid-synthesis"],
  "searched": {
    "channels": ["OpenAlex API /works?search=", "OpenAlex API /works/https://doi.org/<DOI>"],
    "queries": ["fatty acid vesicle growth and division", "vesicle content loss during division", "membrane permeability nutrient uptake protocell", "lipid synthesis cost protocells", "coacervate protocells fuel driven", "competition between vesicles protocell growth", "osmotic pressure vesicle stability division", "protocell growth rate membrane cost", "energetic cost of lipid synthesis in protocells ATP equivalents per lipid", "cost of producing membrane phospholipids ATP per molecule bacterium", "membrane synthesis rate limits protocell growth energy"],
    "records_screened": 868,
    "dois_verified": 18,
    "date": "2026-11-22"
  },
  "scope": "868 записей с непустой аннотацией, 11 поисковых запросов, 18 DOI проверено индивидуально; полные тексты не читались.",
  "notes": "Формулировка «в просмотренной выборке не найдено», а не «в литературе нет». Ближайшие по смыслу работы — про топливный рост коацерватов (DIP16-0007) и про сопряжение проницаемости с внутренним синтезом липидов (10.1038/s41598-017-02799-6, проверена, но в ячейки не вошла: модель без чисел)."
 },
]

# --- verify quotes are verbatim substrings of the fetched abstracts ---
bad = []
for a in ATOMS:
    for work in a["works"]:
        doi = work["doi"]
        if doi not in V:
            bad.append((a["atom"], doi, "DOI not verified")); continue
        if norm(work["quote"]) not in norm(V[doi]["abstract"]):
            bad.append((a["atom"], doi, "QUOTE NOT SUBSTRING"))
        if not (10 <= len(work["quote"].split()) <= 30):
            bad.append((a["atom"], doi, "quote length %d words" % len(work["quote"].split())))
if bad:
    print("PROBLEMS:")
    for b in bad: print("  ", b)
    sys.exit(1)

out = pathlib.Path("/root/marfagenez/literature/dips/reports/dip-2026-11-23-16.jsonl")
order = ["atom","statement","domain","kind","mechanism","formula","symbols","conditions","works","confidence","locator_status","tags","notes"]
with out.open("w", encoding="utf-8") as f:
    for a in ATOMS:
        row = {k: a[k] for k in order if k in a}
        for extra in ("searched","scope"):
            if extra in a: row[extra] = a[extra]
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("WROTE", out, "cells", len(ATOMS), "unique DOIs", len({w["doi"] for a in ATOMS for w in a["works"]}))
