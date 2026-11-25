"""Reznik 2013, Dataset S1 (XLSX): извлечь таблицы и проверить ранее неверифицированные числа.

Файл: docs/artifacts/reznik2013-dataset-s1.xlsx (скачан с PLOS, DOI 10.1371/journal.pcbi.1003195,
supplementary s001). Источник был помечен как «недоступен»: считалось, что PLOS отдаёт TIFF под именем
`.xlsx`. Проверка 25.11.2026: файл настоящий XLSX (PK-архив), три листа — `Figure 2`, `Figure 3`,
`Figure 5C`.

Запуск:
    python3 tools/reznik_dataset.py            # сводка и поиск чисел
    python3 tools/reznik_dataset.py --write    # выгрузить CSV рядом с XLSX
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
XLSX = ROOT / "docs" / "artifacts" / "reznik2013-dataset-s1.xlsx"
OUTDIR = ROOT / "docs" / "artifacts"

# числа, которые в карте стояли как неверифицированные
RECORDED = {
    "пируват": -0.0368,
    "ATP": -15.1745,
    "UTP": -9.0416,
}


def shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    xml = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
    out = []
    for si in re.findall(r"<si>(.*?)</si>", xml, re.S):
        text = "".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))
        out.append(text)
    return out


def col(row_xml: str) -> dict[int, str]:
    cells = {}
    for m in re.finditer(r"<c r=\"([A-Z]+)(\d+)\"([^>]*)>(.*?)</c>", row_xml, re.S):
        letters, _row, attrs, body = m.groups()
        idx = 0
        for ch in letters:
            idx = idx * 26 + (ord(ch) - 64)
        idx -= 1
        t = re.search(r't="([^"]+)"', attrs)
        v = re.search(r"<v>(.*?)</v>", body, re.S)
        val = v.group(1) if v else ""
        if t and t.group(1) == "s" and val != "":
            val = f"@@{val}"
        cells[idx] = val
    return cells


def parse_sheet(z: zipfile.ZipFile, name: str, ss: list[str]) -> list[list[str]]:
    xml = z.read(name).decode("utf-8", "ignore")
    rows = []
    for row_xml in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
        cells = col(row_xml)
        if not cells:
            continue
        width = max(cells) + 1
        vals = []
        for i in range(width):
            v = cells.get(i, "")
            if v.startswith("@@"):
                try:
                    v = ss[int(v[2:])]
                except (ValueError, IndexError):
                    v = ""
            vals.append(v)
        rows.append(vals)
    return rows


def main(argv: list[str]) -> int:
    if not XLSX.exists():
        print(f"нет файла {XLSX}")
        return 1
    z = zipfile.ZipFile(XLSX)
    ss = shared_strings(z)
    wb = z.read("xl/workbook.xml").decode("utf-8", "ignore")
    sheets = re.findall(r"<sheet[^>]*name=\"([^\"]+)\"", wb)

    all_rows: dict[str, list[list[str]]] = {}
    for i, title in enumerate(sheets, start=1):
        rows = parse_sheet(z, f"xl/worksheets/sheet{i}.xml", ss)
        all_rows[title] = rows
        print(f"лист «{title}»: строк {len(rows)}, ширина {max((len(r) for r in rows), default=0)}")
        for r in rows[:3]:
            print("   ", r[:8])

    # поиск записанных чисел
    print()
    print("поиск ранее неверифицированных чисел:")
    numbers: dict[str, list[tuple[str, int, int, str]]] = {}
    for title, rows in all_rows.items():
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                try:
                    x = float(cell)
                except (TypeError, ValueError):
                    continue
                numbers.setdefault(f"{x:.4f}", []).append((title, ri + 1, ci + 1, cell))
    for name, target in RECORDED.items():
        key = f"{target:.4f}"
        hits = numbers.get(key, [])
        if hits:
            for h in hits[:3]:
                print(f"  {name} = {target}: НАЙДЕНО на листе «{h[0]}», строка {h[1]}, колонка {h[2]}")
        else:
            print(f"  {name} = {target}: не найдено точным совпадением до 4 знаков")

    if "--write" in argv:
        OUTDIR.mkdir(parents=True, exist_ok=True)
        for title, rows in all_rows.items():
            safe = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")
            p = OUTDIR / f"reznik2013-{safe}.csv"
            with open(p, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows(rows)
            print(f"записано: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
