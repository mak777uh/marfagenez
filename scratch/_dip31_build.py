import json, pathlib

V = json.load(open("/root/marfagenez/_dip31_verified.json"))
OUT = pathlib.Path("/root/marfagenez/literature/dips/reports")

def work(doi, locator, quote):
    ab = V[doi]["abstract"]
    assert quote in ab, f"QUOTE NOT IN ABSTRACT {doi}: {quote[:60]}"
    n = len(quote.split())
    assert 10 <= n <= 30, f"QUOTE LEN {n} {doi}"
    return {"doi": doi, "locator": locator, "access": "abstract", "quote": quote,
            "resolved_title": V[doi]["title"], "resolved_year": V[doi]["year"]}

atoms = []

atoms.append({
 "atom": "DIP31-0001",
 "statement": "Клиренс Aβ(1-40) из мозга крысы насыщается по нагрузке: при индикаторной дозе период полувыведения 48.8 мин, а половинная концентрация насыщения 8.15 нМ.",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "насыщаемый клиренс пептида через гематоэнцефалический барьер: с ростом концентрации Aβ скорость удаления перестаёт быть пропорциональна нагрузке, и точка полунасыщения задаёт Km процесса",
 "formula": "t1/2(C->0) = 48.8 мин; C_1/2 = 8.15 нМ",
 "symbols": {
   "t1/2": "период полувыведения 125I-Aβ(1-40) из мозга крысы при низкой нагрузке",
   "C_1/2": "концентрация половинного насыщения клиренса (аналог Km)"},
 "conditions": ["in vivo, крыса", "метод Brain Efflux Index (BEEI)", "125I-Aβ(1-40), интрацеребральное введение", "37 °C, физиологический раствор"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1523/jneurosci.2236-04.2004",
                "abstract, предложение о BEEI-кинетике (half-life / half-saturation)",
                "eliminated from rat brain to circulating blood with a half-life of 48.8 min and a half-saturation concentration of 8.15 nm")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["clearance-saturation", "km", "half-life", "amyloid-beta", "blood-brain-barrier"],
 "notes": "Half-saturation concentration трактуется как Km насыщаемого клиренса; авторы не приводят явной формулы Михаэлиса-Ментен, поэтому formula — запись измеренных величин, а не вставленная модель."})

atoms.append({
 "atom": "DIP31-0002",
 "statement": "Скорость элиминации Aβ(1-40) из мозга у 23-месячных крыс на 30.5% ниже, чем у 7-недельных, при том же протоколе измерения.",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "возрастное падение скорости удаления того же субстрата тем же путём; согласуется со снижением ёмкости (Vmax) клиренса, но Km в этой работе отдельно не измерен",
 "formula": "v(23 мес) / v(7 нед) = 1 - 0.305 = 0.695",
 "symbols": {"v": "скорость элиминации Aβ(1-40) из мозга по BEEI"},
 "conditions": ["in vivo, крыса", "23 мес против 7 нед", "тот же BEEI-протокол", "125I-Aβ(1-40)"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1523/jneurosci.2236-04.2004",
                "abstract, предложение о возрастном сравнении",
                "The Abeta(1-40) elimination rate was reduced by 30.5% in 23-month-old rats compared with 7-week-old rats.")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["ageing", "clearance-rate", "amyloid-beta", "vmax-decline"],
 "notes": "Число относится к скорости элиминации, а не к Km; вывод о падении именно Vmax — интерпретация, помеченная в mechanism."})

