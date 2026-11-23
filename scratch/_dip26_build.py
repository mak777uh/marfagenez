import json, pathlib, re

ROOT = pathlib.Path("/root/marfagenez")
TXT = ROOT / "_dip26_txt"
DOIS = json.loads((ROOT / "_dip26_dois.json").read_text(encoding="utf-8"))
OUTJ = ROOT / "literature/dips/reports/dip-2026-11-23-26.jsonl"

SLUG = {
    "ujme": "h_10_13189_ujme_2020_080601",
    "ress": "h_10_1016_j_ress_2005_03_012",
    "tqs": "h_10_17929_tqs_8_51",
    "bjps": "h_10_1214_16_bjps317",
    "beich": "h_10_5784_15_0_417",
    "plphys": "PMC13591397",
}
DOI_MAP = {
    "ujme": "10.13189/ujme.2020.080601",
    "ress": "10.1016/j.ress.2005.03.012",
    "tqs": "10.17929/tqs.8.51",
    "bjps": "10.1214/16-bjps317",
    "beich": "10.5784/15-0-417",
    "plphys": "10.1093/plphys/kiag481",
}
CACHE = {}


def text(key):
    if key not in CACHE:
        CACHE[key] = (TXT / (SLUG[key] + ".txt")).read_text(encoding="utf-8", errors="replace")
    return CACHE[key]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def grab(key, start, end, anchor=None):
    t = text(key)
    base = 0
    if anchor:
        base = t.find(anchor)
        if base < 0:
            raise SystemExit(f"ANCHOR NOT FOUND [{key}] {anchor!r}")
    idx = t.find(start, base)
    if idx < 0:
        raise SystemExit(f"START NOT FOUND [{key}] {start!r}")
    j = t.find(end, idx)
    if j < 0:
        raise SystemExit(f"END NOT FOUND [{key}] {end!r}")
    q = norm(t[idx:j + len(end)])
    if norm(q) not in norm(t):
        raise SystemExit(f"NOT VERBATIM [{key}] {q[:60]!r}")
    return q


cells = []


def add(num, statement, kind, mechanism, formula, symbols, conditions, works, tags, notes):
    wl = []
    for w in works:
        key_l = w["doi"].lower()
        meta = DOIS[w["doi"]] if w["doi"] in DOIS else next(v for k, v in DOIS.items() if k.lower() == key_l)
        wl.append({"doi": w["doi"], "locator": w["locator"], "access": w["access"],
                   "quote": w["quote"], "resolved_title": meta["title"],
                   "resolved_year": meta["year"]})
    cells.append({
        "atom": f"DIP26-{num:04d}", "statement": statement,
        "domain": "reliability.maintenance_economics", "kind": kind,
        "mechanism": mechanism, "formula": formula, "symbols": symbols,
        "conditions": conditions, "requires": [], "contradicts": [],
        "works": wl, "confidence": "medium", "locator_status": "verified",
        "tags": tags, "notes": notes,
    })


q1 = grab("ujme", "C(t0) = (c + k F(t0))/ tMTBR(t0)", "(1 – F(t) ) dt")
add(1,
    "Ожидаемая стоимость в единицу времени при возрастной замене есть отношение ожидаемой стоимости цикла к средней наработке между заменами: C(t0)=(c+kF(t0))/\u222b_0^t0(1\u2212F(t))dt.",
    "formula",
    "числитель — стоимость цикла: плановая замена c плюс цена отказа k, взвешенная вероятностью отказа к возрасту t0; знаменатель — средняя наработка до замены. Минимум этого отношения по t0 и задаёт оптимальный возраст",
    q1,
    {"C(t0)": "ожидаемая стоимость в единицу времени ($/млн циклов)",
     "c": "стоимость плановой замены", "k": "дополнительная цена отказа (liability cost)",
     "F(t)": "функция распределения наработки до отказа", "tMTBR(t0)": "средняя наработка между заменами при возрасте t0"},
    ["аналитическая модель", "возрастная замена (age replacement)", "распределение Вейбулла (2 и 3 параметра)",
     "подшипниковые сборки из стали", "численный пример"],
    [{"doi": DOI_MAP["ujme"], "locator": "раздел с моделью стоимости, абзац «the total mean cost per unit time»",
      "access": "fragment", "quote": q1}],
    ["age-replacement", "cost-per-unit-time", "renewal-reward"],
    "Формула в тексте без номера. Цитата — дословная подстрока извлечённого текста PDF, переводы строк заменены пробелами.")

