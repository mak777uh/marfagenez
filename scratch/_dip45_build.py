import json, re, subprocess, urllib.parse, sys, os

OUT_DIR = "/root/marfagenez/literature/dips/reports"
TARGET = "dip-2026-11-23-45"


def curl(url):
    r = subprocess.run(["curl", "-s", "-m", "90", url], capture_output=True, text=True)
    return r.stdout


def fulltext(pmcid):
    return curl("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid)


def clean(xml):
    x = re.sub(r"<ref-list.*?</ref-list>", " ", xml, flags=re.S)
    x = re.sub(r"<xref[^>]*>.*?</xref>", "", x, flags=re.S)
    x = re.sub(r"<[^>]+>", " ", x)
    x = x.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    x = re.sub(r"&#x?[0-9a-fA-F]+;", " ", x)
    # strip LaTeX preamble injected by MDPI/Springer math
    x = re.sub(r"\\documentclass(\[[^\]]*\])?\{minimal\}", " ", x)
    x = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]*\}", " ", x)
    x = re.sub(r"\\begin\{document\}", " ", x)
    x = re.sub(r"\\end\{document\}", " ", x)
    x = re.sub(r"\\setlength\{[^}]*\}\{[^}]*\}", " ", x)
    x = re.sub(r"\\begin\{math[a-z]*\}", " ", x)
    x = re.sub(r"\\end\{math[a-z]*\}", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x


_cache = {}


def get_text(pmcid):
    if pmcid not in _cache:
        _cache[pmcid] = clean(fulltext(pmcid))
    return _cache[pmcid]


def window(text, anchor, max_words=30):
    """Return a <=max_words verbatim substring centred on anchor."""
    i = text.find(anchor)
    if i < 0:
        raise SystemExit("ANCHOR NOT FOUND: %r" % anchor[:60])
    # sentence bounds
    start = max(text.rfind(". ", 0, i), text.rfind("; ", 0, i), 0)
    start = start + 2 if start else 0
    end = min([p for p in [text.find(". ", i), text.find("; ", i), len(text)] if p > 0])
    sent = text[start:end + 1].strip()
    words = sent.split()
    if len(words) <= max_words:
        return sent
    # trim around anchor to max_words
    at = text[start:end].find(anchor)
    pre = text[start:start + at].split()
    awords = anchor.split()
    post = text[start + at + len(anchor):end].split()
    keep = max_words - len(awords)
    left = min(len(pre), max(1, keep // 2))
    right = min(len(post), keep - left)
    q = " ".join(pre[-left:] + awords + post[:right])
    # verify verbatim
    if q not in text:
        q2 = " ".join(pre[-left:] + awords + post[:right + 1])
        q = q2 if q2 in text else " ".join(awords[:max_words])
    return q


CELLS = [
    dict(atom="DIP45-0001", pmcid="PMC12818437", doi="10.1073/pnas.2515129123",
         anchor="The cooperative swarm yields an entropy production rate of",
         statement="В кооперативном рое бактерий измеренное производство энтропии достигает σ_S ≈ 10^5 k_B/с (при ΔP_S ≈ 0.5 фВт), то есть скорость роста энтропии в живой микросистеме измерена в абсолютных единицах, а не только в относительных.",
         kind="measurement",
         mechanism="Оптический пинцет удерживает бактерии; по силам и скоростям на траекториях вычисляют диссипируемую мощность, делят на температуру и получают производство энтропии роя. Кооперативное плато даёт σ_S ≈ 10^5 k_B/с.",
         formula="σ_S = ΔP_S / T ≈ 10^5 k_B s^-1",
         symbols={"σ_S": "производство энтропии кооперативного роя", "ΔP_S": "диссипируемая мощность мезоскопической вихревой компоненты (≈0.5 фВт)", "T": "температура"},
         conditions=["бактериальный рой в оптическом пинцете", "кооперативное плато (вихревое движение)", "ΔP_S ≈ 0.5 фВт, то есть ~10^-3 полной пиковаттной мощности", "комнатная температура"],
         tags=["entropy-production", "measured", "bacteria", "optical-tweezers", "k_B-per-s"]),
    dict(atom="DIP45-0002", pmcid="PMC12818437", doi="10.1073/pnas.2515129123",
         anchor="They quantified power dissipation up to",
         statement="Мощность диссипации в активной бактериальной системе, измеренная по силам оптического пинцета, достигает 10^6 k_B T/с (порядка фемтоватт), что задаёт верхнюю измеренную планку диссипации на уровне отдельной микросистемы.",
         kind="measurement",
         mechanism="Диссипируемая мощность оценивается из баланса сил (сила ловушки минус сила трения), затем переводится в единицы k_B T/с; верхняя оценка — 10^6 k_B T/с.",
         formula="P_diss up to 10^6 k_B T/s (~fW)",
         symbols={"P_diss": "мощность диссипации", "k_B T": "тепловая единица энергии"},
         conditions=["бактериальный рой, измерение силами оптического пинцета", "активное движение (breaststroke-подобное)", "порядок величины — фемтоватты"],
         tags=["dissipation", "measured", "optical-tweezers", "fW", "k_BT-per-s"]),
    dict(atom="DIP45-0003", pmcid="PMC10083585", doi="10.1073/pnas.2207662120",
         anchor="Averaging across replicate samples, the power dissipated as heat was found to be",
         statement="Калориметрически измеренная мощность тепловой диссипации активного цитоскелетного геля (микротрубочки + кинезин K401) составляет P_diss = 94 ± 20 нВт, при разрешении калориметра ~200 пВт.",
         kind="measurement",
         mechanism="Пикокалориметр измеряет тепловыделение микролитровых образцов активного геля; среднее по повторным образцам даёт 94 ± 20 нВт, что на девять порядков превышает вязкую диссипацию крупномасштабных течений.",
         formula="P_diss = 94 ± 20 nW",
         symbols={"P_diss": "полная мощность, диссипируемая в тепло", "nW": "нановатт"},
         conditions=["активный гель микротрубочек с кинезином K401", "объём образца 0.5 мкл", "разрешение калориметра ~200 пВт", "ATP-регенерация"],
         tags=["calorimetry", "measured", "dissipation", "active-matter", "nW"]),
    dict(atom="DIP45-0004", pmcid="PMC10083585", doi="10.1073/pnas.2207662120",
         anchor="we define the fraction of energy propagated to large-scale flows",
         statement="Доля энергии, дошедшая до крупномасштабных течений, в активном геле измерена как η = P_flow/P_diss ≈ 2×10^-9: почти вся диссипация уходит в тепло, а не в механическое движение.",
         kind="measurement",
         mechanism="Сравнение измеренной тепловой диссипации P_diss = 94 ± 20 нВт с оценкой вязкой диссипации крупномасштабных течений P_flow ≈ 2×10^-7 нВт даёт долю переноса энергии η ≈ 2×10^-9.",
         formula="η = P_flow / P_diss ≈ 2×10^-9",
         symbols={"η": "доля энергии, переданной крупномасштабным течениям", "P_flow": "вязкая диссипация крупномасштабных течений (≈2×10^-7 нВт)", "P_diss": "полная тепловая диссипация"},
         conditions=["активный гель микротрубочек/K401", "вязкость μ ≈ 1 мПа·с", "объём V_0 = 0.5 мкл"],
         tags=["efficiency", "measured", "energy-propagation", "active-matter"]),
    dict(atom="DIP45-0005", pmcid="PMC12972615", doi="10.2142/biophysico.bppb-v23.0003",
         anchor="an estimated energy conversion efficiency of ~20%",
         statement="КПД преобразования энергии кинезином, измеренный через нарушение флуктуационно-диссипативного соотношения (равенство Харада–Саса), составляет около 20% при 10 мкМ ATP.",
         kind="measurement",
         mechanism="Магнитные/оптические пинцеты + равенство Харада–Саса: измеряют спектр флуктуаций и спектр отклика, из их несовпадения получают неравновесную диссипацию J_x, затем КПД = (−F_0·v̄ + J_x)/(Δμ·τ).",
         formula="η = (−F_0 v̄ + J_x) / (Δμ τ) ≈ 20%",
         symbols={"η": "КПД преобразования энергии", "F_0": "приложенная нагрузка", "v̄": "средняя скорость", "J_x": "осевая неравновесная диссипация", "Δμ": "свободная энергия ATP", "τ": "время цикла"},
         conditions=["кинезин-1, in vitro", "10 мкМ ATP", "стоп-сила ~6 пН", "n = 13 молекул", "комнатная температура"],
         tags=["efficiency", "measured", "kinesin", "Harada-Sasa", "FDT-violation"]),
    dict(atom="DIP45-0006", pmcid="PMC12972615", doi="10.2142/biophysico.bppb-v23.0003",
         anchor="Nonequilibrium dissipation",
         statement="Измеренная неравновесная (осевая) диссипация для кинезин-1 при 10 мкМ ATP составляет J_x = 18 ± 14 пН·нм/с при внешней мощности 100 ± 60 пН·нм/с и полном потоке энергии Δμ·τ = 630 ± 380 пН·нм/с.",
         kind="measurement",
         mechanism="Равенство Харада–Саса по одной координате: J_x = γv̄² + γ∫[C̃(f) − 2k_BT R̃′(f)]df; вклады сравниваются с внешней мощностью и полным потоком энергии ATP.",
         formula="J_x = γ v̄^2 + γ ∫ [ C̃(f) − 2k_B T R̃′(f) ] df = 18 ± 14 pN nm/s",
         symbols={"J_x": "осевая неравновесная диссипация", "γ": "коэффициент трения", "C̃(f)": "спектр флуктуаций", "R̃′(f)": "действительная часть спектра отклика"},
         conditions=["кинезин-1 in vitro, 10 мкМ ATP", "n = 13", "сравнение с ATP-free контролем (FDT выполняется)"],
         tags=["dissipation", "measured", "Harada-Sasa", "kinesin", "pN-nm-per-s"]),
    dict(atom="DIP45-0007", pmcid="PMC11638961", doi="10.1021/acs.nanolett.4c04109",
         anchor="The average torque was 22.2 ± 5.6 pN nm",
         statement="Крутящий момент одиночной V-ATPase, измеренный модифицированной флуктуационной теоремой, равен 22,2 ± 5,6 пН·нм (N = 9 молекул), что согласуется с независимой оценкой 23 ± 10 пН·нм.",
         kind="measurement",
         mechanism="Janus-наночастица 500 нм (кремний/золото) как зонд вращения; модифицированная флуктуационная теорема для вращательного движения связывает флуктуации зонда с генерируемым моментом; Δt = 10 мс.",
         formula="N = 22.2 ± 5.6 pN nm (fluctuation theorem)",
         symbols={"N": "крутящий момент", "pN nm": "единица момента"},
         conditions=["EhV_oV_1 (V-ATPase Enterococcus hirae)", "25 °C, 5 мМ ATP, 300 мМ NaCl", "1000 кадр/с, 1 мс разрешение", "N = 9 молекул"],
         tags=["fluctuation-theorem", "measured", "torque", "V-ATPase", "rotary-motor"]),
    dict(atom="DIP45-0008", pmcid="PMC5070456", doi="10.2142/biophysics.8.67",
         anchor="we obtained 33±2.2 pNnm as the rotary torque",
         statement="Флуктуационная теорема даёт крутящий момент V1-ATPase 33 ± 2,2 пН·нм и дикого типа F1-ATPase 38 ± 2,7 пН·нм; таким образом флуктуационное соотношение используется как измерительный прибор с численной погрешностью.",
         kind="measurement",
         mechanism="Определяют производство энтропии σ = FΔX/k_BT по распределению смещений зонда P(σ), затем из нарушения симметрии распределения извлекают силу/момент; метод применён к F1- и V1-ATPase.",
         formula="σ = F ΔX / k_B T ; N = 38 ± 2.7 pN nm (F1, WT), 33 ± 2.2 pN nm (V1)",
         symbols={"σ": "производство энтропии за интервал Δt", "F": "сила/обобщённая сила", "ΔX": "смещение", "N": "крутящий момент"},
         conditions=["одиночные молекулы F1-ATPase и V1-ATPase", "зонд-дуплекс полистирольных бусин", "ΔT = 0.02 и 0.04 мс для P(σ)"],
         tags=["fluctuation-theorem", "measured", "torque", "F1-ATPase", "entropy-production-distribution"]),
    dict(atom="DIP45-0009", pmcid="PMC9674227", doi="10.1073/pnas.2208083119",
         anchor="the total heat dissipated is ≈ 80% of the input energy",
         statement="Для кинезина измеренная доля тепла составляет ≈80% входной энергии, то есть только ≈20% энергии гидролиза ATP идёт на полезную работу при F = 2 пН.",
         kind="measurement",
         mechanism="Из экспериментальных данных по силе–скорости и теоретической модели энергетического баланса оценивают, что ≈80% входной энергии диссипирует в тепло, а КПД ≈20%.",
         formula="Q_heat / E_in ≈ 80% ; η ≈ 20%",
         symbols={"Q_heat": "диссипированное тепло", "E_in": "входная энергия ATP", "η": "КПД"},
         conditions=["кинезин, сопротивление F = 2 пН", "in vitro эксперимент", "оценка по экспериментальным данным и модели"],
         tags=["efficiency", "measured", "kinesin", "heat-fraction"]),
    dict(atom="DIP45-0010", pmcid="PMC9674227", doi="10.1073/pnas.2208083119",
         anchor="we find that Δ μ m c ≈ 9.2 k B T",
         statement="При F = 2 пН химические потенциалы на шаг кинезина измерены как Δμ_mc ≈ 9,2 k_B T и Δμ_ch ≈ 11,3 k_B T — диссипация на шаг выражена прямо в единицах k_B T.",
         kind="measurement",
         mechanism="Из экспериментальных распределений и модели двухголового мотора извлекают перепады химического потенциала на шаг (механо-химический и химический), выраженные в k_B T при заданной нагрузке.",
         formula="Δμ_mc ≈ 9.2 k_B T ; Δμ_ch ≈ 11.3 k_B T at F = 2 pN",
         symbols={"Δμ_mc": "механо-химический перепад потенциала на шаг", "Δμ_ch": "химический перепад на шаг", "F": "сопротивляющаяся сила"},
         conditions=["кинезин, F = 2 пН (сила, использованная в эксперименте по тепловой диссипации)", "in vitro", "модель двухголового мотора"],
         tags=["dissipation-per-step", "measured", "kinesin", "k_BT", "chemical-potential"]),
]

def build():
    rows = []
    for c in CELLS:
        txt = get_text(c["pmcid"])
        q = window(txt, c["anchor"])
        assert q in txt, "quote not verbatim: " + c["atom"]
        assert len(q.split()) >= 8, "quote too short: " + c["atom"]
        row = {
            "atom": c["atom"],
            "statement": c["statement"],
            "domain": "thermodynamics.stochastic",
            "kind": c["kind"],
            "mechanism": c["mechanism"],
            "formula": c["formula"],
            "symbols": c["symbols"],
            "conditions": c["conditions"],
            "works": [{"doi": c["doi"], "locator": "fulltext:%s" % c["pmcid"],
                       "access": "open-access (Europe PMC fullTextXML)",
                       "quote": q}],
            "confidence": "medium",
            "locator_status": "verified",
            "tags": c["tags"],
            "notes": "Цитата — дословная подстрока текста полного текста, полученного через Europe PMC REST fullTextXML (%s); проверено программно (quote in text == True)." % c["pmcid"],
        }
        rows.append((row, c, len(txt)))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, TARGET + ".jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for row, c, _ in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("wrote", path, len(rows), "cells")
    for row, c, n in rows:
        print(row["atom"], c["pmcid"], "words=%d" % len(row["works"][0]["quote"].split()))
        print("   ", row["works"][0]["quote"])

if __name__ == "__main__":
    build()
