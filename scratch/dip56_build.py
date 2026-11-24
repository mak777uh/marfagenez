import json, os, re, sys, time, urllib.request

TXT = "/root/marfagenez/scratch/dip56_txt"
CACHE = "/root/marfagenez/scratch/dip56_doi.json"
KEY = open('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read().strip()
OUT = "/root/marfagenez/literature/dips/reports/dip-2026-11-24-56.jsonl"

def flat(s):
    return re.sub(r"\s+", " ", s).strip()

def oa_work(doi):
    url = "https://api.openalex.org/works/https://doi.org/" + doi
    req = urllib.request.Request(url, headers={"User-Agent": "dip-researcher/1.0"})
    for t in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                w = json.loads(r.read().decode())
            inv = w.get("abstract_inverted_index")
            abs_txt = ""
            if inv:
                pos = {}
                for word, idxs in inv.items():
                    for i in idxs:
                        pos[i] = word
                abs_txt = " ".join(pos[i] for i in sorted(pos))
            return {"doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": w.get("title"), "year": w.get("publication_year"),
                    "id": w.get("id"), "abstract": flat(abs_txt)}
        except Exception as e:
            if t == 3:
                raise
            time.sleep(4 * (t + 1))

DOIS = [
 "10.1186/1475-2859-7-19",
 "10.1128/aem.00638-16",
 "10.1186/1472-6750-13-93",
 "10.3389/fphys.2013.00090",
 "10.1113/jphysiol.2014.282517",
 "10.1152/physrev.1997.77.3.731",
 "10.1371/journal.ppat.1011522",
 "10.1371/journal.pcbi.1006100",
 "10.1128/aem.37.3.537-543.1979",
]

cache = {}
if os.path.exists(CACHE):
    cache = json.load(open(CACHE))
for d in DOIS:
    if d not in cache or not cache[d].get("title"):
        cache[d] = oa_work(d)
        print("DOI ok:", d, "|", cache[d]["year"], "|", (cache[d]["title"] or "")[:80])
        time.sleep(1)
    else:
        print("DOI cached:", d, "|", cache[d]["year"])
json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)

def src(kind):
    if kind == "abs":  # resolved later per doi
        return None
    return flat(open(os.path.join(TXT, kind + ".txt")).read())

def excerpt(text, start, end):
    i = text.find(start)
    if i < 0:
        raise SystemExit("START NOT FOUND: %r" % start[:80])
    j = text.find(end, i)
    if j < 0:
        raise SystemExit("END NOT FOUND: %r" % end[:80])
    q = text[i:j + len(end)]
    return re.sub(r"\s+", " ", q).strip()

# (atom, doi, source, start, end, locator, access, kind, ...)
CELLS = []

CELLS.append(dict(
 atom="DIP56-0001", doi="10.1186/1475-2859-7-19", src="bacillus_maint",
 start="The determined coefficient of 0.39", end="previously reported 0.44 mmol g(cdw) -1 h -1",
 locator="Results, раздел «Maintenance metabolism», абзац 2 (Table 3)", access="fulltext", kind="measurement",
 statement="У Bacillus subtilis 168 коэффициент поддержания, полученный как отрезок на оси ординат регрессии q_glc(D), равен 0.39 ммоль глюкозы/(гCDW·ч), у spo0A-мутанта — 0.49, тогда как в литературе для родственного штамма 1012 указано 0.44 ммоль/(гCDW·ч).",
 mechanism="q_glc линейно зависит от D в хемостате; свободный член регрессии (Pirt/Herbert–Pirt) и есть доля потребления субстрата, не связанная с ростом; инактивация spo0A повышает её, т.е. поддержание — регулируемая, а не константная величина.",
 formula="q_glc = μ / Y_glc^max + m_glc", 
 symbols={"q_glc": "удельная скорость потребления глюкозы, ммоль/(гCDW·ч)", "μ": "удельная скорость роста, ч⁻¹", "Y_glc^max": "максимальный молярный выход биомассы, гCDW/г глюкозы", "m_glc": "коэффициент поддержания, ммоль/(гCDW·ч)"},
 conditions=["хемостат, глюкозо-минимальная среда, B. subtilis 168 (wild type), spo0A и sigE мутанты", "линейный участок q_glc(D), взвешенная МНК-регрессия", "аэробные условия, 37 °C (по разделу Methods)"],
 tags=["maintenance-coefficient", "pirt", "bacillus-subtilis", "chemostat", "mmol-glucose"],
 notes="GAM/NGAM в этой работе в ATP не переводились: m дан в единицах субстрата. Для B. licheniformis в той же Table 3 указано 0.24, для K. aerogenes 0.3 ммоль/(гCDW·ч). У B. subtilis natto коэффициент не определялся, т.к. q_glc(D) нелинеен — это ограничение метода, а не организма."))