atoms.append({
 "atom": "DIP31-0003",
 "statement": "Насыщение клиренса агрегированного IgG у макрофагов наступает на стадии связывания, а не катаболизма: при высоких дозах константа связывания ka падает, тогда как константа катаболизма kc остаётся постоянной (20.0-55.0 × 10-3 мин-1).",
 "domain": "bio.information_error",
 "kind": "mechanism",
 "mechanism": "ограниченное число Fc-рецепторов насыщается раньше, чем деградативный аппарат; поэтому кривая «нагрузка -> скорость» выходит на плато из-за этапа узнавания, а не из-за протеолиза",
 "formula": None,
 "symbols": {
   "ka": "константа связывания A-IgG с макрофагом, 0.7-5.5 × 10-3 мин-1 (субнасыщающие дозы)",
   "kc": "константа катаболизма A-IgG, 20.0-55.0 × 10-3 мин-1",
   "A-IgG": "термоагрегированный 125I-IgG"},
 "conditions": ["in vitro", "перитонеальные макрофаги крысы", "A-IgG 0.01-10 мкг", "37 °C, 10 мин - 24 ч"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.4049/jimmunol.123.5.2040",
                "abstract, предложение о высоких дозах A-IgG",
                "At higher doses of A-IgG, the binding step became saturated (and ka fell) while catabolism remained first order (with constant kc).")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["clearance-saturation", "receptor-limited", "aggregates", "macrophage", "binding-step"],
 "notes": "Разделение «насыщается связывание, а не катаболизм» — ключевое для формы кривой: плато ставит этап доставки/узнавания."})

atoms.append({
 "atom": "DIP31-0004",
 "statement": "Потолок скорости удаления агрегатов зависит от их размера: 1200 молекул на клетку в минуту для мелких агрегатов A-IgG9 против 540 для крупных A-IgG74, хотя по массе крупных агрегатов удаляется больше.",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "Vmax задаётся числом частиц, а не массой груза: одна и та же масса крупных агрегатов содержит меньше частиц, поэтому счётная скорость ниже",
 "formula": "Vmax(A-IgG9) = 1200 молекул·клетка-1·мин-1; Vmax(A-IgG74) = 540 молекул·клетка-1·мин-1",
 "symbols": {
   "Vmax": "максимальная скорость клиренса агрегатов, молекул на клетку в минуту",
   "A-IgG9 / A-IgG74": "агрегаты IgG из 9 и 74 мономеров"},
 "conditions": ["in vitro", "перитонеальные макрофаги крысы", "125I-термоагрегированный IgG", "37 °C"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.4049/jimmunol.123.5.2040",
                "abstract, предложение о зависимости Vmax от размера A-IgG",
                "more micrograms but fewer molecules of A-IgG9 could be cleared per unit time than A-IgG74 (1200 A-IgG9 and 540 A-IgG74 molecules per cell per min)")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["vmax", "aggregate-size", "clearance-capacity", "particle-number"],
 "notes": "Значения относятся к разным препаратам агрегатов в одной системе; это не Km, а потолок скорости."})

atoms.append({
 "atom": "DIP31-0005",
 "statement": "Деградация тромбоспондина фибробластами насыщаема и описывается кинетикой Михаэлиса-Ментен: Km = 6×10-8 М, Vmax = 1.4×10^5 молекул на клетку в минуту.",
 "domain": "bio.information_error",
 "kind": "formula",
 "mechanism": "рецептор-опосредованный захват с последующей лизосомальной деградацией; насыщение по концентрации субстрата даёт гиперболическую кривую нагрузка -> скорость",
 "formula": "v = Vmax·[S] / (Km + [S]); Km = 6×10-8 M; Vmax = 1.4×10^5 молекул·клетка-1·мин-1",
 "symbols": {
   "v": "скорость деградации 125I-тромбоспондина",
   "[S]": "концентрация тромбоспондина",
   "Km": "кажущаяся константа Михаэлиса, 6×10-8 М",
   "Vmax": "максимальная скорость деградации, 1.4×10^5 молекул на клетку в минуту"},
 "conditions": ["in vitro", "эмбриональные лёгочные фибробласты человека", "125I-тромбоспондин", "37 °C", "подавление хлорохином и при 4 °C"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1083/jcb.98.1.22",
                "abstract, предложение о Km и Vmax деградации",
                "The apparent Km and Vmax for degradation at 37 degrees C were 6 X 10(-8) M and 1.4 X 10(5) molecules per cell per minute, respectively.")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["michaelis-menten", "km", "vmax", "lysosomal-degradation", "protein-clearance"],
 "notes": "Хлорохин и 4 °C подавляют деградацию — аргумент в пользу лизосомального пути, а не протеасомы."})

