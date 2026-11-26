"""Проверка `check`-строк из инбокса `kg`: цитата должна быть подстрокой источника.

Для каждой строки `docs/KG-CHECKS.jsonl`:
  1. берём DOI/URL;
  2. тянем аннотацию: OpenAlex (inverted index → текст) или EuropePMC (abstractText);
  3. проверяем, что `quote` — подстрока (нормализация: пробелы, регистр, юникод-дефисы);
  4. пишем вердикт: confirmed / not_found_in_abstract / no_source.

Запуск:
    python3 tools/kg_check_verify.py            проверить все новые строки
    python3 tools/kg_check_verify.py --report   только отчёт по уже проверенным
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = ROOT / 'docs' / 'KG-CHECKS.jsonl'
VERDICTS = ROOT / 'docs' / 'KG-CHECKS-VERIFIED.jsonl'


def norm(text: str) -> str:
    t = str(text).lower()
    t = t.replace('‐', '-').replace('‑', '-').replace('–', '-').replace('—', '-')
    t = t.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'[−–]', '-', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip(' .;,')


def openalex_abstract(doi: str) -> str:
    url = f'https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}'
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    inv = data.get('abstract_inverted_index') or {}
    if not inv:
        return ''
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return ' '.join(pos[i] for i in sorted(pos))


def europepmc_abstract(doi: str) -> str:
    q = urllib.parse.quote(f'DOI:"{doi}"')
    url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=core'
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    res = (data.get('resultList') or {}).get('result') or []
    if not res:
        return ''
    return res[0].get('abstractText') or ''


def fetch_abstract(doi: str) -> tuple[str, str]:
    for name, fn in (('openalex', openalex_abstract), ('europepmc', europepmc_abstract)):
        try:
            text = fn(doi)
        except Exception:
            text = ''
        if text:
            return text, name
    return '', ''


def verify(limit: int | None = None) -> int:
    rows = [json.loads(l) for l in CHECKS.read_text(encoding='utf-8').splitlines() if l.strip()]
    done = set()
    if VERDICTS.exists():
        done = {json.loads(l).get('id') + '|' + str(json.loads(l).get('quote'))[:40]
                for l in VERDICTS.read_text(encoding='utf-8').splitlines() if l.strip()}
    todo = [r for r in rows if (r.get('id') + '|' + str(r.get('quote'))[:40]) not in done]
    if limit:
        todo = todo[:limit]
    print(f'строк в инбоксе: {len(rows)}; уже проверено: {len(done)}; к проверке: {len(todo)}')

    out = []
    for r in todo:
        src = r.get('source') or {}
        doi = src.get('doi') or ''
        quote = r.get('quote') or ''
        text, via = ('', '')
        if doi:
            text, via = fetch_abstract(doi)
        verdict = 'no_source'
        if text:
            verdict = 'confirmed' if norm(quote) in norm(text) else 'not_found_in_abstract'
        row = {'id': r.get('id'), 'verdict_claim': r.get('verdict'), 'quote': quote,
               'doi': doi, 'level': src.get('level'), 'abstract_via': via,
               'verify': verdict}
        out.append(row)
        print(f"  {r.get('id'):7} {verdict:22} via={via or '—':9} {quote[:50]}")

    if out:
        VERDICTS.parent.mkdir(parents=True, exist_ok=True)
        with VERDICTS.open('a', encoding='utf-8') as fh:
            for row in out:
                fh.write(json.dumps(row, ensure_ascii=False) + '\n')
        counts: dict[str, int] = {}
        for row in out:
            counts[row['verify']] = counts.get(row['verify'], 0) + 1
        print('\nитог:', counts)
    return 0


def report() -> int:
    if not VERDICTS.exists():
        print('проверок ещё нет')
        return 0
    rows = [json.loads(l) for l in VERDICTS.read_text(encoding='utf-8').splitlines() if l.strip()]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r['verify']] = counts.get(r['verify'], 0) + 1
    print(f'проверено строк: {len(rows)}')
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    bad = [r for r in rows if r['verify'] != 'confirmed']
    print('\nне подтверждённые цитаты:')
    for r in bad:
        print(f"  {r['id']:7} {r['verify']:22} {r['doi']}  {r['quote'][:60]}")
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--limit', type=int, default=None)
    a = ap.parse_args()
    raise SystemExit(report() if a.report else verify(a.limit))