CELLS.append(dict(
 atom="DIP56-0002", doi="10.1128/aem.00638-16", src="pichia_retentostat",
 start="yielding an estimated m S (± standard deviation) of 0.0100", end="0.0100 ± 0.0023 g S g X −1 h −1",
 locator="Results, раздел «Maintenance energy requirement in glucose-limited chemostat cultures», абзац 4", access="fulltext", kind="measurement",
 statement="У Pichia pastoris (CBS 7435 Δflo8) в глюкозо-лимитированных аэробных хемостатах коэффициент поддержания m_S = 0.0100 ± 0.0023 г глюкозы/(г биомассы·ч); у S. cerevisiae в аэробном ретентостате — 0.0071 ± 0.0005.",
 mechanism="m_S — отрезок на оси q_S при μ→0 в соотношении Герберта–Пирта; измерен по восьми независимым хемостатам при D = 0.025–0.10 ч⁻¹ с линейной аппроксимацией q_S(μ).",
 formula="q_S = μ / Y_X/S^max + m_S",
 symbols={"q_S": "удельная скорость потребления глюкозы, г S/(г X·ч)", "m_S": "коэффициент поддержания, г S/(г X·ч)", "Y_X/S^max": "максимальный выход биомассы на глюкозе, г/г"},
 conditions=["аэробный глюкозо-лимитированный хемостат, 25 °C, pH 5.85, синтетическая среда", "D = 0.025; 0.050; 0.075; 0.100 ч⁻¹, 8 независимых культур", "непродуцирующий штамм (без гетерологичного белка)"],
 tags=["maintenance-coefficient", "pichia-pastoris", "chemostat", "yeast", "g-per-g"],
 notes="Y_X/S^max = 0.584 г/г. Авторы отдельно показывают, что у штаммов, продуцирующих гетерологичный белок, m_S на ~50% выше (0.0147–0.0161), т.е. поддержание зависит от метаболической нагрузки."))

CELLS.append(dict(
 atom="DIP56-0003", doi="10.1128/aem.00638-16", src="pichia_retentostat",
 start="the retentostat cultures equaled 0.0031", end="3-fold lower than the m S value calculated from the chemostat experiments",
 locator="Results, раздел о ретентостатах при near-zero growth, абзац 2", access="fulltext", kind="contradiction",
 statement="При переходе к near-zero growth (μ < 0.001 ч⁻¹) тот же штамм P. pastoris даёт m_S = 0.0031 ± 0.0001 г/(г·ч), т.е. в 3 раза меньше, чем экстраполяция из хемостатов (0.0100); следовательно допущение Пирта о независимости коэффициента поддержания от скорости роста для этого организма не выполняется.",
 mechanism="В ретентостате биомасса удерживается, μ плавно снижается; если m_S — константа, q_S должна выйти на плато m_S. Измеренная q_S падает до 0.004 г/(г·ч), т.е. до 40% от хемостатной m_S, значит клетки снижают удельную стоимость поддержания.",
 formula=None, symbols={},
 conditions=["аэробный глюкозо-лимитированный ретентостат, μ от 0.025 ч⁻¹ до <0.0004 ч⁻¹ (время удвоения выросло с 27.7 ч до >38 сут)", "тот же штамм и среда, что и в хемостате"],
 tags=["maintenance-coefficient", "near-zero-growth", "retentostat", "growth-rate-dependence", "contradiction"],
 notes="Прямое противоречие двухкомпонентной модели Pirt (уже внесена как B7-06-0003/B7-10-0003): там m — константа, здесь m зависит от μ. Цифры: хемостат 0.0100 ± 0.0023, ретентостат 0.0031 ± 0.0001, q_S в конце 0.004 (40% от m_S)."))

