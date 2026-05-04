import json, datetime

PROJECTS_FILE = r'C:\Users\Administrator\awesome-ai-digital-workers\data\projects.json'
STAR_HISTORY_FILE = r'C:\Users\Administrator\awesome-ai-digital-workers\data\star-history.json'
DAILY_DIR = r'C:\Users\Administrator\awesome-ai-digital-workers\data\daily'
ALERTS_DIR = r'C:\Users\Administrator\awesome-ai-digital-workers\data\alerts'

today = '2026-05-04'

# Load projects
with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
    projects = json.load(f)

names = [p['name'] for p in projects]
print(f"graphify in projects: {'graphify' in names}")
print(f"Total projects: {len(projects)}")

# Add graphify if not present
if 'graphify' not in names:
    new_project = {
        "name": "graphify",
        "url": "https://github.com/safishamsi/graphify",
        "owner": "safishamsi",
        "description": "AI coding assistant skill (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, and more). Turn any folder into a queryable knowledge graph.",
        "stars": 41901,
        "language": "Python",
        "topics": ["knowledge-graph", "ai-coding", "codex", "openclaw", "claude-code", "opencode"],
        "discovered": today,
        "category": "AI 工作流 / 自动化",
        "license": "MIT",
        "quality_score": 85,
        "growth": {
            "daily": 0,
            "weekly": 0,
            "monthly": 0,
            "trend": "🆕 new"
        },
        "commits_7d": 0,
        "commits_30d": 0,
        "last_tracked": today,
        "social_pulse": {
            "mentions_today": 0,
            "points_today": 0,
            "last_checked": today
        }
    }
    projects.append(new_project)
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
    print(f"OK: Added graphify ({new_project['stars']} stars)")
else:
    print("graphify already in projects.json")

# Add to star-history
with open(STAR_HISTORY_FILE, 'r', encoding='utf-8') as f:
    star_hist = json.load(f)

graphify_url = "https://github.com/safishamsi/graphify"
if graphify_url not in star_hist:
    star_hist[graphify_url] = [{
        "date": today,
        "stars": 41901,
        "forks": 0,
        "commits_7d": 0
    }]
    with open(STAR_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(star_hist, f, ensure_ascii=False, indent=2)
    print("OK: Added to star-history.json")
else:
    print("Already in star-history.json")

# Create today's daily file
daily_file = rf'{DAILY_DIR}\{today}.json'
daily_data = [{
    "name": "graphify",
    "url": graphify_url,
    "stars": 41901,
    "category": "AI 工作流 / 自动化",
    "reason": "🔍 新发现：AI coding assistant 知识图谱工具，41.9k ★，与 OpenClaw/Codex 生态兼容"
}]
with open(daily_file, 'w', encoding='utf-8') as f:
    json.dump(daily_data, f, ensure_ascii=False, indent=2)
print(f"OK: Created {today}.json daily file")
