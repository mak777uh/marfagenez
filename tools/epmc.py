"""Europe PMC: поиск по полному тексту и аннотациям — канал, которого у нас не было.

OpenAlex даёт метаданные и аннотации, но не ищет по телу статьи. Europe PMC ищет по полному тексту
открытых статей, отдаёт abstractText и PMCID — то есть позволяет закрывать пустоты вида «есть ли работа,
где измерены и X, и Y».

Usage:
    python3 tools/epmc.py search "запрос" [--n 10]
    python3 tools/epmc.py abstract PMC1234567
    python3 tools/epmc.py fulltext PMC1234567 [--grep слово]
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import urllib.parse

CURL = "/mnt/c/Windows/System32/curl.exe"
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def curl(url: str) -> str:
    out = subprocess.run([CURL, "-sS", "-L", "--compressed", "-m", "60", url],
                         capture_output=True, text=True, timeout=120)
    return out.stdout


def search(query: str, n: int = 10) -> int:
    url = (BASE + "/search?query=" + urllib.parse.quote(query)
           + f"&format=json&pageSize={n}&resultType=core")
    try:
        data = json.loads(curl(url))
    except Exception:
        print("не удалось разобрать ответ")
        return 1
    results = (data.get("resultList") or {}).get("result") or []
    print(f"найдено: {data.get('hitCount')} (показано {len(results)})")
    for r in results:
        title = (r.get("title") or "")[:95]
        year = r.get("pubYear")
        doi = r.get("doi")
        pmcid = r.get("pmcid")
        has_abs = "да" if r.get("abstractText") else "нет"
        print(f"\n- {title}\n  {year} | doi:{doi} | {pmcid} | аннотация: {has_abs}")
    return 0


def abstract(pmcid: str) -> int:
    url = BASE + f"/{pmcid}/fullTextXML"
    text = curl(url)
    if not text.strip().startswith("<"):
        print("нет XML (возможно, нет открытого текста)")
        return 1
    import re
    m = re.search(r"<abstract.*?</abstract>", text, re.S)
    if not m:
        print("в XML нет abstract")
        return 1
    clean = re.sub(r"<[^>]+>", " ", m.group(0))
    print(" ".join(clean.split())[:3000])
    return 0


def fulltext(pmcid: str, needle: str | None) -> int:
    url = BASE + f"/{pmcid}/fullTextXML"
    text = curl(url)
    if not text.strip().startswith("<"):
        print("нет XML")
        return 1
    import re
    clean = " ".join(re.sub(r"<[^>]+>", " ", text).split())
    print(f"символов: {len(clean)}")
    if needle:
        low, n = clean.lower(), needle.lower()
        idx = low.find(n)
        while idx != -1:
            print("...", clean[max(0, idx - 200): idx + 260].replace("\n", " "), "...")
            idx = low.find(n, idx + 1)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    verb, rest = argv[0], argv[1:]
    if verb == "search":
        n = int(rest[rest.index("--n") + 1]) if "--n" in rest else 10
        return search(rest[0], n)
    if verb == "abstract":
        return abstract(rest[0])
    if verb == "fulltext":
        needle = rest[rest.index("--grep") + 1] if "--grep" in rest else None
        return fulltext(rest[0], needle)
    print("глаголы: search, abstract, fulltext")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