CELLS.append(dict(
 atom="DIP56-0004", doi="10.1186/1472-6750-13-93", src="putida_maint",
 start="the Growth-Associated Maintenance (GAM) of 85 mmol ATP", end="Non Growth-Associated Maintenance (NGAM) of 3.96 mmol ATP · g DCW -1 · h -1",
 locator="Abstract (те же величины в разделе Results)", access="fulltext", kind="measurement",
 statement="Для Pseudomonas putida KT2440 подгонка геномной модели iJP815 к хемостатным данным дала NGAM = 3.96 ммоль ATP/(гDCW·ч) и GAM = 85 ммоль ATP/гDCW при коэффициенте поддержания по субстрату 0.037 г глюкозы/(гDCW·ч).",
 mechanism="Экспериментально измеренный m_s (г субстрата/(гDCW·ч)) умножен на максимальный теоретический выход ATP из глюкозы Y_ATP = 19.25 моль ATP/моль глюкозы; полученная величина и есть NGAM — скорость диссипации ATP на поддержание в единицу времени.",
 formula="NGAM = m_s · Y_ATP",
 symbols={"m_s": "коэффициент поддержания по глюкозе, г glc/(гDCW·ч)", "Y_ATP": "максимальный теоретический выход ATP, 19.25 моль ATP/моль глюкозы", "NGAM": "не связанное с ростом поддержание, ммоль ATP/(гDCW·ч)", "GAM": "связанное с ростом поддержание, ммоль ATP/гDCW"},
 conditions=["непрерывные биореакторные культуры на минеральной среде с глюкозой как единственным источником углерода", "несколько скоростей разведения, анализ макромолекулярного состава биомассы", "геномная метаболическая модель iJP815"],
 tags=["ngam", "gam", "pseudomonas-putida", "atp-maintenance", "flux-balance"],
 notes="Y_x/s^max = 0.397 гDCW/г глюкозы, μ_max = 0.59 ч⁻¹. Авторы подчёркивают, что обе величины значимо отличаются от прежних назначений в модели именно из-за более низкого выхода и более высокого m_s. Не путать с уже внесённой NGAM 7.836 у M. maripaludis (DIP21B-0002)."))

CELLS.append(dict(
 atom="DIP56-0005", doi="10.3389/fphys.2013.00090", src="pal_review",
 start="Physical activity level 1.70 ± 0.23", end="1.77 ± 0.28 1.13 – 2.69",
 locator="Table 1 (Characteristics of healthy subjects … doubly labeled water)", access="fulltext", kind="measurement",
 statement="У взрослых из североевропейской базы DLW-измерений уровень физической активности PAL = 1.70 ± 0.23 (женщины, n = 301) и 1.77 ± 0.28 (мужчины, n = 346), т.е. базальный/рутинный обмен составляет 1/1.75 ≈ 57% суточных затрат энергии.",
 mechanism="PAL = TEE/BMR (или TEE/REE) делит суточные затраты на «поддерживающую» и «активностную» части; чем ближе PAL к 1, тем большая доля дохода уходит на поддержание.",
 formula="PAL = TEE / BMR;  BMR/TEE = 1/PAL",
 symbols={"PAL": "уровень физической активности, безразмерный", "TEE": "суточные затраты энергии, МДж/сут", "BMR": "базальный метаболизм, МДж/сут"},
 conditions=["574 измерения TEE методом дважды меченой воды, здоровые взрослые 18–96 лет, Северная Европа", "PAL усреднён по 14 дням свободной жизни", "BMR/REE измерен прямым методом, не расчётной формулой"],
 tags=["bmr", "pal", "doubly-labelled-water", "human", "maintenance-share"],
 notes="В той же Table 1: REE 6.1 ± 1.0 МДж/сут и TEE 10.3 ± 2.0 МДж/сут у женщин (6.1/10.3 = 59%); 7.5 и 13.2 МДж/сут у мужчин (57%). Средний PAL «около 1.75» авторы называют в тексте (раздел Physical activity level and body mass index)."))

