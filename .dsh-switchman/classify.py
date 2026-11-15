"""Classify every uncommitted change: mine, the old agent's, or line-ending churn."""

import subprocess

MINE = {
    "laws/Medium/Child.lean",
    "laws/Medium/Corrected.lean",
    "run.sh",
    "checks/room_model.py",
    "checks/corrected_model.py",
    "checks/budget_model.py",
}


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, cwd="/root/marfagenez")


def main():
    st = run("git", "status", "--porcelain=v1").stdout.splitlines()
    deleted, modified, untracked = [], [], []
    for line in st:
        code, path = line[:2], line[3:]
        if code == " D":
            deleted.append(path)
        elif code == " M":
            modified.append(path)
        elif code == "??":
            untracked.append(path)

    print(f"deleted {len(deleted)}  modified {len(modified)}  untracked {len(untracked)}")
    print()

    print("=== modified tracked files ===")
    for p in modified:
        head = run("git", "show", f"HEAD:{p}")
        head_crlf = "\r\n" in head.stdout
        with open(f"/root/marfagenez/{p}", "rb") as fh:
            cur = fh.read()
        cur_crlf = b"\r\n" in cur
        churn = head_crlf != cur_crlf
        tag = "MINE" if p in MINE else ("CRLF-CHURN" if churn else "OLD-AGENT")
        print(f"  {tag:12} {p}")
    print()

    print("=== untracked: mine vs old agent ===")
    mine_u = [p for p in untracked if p in MINE]
    old_u = [p for p in untracked if p not in MINE]
    print(f"  mine ({len(mine_u)}): {mine_u}")
    print(f"  old agent ({len(old_u)}):")
    for p in old_u:
        print(f"    {p}")
    print()

    print("=== deleted (old agent) ===")
    for p in deleted:
        print(f"    {p}")


if __name__ == "__main__":
    main()
