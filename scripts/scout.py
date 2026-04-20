#!/usr/bin/env python3
"""
Daily AI Digital Workers Scout
每日自动检索 GitHub 上与 AI Agent / 数字员工 / Hermes / OpenClaw 相关的开源项目
"""

import json
import os
import subprocess
import re
from datetime import datetime, timezone, timedelta

# ---------- 配置 ----------
SEARCH_QUERIES = [
    "hermes agent",
    "openclaw",
    "AI digital worker",
    "AI agent framework",
    "autonomous AI agent",
    "AI employee",
    "digital worker automation",
    "AI agent orchestration",
    "hermes openclaw skill",
    "AI agent self-hosted",
]

# 分类关键词映射
CATEGORIES = {
    "Hermes / OpenClaw 生态": [
        "hermes", "openclaw", "claw", "clawhub",
    ],
    "Agent 框架": [
        "agent framework", "agent platform", "agent sdk",
        "multi-agent", "agent orchestration", "agentic",
    ],
    "数字员工 / RPA + AI": [
        "digital worker", "digital employee", "AI employee",
        "AI worker", "RPA", "数字员工", "AI助理", "AI assistant",
    ],
    "AI 工作流 / 自动化": [
        "workflow", "automation", "pipeline", "task runner",
        "orchestrat",
    ],
    "多模态 Agent": [
        "multimodal", "vision", "voice", "多模态",
    ],
}

README_PATH = "README.md"
DATA_PATH = "data/projects.json"
DAILY_DIR = "data/daily"

# ---------- 工具函数 ----------