CELLS.append(dict(
 atom="DIP56-0006", doi="10.1113/jphysiol.2014.282517", src="nonsig_brain",
 start="The brain spends just under half of its energy", end="which tasks are so energetically costly for the brain.",
 locator="Abstract", access="fulltext", kind="measurement",
 statement="Мозг тратит чуть меньше половины своей энергии на несигнальные («housekeeping») процессы, т.е. доля поддержания в энергобюджете мозга ≈ 45–50%.",
 mechanism="Несигнальные процессы — синтез белка и липидов, утечка протонов через митохондриальную мембрану, перестройки цитоскелета; они не кодируют информацию, но потребляют ATP, и в прежних бюджетах им приписывали 25–50%.",
 formula=None, symbols={},
 conditions=["обзор экспериментальных данных и модельных оценок для мозга млекопитающих (крыса/человек)", "не прямое измерение, а сведение опубликованных бюджетов"],
 tags=["brain", "housekeeping", "maintenance-share", "proton-leak", "protein-synthesis"],
 notes="Там же: «в прежних энергетических бюджетах на несигнальные задачи отводили 25–50% энергии мозга». Это единственная найденная работа, где доля поддержания в мозге сформулирована как явная доля от общего расхода."))

CELLS.append(dict(
 atom="DIP56-0007", doi="10.1113/jphysiol.2014.282517", src="nonsig_brain",
 start="in unanaesthetised animals, sodium pumping accounts", end="less than 45% is used on other tasks.",
 locator="Discussion, раздел о Na+-pumping и энергетическом бюджете, абзац 1", access="fulltext", kind="measurement",
 statement="У бодрствующих (неанестезированных) животных работа Na+/K+-насоса потребляет более 55% ATP мозга, а на все остальные задачи остаётся менее 45%.",
 mechanism="Снижение входа Na+ (по сравнению с прежними оценками) уменьшает расчётную долю насоса; авторы пересчитывают бюджет и получают, что именно насос — крупнейшая статья расхода ATP, а не сигнальные процессы.",
 formula="доля_насоса + доля_прочих = 1;  доля_насоса > 0.55",
 symbols={},
 conditions=["пересчёт по данным о входе Na+ во время потенциалов действия у бодрствующих животных", "оценка для серого вещества мозга"],
 tags=["na-k-atpase", "ion-pump-share", "brain", "atp-budget"],
 notes="Прямое числовое утверждение о доле ATP на насос, которого не было в старых бюджетах (там насосу отводили ~50%). Совместно с DIP56-0006 задаёт разбиение: >55% насос, <45% прочие несигнальные/сигнальные задачи."))

CELLS.append(dict(
 atom="DIP56-0008", doi="10.1152/physrev.1997.77.3.731", src="abs",
 start="We estimate that approximately 90% of mammalian oxygen consumption", end="uncoupled by the mitochondrial proton leak",
 locator="Abstract", access="abstract", kind="measurement",
 statement="Около 90% потребления кислорода млекопитающим в стандартном состоянии приходится на митохондрии, и примерно 20% этого потока рассеивается утечкой протонов через внутреннюю мембрану, т.е. не идёт на синтез ATP.",
 mechanism="Утечка протонов — разобщающая реакция внутренней мембраны: она снижает P/O и превращает часть окислительного потока в тепло, образуя постоянную «поддерживающую» статью расхода, не связанную ни с ростом, ни с размножением.",
 formula="SMR_O2 = 0.9·SMR_O2(митохондрии) = 0.2·(митохондриальный поток, разобщённый) + 0.8·(поток, сопряжённый с ATP)",
 symbols={"SMR": "standard metabolic rate, стандартный обмен, Вт/кг или моль O2/(г·ч)", "P/O": "отношение фосфорилирования к окислению"},
 conditions=["стандартное состояние (покой, термонейтральность, натощак), млекопитающие", "обзор и количественная сводка по тканям, не одно измерение"],
 tags=["proton-leak", "mitochondria", "membrane-bioenergetics", "smr", "uncoupling"],
 notes="Ключевая для домена membranes.bioenergetics цифра: утечка протонов — самая крупная одиночная «поддерживающая» статья энергобюджета млекопитающего (20% от 90% митохондриального потока ≈ 18% SMR). Доступ только к аннотации (Physiol Rev 1997 не в открытом доступе), поэтому confidence medium."))