q2 = grab("ujme", "The optimal replacement time t0*", "dC/dt0 (t0*)= 0")
add(2,
    "Оптимальный возраст замены t0* — точка, в которой производная стоимости по возрасту обращается в нуль: dC/dt0(t0*)=0.",
    "condition",
    "условие первого порядка для минимума отношения стоимость/время; в источнике проверяется численно по знаку производной",
    "dC/dt0 (t0*)= 0",
    {"t0*": "оптимальный возраст замены", "C": "стоимость в единицу времени", "k": "цена отказа (параметр семейства кривых)"},
    ["аналитическая модель", "необходимое условие экстремума", "численная проверка производной (рис. 6a/6b)"],
    [{"doi": DOI_MAP["ujme"], "locator": "абзац «The optimal replacement time t0* …», сразу после модели стоимости",
      "access": "fragment", "quote": q2}],
    ["optimality-condition", "first-order-condition", "dC-dT"],
    "В источнике оговорено: замкнутые выражения для t0* получены только для части значений параметров, в общем случае — численно.")

q3 = grab("ujme", "IN the case of", "considered")
add(3,
    "При росте цены отказа k от 10^3 до 10^6 оптимальный возраст замены AM-подшипников падает с ~5\u00b710^6 примерно до 2,7\u00b710^6 циклов.",
    "measurement",
    "цена отказа входит в числитель стоимости цикла, поэтому чем она выше, тем раньше выгодно заменить узел, чтобы не платить её",
    None,
    {"k": "цена отказа (liability cost), диапазон 10^3…10^6", "t0*": "оптимальный возраст замены, млн циклов"},
    ["численный эксперимент", "две партии подшипников (AM и VAR)", "c=10 и c=100", "Вейбулл с параметрами из табл. 1 источника"],
    [{"doi": DOI_MAP["ujme"], "locator": "обсуждение рисунков 6a/6b", "access": "fragment", "quote": q3}],
    ["failure-cost-elasticity", "interval-vs-failure-price", "measurement"],
    "Для VAR-подшипников в том же абзаце интервал падает с 16,7\u00b710^6 до ~0,3\u00b710^6 — чувствительность к цене отказа сильнее; в цитату это не вошло.")

q4 = grab("ress", "and\nT0 =", "(13)")
add(4,
    "Для Вейбулла с h(t)=\u03b2t^(\u03b2\u22121) оптимальный интервал между профилактиками имеет замкнутый вид T0={((N0\u22121)cp+cr)/(cm(\u03b2\u22121)\u03a3\u03b3k)}^(1/\u03b2).",
    "formula",
    "в числителе — цена замены и предыдущих профилактик, в знаменателе — цена минимального ремонта, умноженная на (\u03b2\u22121); параметр формы Вейбулла \u03b2 прямо задаёт оптимальный интервал",
    q4[q4.index("T0 ="):],
    {"T0": "оптимальный интервал между профилактическими обслуживаниями",
     "N0": "оптимальное число профилактик до замены", "cp": "стоимость одной профилактики (PM)",
     "cr": "стоимость замены", "cm": "стоимость минимального ремонта",
     "\u03b2": "параметр формы Вейбулла", "\u03b3k": "коэффициент сохранения качества после k-й профилактики"},
    ["аналитическая модель", "несовершенное PM: случайное качество обслуживания (age reduction и failure-rate модели)",
     "Вейбулл \u03b2=1,6 в численном примере", "равномерное распределение фактора восстановления \u03b8"],
    [{"doi": DOI_MAP["ress"], "locator": "раздел 4.1 Model A, уравнение (13)", "access": "fragment", "quote": q4}],
    ["weibull-in-cost", "optimal-interval", "imperfect-pm", "closed-form"],
    "Запись многострочная, как в извлечённом PDF; сумма в знаменателе берётся по k=1…N0.")