atoms.append({
 "atom": "DIP31-0006",
 "statement": "Высокоаффинный сайт пептидилглутамил-пептид-гидролазной активности протеасомы подчиняется кинетике Михаэлиса-Ментен с Km около 100 мкМ по синтетическому субстрату LLE-NA.",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "гиперболическое насыщение первого (высокоаффинного) сайта протеасомы; Km задаёт концентрацию, при которой скорость гидролиза равна половине максимальной",
 "formula": "Km(LLE1) ≈ 100 мкМ",
 "symbols": {
   "Km(LLE1)": "константа Михаэлиса высокоаффинного сайта протеасомы по LLE-NA",
   "LLE-NA": "Z-Leu-Leu-Glu-бета-нафтиламид, синтетический пептидный субстрат"},
 "conditions": ["in vitro", "мультикаталитический протеазный комплекс (протеасома) из печени крысы", "субстрат LLE-NA", "pH 7.0-7.5"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1021/bi00131a033",
                "abstract, пункт (a) о высокоаффинном сайте LLE1",
                "there is a high-affinity site (LLE1) which obeys Michaelis-Menten kinetics with a Km value of approximately 100 microM")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["proteasome", "km", "michaelis-menten", "peptide-substrate", "lle-na"],
 "notes": "Субстрат синтетический пептид, не повреждённый белок; перенос Km на белковые субстраты не проверен в этой работе."})

atoms.append({
 "atom": "DIP31-0007",
 "statement": "При более высокой концентрации того же субстрата кривая скорость-нагрузка перестаёт быть гиперболической и становится сигмоидной, что несовместимо с простым насыщением по одному сайту.",
 "domain": "bio.information_error",
 "kind": "condition",
 "mechanism": "второй сайт или аллостерическая активация: при росте нагрузки скорость растёт круче гиперболы, то есть клиренс не просто выходит на плато, а меняет форму кривой",
 "formula": None,
 "symbols": {
   "LLE2": "второй (низкоаффинный) сайт связывания LLE-NA, дающий сигмоидную зависимость"},
 "conditions": ["in vitro", "протеасома из печени крысы", "высокие концентрации LLE-NA", "pH 7.0-7.5"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1021/bi00131a033",
                "abstract, пункт (b) о сайте LLE2",
                "at higher substrate concentrations (LLE2) the curve is sigmoidal, suggesting either allosteric activation of the proteinase at a second site")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["sigmoidal-kinetics", "allostery", "proteasome", "load-response", "non-michaelis"],
 "notes": "Контрпример к предположению «клиренс всегда гиперболически насыщается»: форма кривой зависит от диапазона нагрузки."})

atoms.append({
 "atom": "DIP31-0008",
 "statement": "Km кальций-активируемой протеазы мозга по трём нейрофиламентным субстратам равны 3.9×10-8, 4.4×10-8 и 8.2×10-8 М и растут с молекулярной массой субстрата.",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "аффинность протеазы к белковому субстрату падает с ростом размера субстрата: Km(P68) < Km(P150) < Km(P200)",
 "formula": "Km(P68) = 3.9×10-8 M; Km(P150) = 4.4×10-8 M; Km(P200) = 8.2×10-8 M",
 "symbols": {
   "Km(P68/P150/P200)": "кажущиеся константы Михаэлиса по нейрофиламентным белкам 68, 150 и 200 кДа"},
 "conditions": ["in vitro", "мозг крысы", "125I-нейрофиламентные белки P68, P150, P200", "Ca2+-зависимая тиоловая протеаза", "pH 7.4-8.0"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1021/bi00260a012",
                "abstract, предложение о Km для P68/P150/P200",
                "The apparent Km values for 68000- (P68), 150000- (P150), and 200000- (P200) dalton neurofilament proteins are 3.9 x 10(-8) M, 4.4 x 10(-8) M, and 8.2 x 10(-8) M, respectively.")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["km", "substrate-size", "calpain", "neurofilament", "protease"],
 "notes": "Три Km для одного фермента и разных субстратов — прямой пример зависимости аффинности от размера груза."})

