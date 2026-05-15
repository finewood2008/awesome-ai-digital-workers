import json, os

import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\Administrator\awesome-ai-digital-workers\data\projects.json', 'r', encoding='utf-8') as f:
    projects = json.load(f)

print("=== TOP 5 QUALITY SCORE ===")
top5 = sorted(projects, key=lambda p: p.get('quality_score', 0), reverse=True)[:5]
for p in top5:
    g = p.get('growth', {})
    print(f'{p["name"]:30s} score={p.get("quality_score",0):3d}  stars={p.get("stars",0):>7,d}  trend={g.get("trend","")}')

# Last tracked date
dates = set()
for p in projects:
    lt = p.get('last_tracked', '')
    if lt: dates.add(lt)
print(f'\nLast tracked dates: {sorted(dates)[-3:]}')

# Hermes/OpenClaw ecosystem
hermes_oc = [p for p in projects if 'hermes' in p['name'].lower() or 'openclaw' in p['name'].lower()]
print(f'\nHermes/OpenClaw ecosystem projects tracked: {len(hermes_oc)}')
for p in sorted(hermes_oc, key=lambda x: x.get('stars',0), reverse=True)[:8]:
    print(f'  {p["name"]:35s} stars={p.get("stars",0):>7,d}  score={p.get("quality_score",0):3d}')

# Check total tracked
print(f'\nTotal tracked projects: {len(projects)}')
categories = {}
for p in projects:
    cat = p.get('category', 'Uncategorized')
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f'  {cat}: {count}')