q5 = grab("ress", "(N0 \u2212 1)T0 \u03b2\u03b3N0", "(12)")
add(5,
    "Оптимальное число профилактик N0 задаётся попаданием отношения (cr\u2212cp)/cm в интервал между двумя границами, зависящими от T0^\u03b2 и \u03b3k.",
    "condition",
    "выбор числа профилактик — это сравнение цены замены и цены профилактики с ценой минимального ремонта: чем дороже замена относительно ремонта, тем больше профилактик выгодно",
    q5,
    {"cr": "стоимость замены", "cp": "стоимость профилактики", "cm": "стоимость минимального ремонта",
     "N0": "оптимальное число профилактик", "\u03b3k": "коэффициенты качества обслуживания", "\u03b2": "параметр формы Вейбулла"},
    ["аналитическая модель", "Вейбулл", "несовершенное PM", "численный пример"],
    [{"doi": DOI_MAP["ress"], "locator": "раздел 4.1 Model A, неравенство (12)", "access": "fragment", "quote": q5}],
    ["repair-vs-replace-threshold", "cost-ratio-condition", "number-of-pm"],
    "Неравенство — критерий N0 при известном T0; вместе с (13) даёт пару (T0, N0).")

q6 = grab("tqs", "Under the model introduced in Section 2, cost rate", "(6)")
add(6,
    "Стоимость в единицу времени для возрастной замены системы из n элементов равна (cP(1\u2212FS(T))+\u03a3ciF\u0303i(T)+cL\u00b7D(T))/(\u222b_0^T(1\u2212FS)dt+D(T)), то есть цена простоя cL стоит и в числителе, и в знаменателе.",
    "formula",
    "числитель — ожидаемая стоимость цикла (плановая замена, отказы элементов, потеря от простоя), знаменатель — ожидаемая длина цикла вместе с ожидаемым временем обслуживания D(T)",
    q6[q6.index("is ") + 3:],
    {"C(T)": "стоимость в единицу времени", "cP": "стоимость плановой замены", "ci": "стоимость отказа элемента i",
     "cL": "потеря за единицу времени простоя", "FS": "функция распределения наработки системы",
     "D(T)": "ожидаемое время обслуживания за цикл", "F\u0303i": "ожидаемое число отказов элемента i за цикл"},
    ["аналитическая модель", "система из 5 элементов", "Вейбулл для наработки, гамма для времени обслуживания",
     "явный учёт времени обслуживания"],
    [{"doi": DOI_MAP["tqs"], "locator": "раздел 3.1 Cost Model and Cost Rate, уравнение (6)", "access": "fragment", "quote": q6}],
    ["cost-rate", "downtime-cost", "age-replacement", "series-system"],
    "Удвоенные глифы (𝐶𝐶, 𝑇𝑇) в цитате — следствие курсивной математики в PDF; запись дословная.")

q7 = grab("tqs", "Under conditions (i)", "will never be optimal.", anchor="Corollary 1")
add(7,
    "Если предел (\u03a3ai\u03bbi(\u221e)+cL\u03a3bi\u03bbi(\u221e))/(1+\u03a3bi\u03bbi(\u221e)) не превосходит C(\u221e), профилактическая замена не оптимальна никогда.",
    "condition",
    "сравнение асимптотической стоимости работы до отказа C(\u221e) с комбинацией цен отказов и цены простоя даёт порог, ниже которого вмешательство невыгодно вообще",
    q7[q7.index("if ") + 3:q7.rindex(", preventive")],
    {"ai": "разность цен отказа элемента i и плановой замены (ci\u2212cP)",
     "bi": "разность ожидаемых времён ремонта и плановой замены", "\u03bbi": "интенсивность отказов элемента i",
     "cL": "цена простоя", "C(\u221e)": "стоимость в единицу времени при работе до отказа"},
    ["аналитическая модель", "условия (i)–(iii): возрастающая интенсивность отказов; время ремонта больше времени профилактики; cL\u00b7E[наработка] > cP"],
    [{"doi": DOI_MAP["tqs"], "locator": "раздел 3.2 Conditions for Optimal Interval, Corollary 1", "access": "fragment", "quote": q7}],
    ["no-pm-zone", "threshold", "corollary"],
    "Corollary 1 формулирует зону, где обслуживание невыгодно, — прямой аналог worse-than-minimal зоны.")

