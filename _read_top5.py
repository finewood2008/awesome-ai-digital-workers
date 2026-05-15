import json
with open('data/projects.json', encoding='utf-8') as f:
    data = json.load(f)
top5 = sorted(data, key=lambda x: x.get('quality', x.get('score', 0)), reverse=True)[:5]
for p in top5:
    nm = p.get('name', '?')
    sc = p.get('quality', p.get('score', '?'))
    st = p.get('stars', '?')
    print(f"{nm:35s} score={sc} stars={st}")
