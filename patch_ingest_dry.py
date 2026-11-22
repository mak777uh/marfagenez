import pathlib
import re

p = pathlib.Path('/root/marfagenez/tools/map_ingest.py')
s = p.read_text(encoding='utf-8')

# 1) document the flag
s = s.replace('''  * отчёт всегда пишется, даже если всё отклонено.''',
              '''  * отчёт всегда пишется, даже если всё отклонено;
  * `--dry-run` действительно ничего не пишет (проверено на инциденте: дип вызвал несуществующий флаг,
    флаг был молча проигнорирован, и ячейки попали в карту; теперь неизвестные флаги — ошибка).''')

# 2) strict flag parsing + dry-run
old = '''def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    patterns = [a for a in argv if not a.startswith("--")]'''
new = '''KNOWN_FLAGS = ("--report", "--edges", "--dry-run")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 2
    # Молчаливое игнорирование флага — это ложное подтверждение. Именно так `--dry-run`, которого не было,
    # записал партию в карту. Неизвестный флаг теперь ошибка.
    for arg in argv:
        if arg.startswith("--") and arg not in KNOWN_FLAGS:
            print(f"неизвестный флаг {arg}; известные: {', '.join(KNOWN_FLAGS)}", file=sys.stderr)
            return 2
    dry = "--dry-run" in argv
    patterns = [a for a in argv if not a.startswith("--")]'''
if old in s:
    s = s.replace(old, new, 1)

# 3) guard the writes
s = s.replace('''        EDGES.parent.mkdir(parents=True, exist_ok=True)
        EDGES.write_text''', '''        if not dry:
            EDGES.parent.mkdir(parents=True, exist_ok=True)
        if not dry:
            EDGES.write_text''')
s = s.replace('''    MAP.mkdir(parents=True, exist_ok=True)
    ATOMS.write_text''', '''    if not dry:
        MAP.mkdir(parents=True, exist_ok=True)
    if not dry:
        ATOMS.write_text''')
s = s.replace('''    if report_path:''', '''    if dry:
        print("dry-run: файлы не записаны")
        return 0
    if report_path:''')

p.write_text(s, encoding='utf-8')
print('map_ingest: strict flags, real dry-run')
