import json

P = "/root/marfagenez/literature/dips/reports/dip-2026-11-24-56.jsonl"
rows = [json.loads(l) for l in open(P) if l.strip()]
by = {r["atom"]: r for r in rows}

by["DIP56-0003"]["works"][0]["locator"] = ("Results, абзац с «the retentostat cultures equaled 0.0031 ± 0.0001 …», "
    "непосредственно перед «An alternative explanation for this deviation …»; Fig. 6")
by["DIP56-0003"]["notes"] = ("Прямое противоречие двухкомпонентной модели Pirt (уже внесена как B7-06-0003/B7-10-0003): "
    "там m — константа, здесь m зависит от μ. Цифры: хемостат 0.0100 ± 0.0023, ретентостат 0.0031 ± 0.0001, "
    "q_S в конце 0.004 (40% от m_S). Авторы пишут, что «growth-rate-dependent maintenance energy requirement "
    "has not been observed in a yeast or fungus so far», а для прокариот такие данные есть (E. coli, "
    "Bacillus polymyxa, Nitrobacter winogradskyi, Nitrosomonas europaea) — т.е. это не ошибка измерения, "
    "а реальная разница между группами.")

by["DIP56-0007"]["works"][0]["locator"] = ("Body, абзац «…sodium pumping accounts for more than 55% of ATP use…» "
    "(обсуждение бюджета Na+-насоса; рядом — пересчёт Attwell & Laughlin / Harris & Attwell)")

by["DIP56-0011"]["works"][0]["locator"] = ("Results, абзац «How can we check that the resulting parameters in AmP are "
    "not dominated by the use of pseudo-data?», предложение 4 (распределение κ по видам базы AmP)")

with open(P, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("patched", len(rows))
for a in ("DIP56-0003", "DIP56-0007", "DIP56-0011"):
    print(a, "->", by[a]["works"][0]["locator"][:90])
