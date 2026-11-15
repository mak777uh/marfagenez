import sys
sys.path.insert(0,".dsh-switchman")
from trace_steps import run
frames,h = run(16,3.0,0.8,"proportional",2005,1,1)
for i,f in enumerate(frames):
    if f["step"] in (1999,2000,2001,2002):
        print("idx",i,"step",f["step"],"alive",sum(1 for s in f["samples"] if s["alive"]),"E",[round(s["energy"],6) for s in f["samples"][:3]],"dmg",[round(s["damage"],6) for s in f["samples"][:3]])