def gh_search(query: str, limit: int = 20) -> list:
    """使用 gh CLI 搜索 GitHub 仓库"""
    try:
        result = subprocess.run(
            [
                "gh", "search", "repos", query,
                "--limit", str(limit),
                "--sort", "stars",
                "--json", "name,owner,url,description,stargazersCount,updatedAt,language,topics",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        print(f"  ⚠️ Search failed for '{query}': {e}")
    return []


def categorize(repo: dict) -> str:
    """根据项目描述和名称判断分类"""
    text = f"{repo.get('name', '')} {repo.get('description', '')}".lower()
    topics = " ".join(repo.get("topics", []) or []).lower()
    combined = f"{text} {topics}"

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in combined:
                return category
    return "Agent 框架"  # 默认分类


def load_existing_projects() -> dict:
    """加载已收录的项目（以 URL 为 key）"""
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {p["url"]: p for p in data}
    return {}


def save_projects(projects: dict):
    """保存项目数据"""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(list(projects.values()), f, ensure_ascii=False, indent=2)


def save_daily_report(new_projects: list, date_str: str):
    """保存每日新发现"""
    os.makedirs(DAILY_DIR, exist_ok=True)
    path = os.path.join(DAILY_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_projects, f, ensure_ascii=False, indent=2)


def generate_readme(projects: dict):
    """生成 README.md（含增长数据和质量评分）"""
    proj_list = list(projects.values())

    # 按分类整理
    categorized = {}
    for p in proj_list:
        cat = p.get("category", "Agent 框架")
        categorized.setdefault(cat, []).append(p)

    # 每个分类按质量评分降序，其次按 stars
    for cat in categorized:
        categorized[cat].sort(
            key=lambda x: (x.get("quality_score", 0), x.get("stars", 0)),
            reverse=True,
        )

    # 分类图标和顺序
    icons = {
        "Hermes / OpenClaw 生态": "🦊",
        "Agent 框架": "🏗️",
        "数字员工 / RPA + AI": "🤖",
        "AI 工作流 / 自动化": "⚡",
        "多模态 Agent": "🎯",
    }
    order = [
        "Hermes / OpenClaw 生态",
        "Agent 框架",
        "数字员工 / RPA + AI",
        "AI 工作流 / 自动化",
        "多模态 Agent",
    ]

    now_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')

    lines = [
        "# 🤖 Awesome AI Digital Workers\n",
        "> AI Agent / 数字员工相关优秀开源项目收集整理",
        "> ",
        "> 每日由 GitHub Actions 自动检索 + 增长监控 + 社媒热度分析",
        f"> ",
        f"> 📊 共收录 **{len(proj_list)}** 个项目 | 🕐 最后更新: {now_str} CST\n",
        "---\n",
    ]

    # 🏆 增长排行榜（如果有增长数据）
    ranked = [p for p in proj_list if p.get("quality_score")]
    if ranked:
        ranked.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        lines.append("## 🏆 质量排行 Top 10\n")
        lines.append("| # | 项目 | 评分 | ⭐ Stars | 📈 周增 | 🔨 周Commit | 📄 License | 趋势 |")
        lines.append("|---|------|------|---------|--------|------------|-----------|------|")
        for i, p in enumerate(ranked[:10], 1):
            g = p.get("growth", {})
            lines.append(
                f"| {i} | [{p['name']}]({p['url']}) | {p.get('quality_score', 0)} | "
                f"{p.get('stars', 0):,} | +{g.get('weekly', 0)} | "
                f"{p.get('commits_7d', '-')} | {p.get('license', '?')} | "
                f"{g.get('trend', '?')} |"
            )
        lines.append("")

    # 🔥 高增长预警
    fast_growing = [p for p in proj_list if p.get("growth", {}).get("weekly", 0) > 50]
    if fast_growing:
        fast_growing.sort(key=lambda x: x["growth"]["weekly"], reverse=True)
        lines.append("## 🔥 高增长项目\n")
        for p in fast_growing[:5]:
            g = p["growth"]
            lines.append(
                f"- **[{p['name']}]({p['url']})** — "
                f"周增 +{g['weekly']} ⭐ (日均 +{g['daily']}) "
                f"{g.get('trend', '')}"
            )
        lines.append("")

    lines.append("---\n")

    # 分类列表
    for cat in order:
        repos = categorized.get(cat, [])
        if not repos:
            continue
        icon = icons.get(cat, "📦")
        lines.append(f"## {icon} {cat}\n")
        lines.append("| 项目 | ⭐ Stars | 📈 周增 | 评分 | 语言 | License | 简介 | 发现日期 |")
        lines.append("|------|---------|--------|------|------|---------|------|----------|")
        for r in repos:
            g = r.get("growth", {})
            weekly = f"+{g['weekly']}" if g.get("weekly") else "-"
            score = r.get("quality_score", "-")
            desc = (r.get("description", "") or "")[:100]
            lines.append(
                f"| [{r['name']}]({r['url']}) | {r.get('stars', 0):,} | {weekly} | "
                f"{score} | {r.get('language', '-') or '-'} | "
                f"{r.get('license', '?')} | {desc} | {r.get('discovered', '')} |"
            )
        lines.append("")

    # 更新日志
    if os.path.exists(DAILY_DIR):
        lines.append("---\n")
        lines.append("## 📝 最近更新\n")
        daily_files = sorted(
            [f for f in os.listdir(DAILY_DIR) if f.endswith(".json")],
            reverse=True,
        )[:7]
        for df in daily_files:
            date = df.replace(".json", "")
            with open(os.path.join(DAILY_DIR, df), "r", encoding="utf-8") as f:
                day_projects = json.load(f)
            if day_projects:
                lines.append(f"### {date}")
                for p in day_projects:
                    lines.append(
                        f"- [{p['name']}]({p['url']}) ⭐{p.get('stars', 0):,} — "
                        f"{(p.get('description', '') or '')[:80]}"
                    )
                lines.append("")

    lines.append("---\n")
    lines.append("*由 GitHub Actions 每日自动检索 + 增长监控 + 社媒热度分析 🌙*\n")

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------- 主流程 ----------

def main():
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    print(f"🔍 Daily AI Project Scout — {today}")

    existing = load_existing_projects()
    print(f"📦 已收录项目: {len(existing)}")

    all_results = {}
    for query in SEARCH_QUERIES:
        print(f"  🔎 Searching: {query}")
        repos = gh_search(query)
        for r in repos:
            url = r.get("url", "")
            if url and url not in all_results:
                all_results[url] = r

    print(f"  📥 本次检索去重后: {len(all_results)} 个候选")

    # 筛选：stars >= 50 或与 hermes/openclaw 直接相关
    new_projects = []
    for url, r in all_results.items():
        if url in existing:
            # 更新已有项目的 stars
            existing[url]["stars"] = r.get("stargazersCount", 0)
            continue

        stars = r.get("stargazersCount", 0)
        desc = (r.get("description", "") or "").lower()
        name = (r.get("name", "") or "").lower()

        # 与 hermes/openclaw 相关的不设 star 门槛
        is_ecosystem = any(kw in f"{name} {desc}" for kw in ["hermes", "openclaw", "claw"])

        if stars >= 50 or is_ecosystem:
            project = {
                "name": r.get("name", ""),
                "url": url,
                "owner": r.get("owner", {}).get("login", ""),
                "description": r.get("description", ""),
                "stars": stars,
                "language": r.get("language", ""),
                "topics": r.get("topics", []),
                "discovered": today,
                "category": categorize(r),
            }
            new_projects.append(project)
            existing[url] = project

    print(f"  🆕 新发现: {len(new_projects)} 个项目")

    # 保存
    save_projects(existing)
    save_daily_report(new_projects, today)
    generate_readme(existing)

    # 输出摘要
    if new_projects:
        print("\n✨ 今日新发现:")
        for p in sorted(new_projects, key=lambda x: x["stars"], reverse=True)[:10]:
            print(f"  ⭐ {p['stars']:>6,} | {p['name']:<35} | {(p['description'] or '')[:60]}")
    else:
        print("\n📭 今天没有新项目")


if __name__ == "__main__":
    main()