q8 = grab("bjps", "renewal-reward theorem, we can observe", "Z(n,k).")
add(8,
    "Долгосрочная стоимость в единицу времени для политики с накопленным пределом цены ремонта L есть отношение ожидаемой стоимости цикла к ожидаемой длине цикла: C(n,k,L)=R(n,k)/Z(n,k).",
    "formula",
    "теорема восстановления (renewal-reward): политика задаётся тройкой (n,k,L) — число отказов первого блока, уровень повреждения второго и предел накопленной цены ремонта",
    "C(n,k,L)= R(n,k)/Z(n,k).",
    {"C(n,k,L)": "долгосрочная ожидаемая стоимость в единицу времени",
     "R(n,k)": "ожидаемая стоимость цикла замены", "Z(n,k)": "ожидаемая длина цикла",
     "n": "число отказов блока 1, после которого система заменяется",
     "k": "уровень повреждения блока 2, при котором система заменяется",
     "L": "предел накопленной цены ремонта"},
    ["аналитическая модель", "двухблочная система", "взаимодействие ударных повреждений (shock damage interaction)",
     "минимальный ремонт, пока накопленная цена ниже L"],
    [{"doi": DOI_MAP["bjps"], "locator": "раздел 2 Model analysis, формула стоимости в единицу времени", "access": "fragment", "quote": q8}],
    ["repair-cost-limit", "renewal-reward", "bivariate-policy"],
    "Далее R(n,k) и Z(n,k) раскрываются суммами интегралов (уравнения 10–12 источника).")

q9 = grab("bjps", "if the cumulative repair cost", "system is preventively replaced.")
add(9,
    "Правило предела цены ремонта: если накопленная цена ремонта до очередного отказа меньше заданного предела L, выполняется минимальный ремонт; иначе система профилактически заменяется.",
    "condition",
    "порог L превращает накопленные затраты в бинарное решение ремонт/замена, поэтому управляющей переменной становится цена ремонта, а не только возраст",
    None,
    {"L": "предопределённый предел накопленной цены ремонта",
     "n": "число отказов до принудительной замены", "k": "уровень повреждения второго блока"},
    ["аналитическая модель", "двухблочная система", "аддитивные ударные повреждения", "накопленная цена ремонта"],
    [{"doi": DOI_MAP["bjps"], "locator": "Abstract (формулировка правила политики)", "access": "fragment", "quote": q9}],
    ["repair-or-replace", "threshold-rule", "cumulative-cost"],
    "Это определение политики, а не формула: в поле formula — пересказ правила словами источника, значение L задаётся извне.")

q10 = grab("beich", "In the examples", "between 4% and 30%.")
add(10,
    "Замена политики «по экономическому сроку службы» на политику накопленного предела цены ремонта даёт экономию затрат от 4% до 30% в разобранных примерах.",
    "measurement",
    "экономический срок службы минимизирует среднюю стоимость в единицу времени, но не учитывает индивидуальный разброс затрат конкретной системы; предел цены ремонта учитывает его",
    None,
    {"экономия": "4–30% затрат на поддержание"},
    ["разобранные автором примеры", "модель цены ремонта как процесса восстановления (в работе Beichelt [2] — винеровский процесс с дрейфом)",
     "одномерное распределение процесса затрат"],
    [{"doi": DOI_MAP["beich"], "locator": "Abstract", "access": "fragment", "quote": q10}],
    ["repair-cost-limit", "savings-percent", "vs-economic-life"],
    "Числа из аннотации. Текст статьи — сканированный, формулы в извлечении искажены, поэтому ячейка измерения, а не формулы.")

