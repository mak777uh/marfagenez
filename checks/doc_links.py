#!/usr/bin/env python3
"""doc_links.py -- a link to a file that does not exist is a broken promise.

The docs corpus is the agent's map; a dead relative link costs a round of guessing. This check
walks every markdown file in the repository, resolves relative .md links and fails when a target
is missing. External links are not fetched (no network here) and are skipped by scheme.

Exit 0 = all relative links resolve; 1 = report of the broken ones.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([A-Za-z0-9_./-]+\.md)(?:#[^)]*)?\)")
SKIP = {"node_modules", ".git", ".lake", "target", "results"}


def markdown_files():
    for p in ROOT.rglob("*.md"):
        if any(part in SKIP for part in p.parts):
            continue
        yield p


ALLOW = pathlib.Path(__file__).resolve().parent / "doc_links_allow.txt"


def allowed():
    if not ALLOW.exists():
        return set()
    out = set()
    for line in ALLOW.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def main():
    healthy = allowed()
    known, broken = [], []
    for p in markdown_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://")):
                continue
            path = (p.parent / target).resolve()
            if not path.exists():
                key = str(p.relative_to(ROOT)) + " -> " + target
                if key in healthy:
                    known.append(key)
                    continue
                hint = [q for q in ROOT.rglob(pathlib.Path(target).name) if q.is_file()][:1]
                broken.append((str(p.relative_to(ROOT)), target, str(hint[0].relative_to(ROOT)) if hint else ""))
    if not broken:
        print("ссылки в документации: все относительные .md разрешаются" +
              ((" (известных мёртвых: " + str(len(known)) + ")") if known else ""))
        return 0
    print("битые ссылки: " + str(len(broken)))
    for src, target, hint in broken:
        print("  " + src + " -> " + target + (("  (есть: " + hint + ")") if hint else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