CELLS.append(dict(
 atom="DIP56-0009", doi="10.1152/physrev.1997.77.3.731", src="abs",
 start="Of the 80% of oxygen consumption coupled to ATP synthesis", end="4-8% by the Ca2(+)-ATPase",
 locator="Abstract", access="abstract", kind="measurement",
 statement="Из 80% потребления кислорода, сопряжённого с синтезом ATP, примерно 25–30% расходуется на синтез белка, 19–28% — на Na+/K+-ATPase, 4–8% — на Ca2+-ATPase, 2–8% — на актомиозиновую ATPase.",
 mechanism="Декомпозиция стандартного обмена по ATP-потребляющим реакциям: доля насоса задана как доля от сопряжённого потока, а не от всего SMR; при пересчёте на SMR доля Na+/K+-ATPase ≈ 15–22%.",
 formula="доля_от_SMR(Na/K) = 0.8 × (0.19…0.28)",
 symbols={"19–28%": "доля сопряжённого с ATP потока O2, идущая на Na+/K+-ATPase", "80%": "доля O2, сопряжённая с синтезом ATP"},
 conditions=["стандартное состояние, млекопитающие, сводка по тканям", "только аннотация; первичные таблицы по тканям в тексте недоступны"],
 tags=["na-k-atpase", "ion-pump-share", "protein-synthesis", "atp-budget", "mammals"],
 notes="Оценка дана как диапазон, а не точка: 19–28% — это разброс между тканями. Для сравнения с DIP56-0007 (мозг, >55%) важно, что здесь доля считается от сопряжённого с ATP потока, а не от общего потребления O2."))

CELLS.append(dict(
 atom="DIP56-0010", doi="10.1371/journal.ppat.1011522", src="trypanosome_atp",
 start="DNA replication 0.3 1.8 25 c", end="Protein turnover 26.3",
 locator="Table 13 (Comparison of ATP demand in different cell types), колонка BSF T. brucei (This work)", access="fulltext", kind="measurement",
 statement="В теоретическом ATP-бюджете bloodstream-формы Trypanosoma brucei обновление (turnover) протеома требует 26.3% всего ATP, а удвоение протеома — 33.3%, т.е. на «поддержание и обновление» уже существующих молекул уходит почти столько же, сколько на построение новых.",
 mechanism="Стоимость turnover = стоимость замены молекул, деградировавших за клеточный цикл (5.3 ч), при допущении о рецикле аминокислот; складывается с синтезом нового протеома в общий бюджет.",
 formula="ATP_turnover = Σ_i (N_i / t½_i) · c_AA · 4 ATP",
 symbols={"N_i": "число молекул i-го белка", "t½_i": "время полужизни, ч", "4 ATP": "затраты на одну пептидную связь"},
 conditions=["bloodstream-form T. brucei, длительность клеточного цикла 5.3 ч", "теоретическая реконструкция бюджета по протеомным и биохимическим данным, не прямое измерение"],
 tags=["protein-turnover", "repair-share", "atp-budget", "trypanosoma", "maintenance"],
 notes="Суммарно трансляция + turnover дают 58.6% ATP-бюджета (в тексте: «translation and protein turnover demand 58.6% of the ATP budget»). В цитате сохранены надстрочные буквы-сноски b/c/d исходной таблицы — они относятся к примечаниям о составе колонок (бактерии/клетки млекопитающих), а не к числам."))