atoms.append({
 "atom": "DIP31-0009",
 "statement": "Активность этой протеазы имеет порог по Ca2+: ниже примерно 10-6 М гидролиз практически не идёт, насыщение достигается при примерно 10-4 М, то есть скорость удаления субстрата ограничена не только его концентрацией.",
 "domain": "bio.information_error",
 "kind": "condition",
 "mechanism": "кофакторный порог и кофакторное насыщение: без достаточной концентрации Ca2+ аппарат удаления не работает, а выше порога насыщается по активатору",
 "formula": "порог [Ca2+] ≈ 10-6 M; насыщение [Ca2+] ≈ 10-4 M",
 "symbols": {"[Ca2+]": "концентрация ионов кальция, активирующих протеазу"},
 "conditions": ["in vitro", "мозг крысы", "Ca2+-зависимая тиоловая протеаза", "125I-нейрофиламентные белки"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1021/bi00260a012",
                "abstract, предложение о пороге и насыщении по Ca2+",
                "Proteolytic activity is dependent upon Ca2+ concentration with threshold and saturation values of 10(-6) and 10(-4) M, respectively.")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["threshold", "cofactor-saturation", "calcium", "protease", "load-response"],
 "notes": "Порог по активатору, а не по субстрату; важен как пример того, что «скорость от нагрузки» может определяться третьей переменной."})

atoms.append({
 "atom": "DIP31-0010",
 "statement": "Рецептор-опосредованный захват лизосомального фермента BMN 250 в нейронах и астроцитах насыщается: Kuptake = 5 и 3 нМ, Vmax = 764 и 5380 нмоль/(ч·мг).",
 "domain": "bio.information_error",
 "kind": "measurement",
 "mechanism": "CI-MPR-опосредованный эндоцитоз насыщается по концентрации фермента; ёмкость доставки в лизосомы различается между типами клеток примерно в 7 раз",
 "formula": "Kuptake = 5 нМ (нейроны), 3 нМ (астроциты); Vmax = 764 и 5380 нмоль·ч-1·мг-1",
 "symbols": {
   "Kuptake": "концентрация фермента при полумаксимальном захвате (аналог Km)",
   "Vmax": "максимальная ёмкость захвата, нмоль на час на мг белка"},
 "conditions": ["in vitro", "нейроны и астроциты грызунов", "BMN 250 (IGF2-меченная NAGLU), CI-MPR-опосредованный захват", "24 ч инкубации"],
 "requires": [],
 "contradicts": [],
 "works": [work("10.1371/journal.pone.0207836",
                "abstract, предложение о Kuptake и Vmax",
                "the concentration of enzyme at half-maximal uptake, is 5 nM and 3 nM in neurons and astrocytes, with a maximal uptake capacity (Vmax) corresponding to 764 nmol/hr/mg and 5380 nmol/hr/mg")],
 "confidence": "medium",
 "locator_status": "verified",
 "tags": ["km", "vmax", "lysosomal-targeting", "ci-mpr", "saturable-uptake", "neuron"],
 "notes": "Измерен захват фермента, а не деградация агрегата; включён как количественная кривая «нагрузка -> скорость» для лизосомальной доставки."})

lines = []
for a in atoms:
    lines.append(json.dumps(a, ensure_ascii=False))
(OUT / "dip-2026-11-23-31.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("atoms:", len(atoms), "works:", len({w["doi"] for a in atoms for w in a["works"]}))
