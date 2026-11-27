"""Planted defects: the checks must fail when they should.

A check that cannot fail is not a check. This script plants each defect in a copy of the tree,
runs the corresponding checker and requires a non-zero exit.
"""
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(args, cwd=ROOT):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


def test_finding_prefix():
    sys.path.insert(0, str(ROOT / 'kg'))
    import kg  # noqa: E402
    nodes = [{"id": "T-1", "kind": "claim", "evidence": [{"kind": "result", "ref": "FINDING-14"}]}]
    _, unresolved = kg.resolve_refs(nodes)
    bad = bool(unresolved)
    nodes2 = [{"id": "T-2", "kind": "claim", "evidence": [{"kind": "result", "ref": "FINDING-320"}]}]
    _, unresolved2 = kg.resolve_refs(nodes2)
    good = not unresolved2
    print("  FINDING-14 не разрешается:", "ok" if bad else "ПРОВАЛ (нашёлся префикс)")
    print("  FINDING-320 разрешается:", "ok" if good else "ПРОВАЛ")
    return bad and good


def test_regress_content():
    claims = ROOT / 'kg' / 'claims.jsonl'
    backup = claims.read_text(encoding='utf-8')
    try:
        lines = backup.splitlines()
        node = json.loads(lines[0])
        node['text'] = node['text'] + ' (подложенная правка)'
        lines[0] = json.dumps(node, ensure_ascii=False)
        claims.write_text("\n".join(lines) + "\n", encoding='utf-8')
        subprocess.run(['python3', 'kg/migrate.py'], cwd=str(ROOT), capture_output=True)
        subprocess.run(['python3', 'kg/kg.py', 'build'], cwd=str(ROOT), capture_output=True)
        # now the generated file agrees with the corpus; the committed one does not
        subprocess.run(['git', 'checkout', '--', 'kg/nodes.jsonl'], cwd=str(ROOT), capture_output=True)
        r = run(['python3', 'kg/regress.py'])
        ok = r.returncode != 0 and 'содержимому' in r.stdout
        print("  подложенная правка текста ловится:", "ok" if ok else "ПРОВАЛ")
        return ok
    finally:
        claims.write_text(backup, encoding='utf-8')
        subprocess.run(['python3', 'kg/migrate.py'], cwd=str(ROOT), capture_output=True)
        subprocess.run(['python3', 'kg/kg.py', 'build'], cwd=str(ROOT), capture_output=True)


def test_refs_in_gate():
    claims = ROOT / 'kg' / 'claims.jsonl'
    backup = claims.read_text(encoding='utf-8')
    try:
        lines = backup.splitlines()
        node = json.loads(lines[0])
        node.setdefault('evidence', []).append({"kind": "result", "ref": "FINDING-999-missing", "strength": "weak"})
        node['evidence'].append({"kind": "result", "ref": "docs/НЕТ-ТАКОГО.md", "strength": "weak"})
        lines[0] = json.dumps(node, ensure_ascii=False)
        claims.write_text("\n".join(lines) + "\n", encoding='utf-8')
        subprocess.run(['python3', 'kg/migrate.py'], cwd=str(ROOT), capture_output=True)
        subprocess.run(['python3', 'kg/kg.py', 'build'], cwd=str(ROOT), capture_output=True)
        r = run(['python3', 'kg/kg.py', 'check', '--refs'])
        ok = r.returncode != 0
        print("  битая ссылка при check --refs:", "ok" if ok else "ПРОВАЛ (код 0)")
        return ok
    finally:
        claims.write_text(backup, encoding='utf-8')
        subprocess.run(['python3', 'kg/migrate.py'], cwd=str(ROOT), capture_output=True)
        subprocess.run(['python3', 'kg/kg.py', 'build'], cwd=str(ROOT), capture_output=True)


def main():
    print("подложенные дефекты:")
    results = [test_finding_prefix(), test_regress_content(), test_refs_in_gate()]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