CELLS.append(dict(
 atom="DIP56-0011", doi="10.1371/journal.pcbi.1006100", src="amp_deb",
 start="The median value is 0.9", end="the pseudo-data value for κ is 0.8",
 locator="Results, раздел о распределении параметров в базе AmP, абзац 3", access="fulltext", kind="measurement",
 statement="В базе AmP (Add-my-Pet, сотни видов животных) доля ассимиляции, направляемая в сому, κ имеет медиану 0.9 при стартовом (псевдо-данном) значении 0.8 и распределена по бета-распределению.",
 mechanism="κ-правило DEB: доля κ мобилизованного резерва идёт на соматическое поддержание и рост, доля (1−κ) — на созревание/размножение; при подгонке κ определяется данными о росте и размножении, поэтому псевдо-данное значение 0.8 почти не влияет на медиану.",
 formula="κ = ṗ_s / ṗ_C ;  1−κ = ṗ_J / ṗ_C",
 symbols={"κ": "доля ассимиляции (мобилизованного резерва), идущая в сому", "ṗ_C": "поток мобилизованной энергии", "ṗ_s": "поток в соматическое поддержание и рост", "ṗ_J": "поток в созревание/размножение"},
 conditions=["база AmP: по одному виду = одна запись DEB-модели, параметры оценены в контексте данных", "распределение κ по всем видам базы, не отдельный эксперимент"],
 tags=["deb", "kappa", "allocation", "amp-database", "soma"],
 notes="Практический вывод: κ ≈ 0.8–0.9, т.е. 80–90% ассимиляции уходит на сому (поддержание + рост) и только 10–20% на созревание/размножение. Это не κ Коха (L-059) и не κ-правило в формулировке Крайгха; совпадение обозначений не означает совпадения величин."))

CELLS.append(dict(
 atom="DIP56-0012", doi="10.1128/aem.37.3.537-543.1979", src="abs",
 start="Large differences (as high as 8.5-fold)", end="among these bacteria.",
 locator="Abstract", access="abstract", kind="condition",
 statement="У пяти видов рубцовых бактерий (Selenomonas ruminantium, Butyrivibrio fibrisolvens, Bacteroides ruminicola, Megasphaera elsdenii, Streptococcus bovis) затраты на поддержание различаются до 8.5 раза при одной и той же среде с глюкозой.",
 mechanism="Величина m определяется не только филогенией и средой: при идентичных условиях культивирования разные виды тратят на поддержание настолько разные доли субстрата, что межвидовая дисперсия m превышает 8-кратный размах.",
 formula=None, symbols={},
 conditions=["непрерывная культура (continuous culture), сложная среда с глюкозой как источником углерода", "пять видов рубцовых бактерий, 30 °C (по Methods)"],
 tags=["maintenance-coefficient", "rumen-bacteria", "interspecific-variation", "continuous-culture"],
 notes="Только аннотация: полный текст (PMC243251) отдаётся Europe PMC/eutils в виде скана без извлекаемого текста, поэтому абсолютные значения m (г/(г·ч)) по видам не приводятся — в ячейке остаётся измеренный размах 8.5×. Годится как контекст к DIP56-0001/0002: m — видоспецифичный, а не универсальный параметр."))

# ---- build ----
rows = []
report = []
for c in CELLS:
    if c["src"] == "abs":
        text = cache[c["doi"]]["abstract"]
        if not text:
            raise SystemExit("empty abstract for " + c["doi"])
    else:
        text = src(c["src"])
    q = excerpt(text, c["start"], c["end"])
    wc = len(q.split())
    body_ok = q in text
    if not body_ok:
        raise SystemExit("quote not verbatim for " + c["atom"])
    if wc < 10 or wc > 30:
        raise SystemExit("wordcount out of range %s: %d" % (c["atom"], wc))
    if cache[c["doi"]]["doi"].lower() != c["doi"].lower():
        raise SystemExit("DOI mismatch: " + c["doi"] + " vs " + cache[c["doi"]]["doi"])
    row = {
        "atom": c["atom"],
        "statement": c["statement"],
        "domain": "membranes.bioenergetics",
        "kind": c["kind"],
        "mechanism": c["mechanism"],
        "formula": c["formula"],
        "symbols": c["symbols"],
        "conditions": c["conditions"],
        "works": [{"doi": c["doi"], "locator": c["locator"], "access": c["access"], "quote": q}],
        "confidence": "medium",
        "locator_status": "verified",
        "tags": c["tags"],
        "notes": c["notes"],
    }
    rows.append(row)
    report.append((c["atom"], c["doi"], cache[c["doi"]]["year"], wc, c["src"], c["kind"]))

with open(OUT, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("\nWROTE", OUT, len(rows), "cells")
for a, d, y, wc, s, k in report:
    print("%s | %-34s | %s | %2d words | %-18s | %s" % (a, d, y, wc, s, k))
uniq = sorted(set(r[1] for r in report))
print("unique DOIs:", len(uniq))
for d in uniq:
    print("  ", d, "->", cache[d]["title"][:75])
