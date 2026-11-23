import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harvest2 as H

ids = sys.argv[1:]
for p in ids:
    fn = os.path.join(H.FT, p + '.xml')
    if os.path.exists(fn) and os.path.getsize(fn) > 2000:
        print('cached', p, flush=True)
        continue
    for attempt in range(3):
        try:
            xml = H.fulltext(p)
            t = H.text(xml)
            open(os.path.join(H.TXT, p + '.txt'), 'w', encoding='utf-8').write(t)
            print('OK', p, len(t), flush=True)
            break
        except Exception as e:
            print('FAIL', p, attempt, e, flush=True)
            time.sleep(20)
    time.sleep(10)
print('done', flush=True)
