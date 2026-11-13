import re, os, subprocess, json, glob

ROOT = "/root/marfagenez"
os.chdir(ROOT)

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

# --- live numbers ---
medium_files = len(glob.glob("laws/Medium/*.lean"))
medium_thm = int(sh("grep -rhoE '^(theorem|lemma) [A-Za-z0-9_]+' laws/Medium/*.lean | wc -l"))
medium_sorry = int(sh("grep -rn 'sorry' laws/Medium/*.lean | wc -l"))
legacy_files = len(glob.glob("laws/Legacy/*.lean"))
legacy_thm = int(sh("grep -rhoE '^(theorem|lemma) [A-Za-z0-9_]+' laws/Legacy/*.lean | wc -l"))
legacy_sorry = int(sh("grep -rn 'sorry' laws/Legacy/*.lean | wc -l"))

verd = {"passed": 0, "failed": 0, "void": 0}
nres = 0
for f in glob.glob("results/**/run-*.json", recursive=True):
    if "_archive" in f:
        continue
    nres += 1
    v = json.load(open(f)).get("verdict")
    if isinstance(v, dict):
        v = v.get("kind")
    verd[v] = verd.get(v, 0) + 1

nexp = len(glob.glob("checks/exp*.py"))
ndocs = len(glob.glob("docs/*.md"))
nfind = len(glob.glob("docs/FINDING-*.md"))

print("medium files", medium_files, "thm", medium_thm, "sorry", medium_sorry)
print("legacy files", legacy_files, "thm", legacy_thm, "sorry", legacy_sorry)
print("results", nres, verd)
print("checks", nexp, "docs", ndocs, "findings", nfind)