q11 = grab("plphys", "This reaction allows for a cost benefit over resynthesis", "Table 1 ).")
add(11,
    "В растительной клетке ферментативная репарация повреждённого белка дешевле его ресинтеза: для сульфиредоксиновой системы выигрыш более чем в 1 200 раз, по таблице 1 — от \u223c25\u00d7 до \u223c1 260\u00d7 в зависимости от системы репарации.",
    "measurement",
    "цена репарации измеряется в ATP-эквивалентах на одно восстановленное повреждение (1–2,5 ATP), цена замены — полный ресинтез белка; отношение этих цен и есть цена отказа от ремонта",
    None,
    {"ATP-эквивалент репарации": "1–2,5 ATP на повреждение (MSR, Trx, Srx, Grx)",
     "цена ресинтеза относительно репарации": "\u223c25\u00d7, \u223c460\u00d7, \u223c1 260\u00d7, >100\u00d7, >1 000\u00d7"},
    ["обзор (Plant Physiology, 2026)", "растительные клетки", "данные по ферментам репарации in vivo"],
    [{"doi": DOI_MAP["plphys"], "locator": "раздел Protein repair mechanisms and the cost benefit over resynthesis + Table 1",
      "access": "fragment", "quote": q11}],
    ["biology-analogue", "repair-vs-replace-price", "protein-turnover", "atp-cost"],
    "Столбец таблицы 1 «Cost of resynthesis relative to repair» — биологический аналог порога ремонт/замена.")

q12 = grab("plphys", "Approximately half of the carbon fixed", "\u223c25% to \u223c40%.")
add(12,
    "В просмотренной биологической выборке не найдено записанной формулы оптимального интервала обновления ткани/покрова как функции цены отказа; найдены только доли затрат (оборот белка — \u223c25–40% дыхания) и отношения цен репарации к ресинтезу.",
    "gap",
    None, None, {},
    ["линька птиц и млекопитающих", "оборот и репарация белка", "теоретические модели интервала обновления ткани"],
    [{"doi": DOI_MAP["plphys"], "locator": "Введение, абзац о стоимости оборота белка", "access": "fragment", "quote": q12}],
    ["gap", "biology", "renewal-interval", "missing-formula"],
    "Это отсутствие в просмотренной выборке, а не в литературе вообще.")

cells[11]["searched"] = {
    "channels": ["OpenAlex (filter is_oa:true)", "Europe PMC full-text search", "PMC fullTextXML",
                 "Internet Archive Wayback (для закрытых PDF)"],
    "queries": ["optimal moult duration model cost feather replacement",
                "optimal replacement interval worn tissue cost model biology",
                "protein turnover cost benefit optimal degradation rate model",
                "\"moult\" AND \"cost per unit time\"",
                "\"feather\" AND \"replacement\" AND \"optimal interval\" AND \"cost\""],
    "dates": "2026-11-23",
}
cells[11]["scope"] = ("прочитаны извлечённые тексты 8 работ по линьке и обороту белка "
                      "(10.1038/s41467-019-10452-1, 10.1371/journal.pone.0061106, 10.1242/bio.061989, "
                      "10.13157/arla.65.2.2018.rp1, 10.30456/avo.2019106, 10.5253/078.101.0114, "
                      "10.1093/plphys/kiag481; 10.1093/aob/mci050 недоступен) плюс поиск по полным текстам "
                      "Europe PMC; формулы оптимального интервала как функции цены отказа ни в одной нет")

for c in cells:
    for w in c["works"]:
        q = w.get("quote")
        if not q:
            continue
        src = [k for k, d in DOI_MAP.items() if d.lower() == w["doi"].lower()]
        assert src, w["doi"]
        if norm(q) not in norm(text(src[0])):
            raise SystemExit(f"QUOTE BROKEN {c['atom']} {w['doi']}")
print("cells:", len(cells), "quotes:", sum(1 for c in cells for w in c["works"] if w.get("quote")))

OUTJ.parent.mkdir(parents=True, exist_ok=True)
with OUTJ.open("w", encoding="utf-8") as fh:
    for c in cells:
        fh.write(json.dumps(c, ensure_ascii=False) + "\n")
print("wrote", OUTJ)
