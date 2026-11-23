import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ft as H

ids = sys.argv[1:]
for p in ids:
    for attempt in range(2):
        try:
            t = H.load_text(p)
            print('OK', p, len(t), flush=True)
            break
        except Exception as e:
            print('FAIL', p, attempt, e, flush=True)
            time.sleep(4)
    time.sleep(1.2)
print('done', flush=True)
