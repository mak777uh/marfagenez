import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
print('verdict:', d.get('verdict'))
print('controls:', json.dumps(d.get('controls'), ensure_ascii=False)[:2500])
