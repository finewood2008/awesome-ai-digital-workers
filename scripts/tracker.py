#!/usr/bin/env python3
"""
Star Tracker — 监控已收录项目的 star 增长情况
每天记录 star 数、计算增速，识别高增长项目
"""

import json
import os
import subprocess
from datetime import datetime, timezone, timedelta

DATA_DIR = "data"
PROJECTS_PATH = os.path.join(DATA_DIR, "projects.json")
HISTORY_PATH = os.path.join(DATA_DIR, "star-history.json")
ALERTS_PATH = os.path.join(DATA_DIR, "alerts")

CST = timezone(timedelta(hours=8))


def gh_api(endpoint: str) -> dict:
    """调用 GitHub API"""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint, "--cache", "0s"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"  ⚠️ API failed for {endpoint}: {e}")
    return {}


def load_json(path: str, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_repo_details(owner: str, repo: str) -> dict:
    """获取仓库详细信息"""
    data = gh_api(f"repos/{owner}/{repo}")
    if not data:
        return {}

    # 获取最近 commit 活跃度
    commits_7d = []
    commits_30d = []
    try:
        since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits",
             "--method", "GET", "-f", f"since={since_7d}", "-f", "per_page=100"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            commits_7d = json.loads(result.stdout)

        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits",
             "--method", "GET", "-f", f"since={since_30d}", "-f", "per_page=100"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            commits_30d = json.loads(result.stdout)
    except Exception:
        pass

    return {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "license": (data.get("license") or {}).get("spdx_id", "Unknown"),
        "language": data.get("language", ""),
        "pushed_at": data.get("pushed_at", ""),
        "created_at": data.get("created_at", ""),
        "archived": data.get("archived", False),
        "commits_7d": len(commits_7d) if isinstance(commits_7d, list) else 0,
        "commits_30d": len(commits_30d) if isinstance(commits_30d, list) else 0,
        "topics": data.get("topics", []),
    }


def calculate_growth(history: list) -> dict:
    """计算增长指标"""
    if len(history) < 2:
        return {"daily": 0, "weekly": 0, "monthly": 0, "trend": "new"}

    latest = history[-1]["stars"]
    yesterday = history[-2]["stars"] if len(history) >= 2 else latest

    # 找 7 天前和 30 天前的记录
    week_ago = None
    month_ago = None
    today = datetime.fromisoformat(history[-1]["date"])

    for h in reversed(history):
        h_date = datetime.fromisoformat(h["date"])
        days_diff = (today - h_date).days
        if days_diff >= 7 and week_ago is None:
            week_ago = h["stars"]
        if days_diff >= 30 and month_ago is None:
            month_ago = h["stars"]
            break

    daily = latest - yesterday
    weekly = (latest - week_ago) if week_ago is not None else daily * 7
    monthly = (latest - month_ago) if month_ago is not None else weekly * 4

    # 趋势判断
    if daily > 100 or weekly > 500:
        trend = "🚀 explosive"
    elif daily > 20 or weekly > 100:
        trend = "📈 fast"
    elif daily > 5 or weekly > 30:
        trend = "📊 steady"
    elif daily >= 0:
        trend = "➡️ stable"
    else:
        trend = "📉 declining"

    return {
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "trend": trend,
    }


def quality_score(details: dict, growth: dict) -> int:
    """综合质量评分 (0-100)"""
    score = 0

    # Star 基数 (0-20)
    stars = details.get("stars", 0)
    if stars >= 10000: score += 20
    elif stars >= 5000: score += 16
    elif stars >= 1000: score += 12
    elif stars >= 500: score += 8
    elif stars >= 100: score += 4

    # Star 增速 (0-25)
    weekly = growth.get("weekly", 0)
    if weekly >= 500: score += 25
    elif weekly >= 100: score += 20
    elif weekly >= 50: score += 15
    elif weekly >= 10: score += 10
    elif weekly >= 3: score += 5

    # Commit 活跃度 (0-20)
    c7d = details.get("commits_7d", 0)
    c30d = details.get("commits_30d", 0)
    if c7d >= 20: score += 20
    elif c7d >= 10: score += 15
    elif c7d >= 5: score += 10
    elif c30d >= 10: score += 5

    # License (0-15)
    lic = details.get("license", "Unknown")
    if lic in ("MIT", "Apache-2.0"): score += 15
    elif lic in ("BSD-2-Clause", "BSD-3-Clause", "ISC"): score += 12
    elif lic in ("GPL-3.0", "LGPL-3.0", "MPL-2.0"): score += 8
    elif lic != "Unknown": score += 5

    # 项目健康度 (0-10)
    if not details.get("archived", False): score += 3
    if details.get("forks", 0) >= 100: score += 3
    pushed = details.get("pushed_at", "")
    if pushed:
        try:
            last_push = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last_push).days
            if days_since <= 7: score += 4
            elif days_since <= 30: score += 2
        except Exception:
            pass

    # 生态相关性 (0-10)
    topics = " ".join(details.get("topics", []))
    eco_keywords = ["hermes", "openclaw", "claw", "agent", "mcp", "skills"]
    eco_count = sum(1 for kw in eco_keywords if kw in topics.lower())
    score += min(eco_count * 3, 10)

    return min(score, 100)


def main():
    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    print(f"📊 Star Tracker — {today_str}")

    projects = load_json(PROJECTS_PATH, [])
    if not projects:
        print("  ⚠️ No projects to track")
        return

    history = load_json(HISTORY_PATH, {})
    alerts = []

    print(f"  📦 Tracking {len(projects)} projects...")

    for p in projects:
        url = p.get("url", "")
        name = p.get("name", "")

        # 从 URL 提取 owner/repo
        parts = url.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        owner, repo = parts[-2], parts[-1]

        print(f"  🔍 {owner}/{repo}...", end=" ")

        details = get_repo_details(owner, repo)
        if not details:
            print("❌ API failed")
            continue

        # 更新 star history
        if url not in history:
            history[url] = []

        # 避免同一天重复记录
        today_records = [h for h in history[url] if h["date"] == today_str]
        if not today_records:
            history[url].append({
                "date": today_str,
                "stars": details["stars"],
                "forks": details["forks"],
                "commits_7d": details["commits_7d"],
            })

        # 计算增长
        growth = calculate_growth(history[url])
        score = quality_score(details, growth)

        # 更新项目数据
        p["stars"] = details["stars"]
        p["license"] = details["license"]
        p["language"] = details["language"] or p.get("language", "")
        p["quality_score"] = score
        p["growth"] = growth
        p["commits_7d"] = details["commits_7d"]
        p["commits_30d"] = details["commits_30d"]
        p["last_tracked"] = today_str

        trend_icon = growth["trend"].split(" ")[0]
        print(f"⭐{details['stars']:,} {trend_icon} (日+{growth['daily']}, 周+{growth['weekly']}) 分数:{score}")

        # 高增长预警
        if growth["daily"] > 50 or growth["weekly"] > 200:
            alerts.append({
                "name": name,
                "url": url,
                "stars": details["stars"],
                "growth": growth,
                "score": score,
                "reason": f"星星增速异常：日+{growth['daily']}，周+{growth['weekly']}",
            })

    # 保存
    save_json(PROJECTS_PATH, projects)
    save_json(HISTORY_PATH, history)

    if alerts:
        os.makedirs(ALERTS_PATH, exist_ok=True)
        save_json(os.path.join(ALERTS_PATH, f"{today_str}-growth.json"), alerts)
        print(f"\n🚨 {len(alerts)} 个项目增长异常:")
        for a in alerts:
            print(f"  🔥 {a['name']} — {a['reason']}")

    # 生成增长排行
    ranked = sorted(
        [p for p in projects if p.get("quality_score")],
        key=lambda x: x.get("quality_score", 0),
        reverse=True,
    )
    if ranked:
        print(f"\n🏆 质量评分 Top 10:")
        for i, p in enumerate(ranked[:10], 1):
            g = p.get("growth", {})
            print(f"  {i}. [{p.get('quality_score', 0):>3}分] {p['name']:<30} ⭐{p['stars']:>6,} 周+{g.get('weekly', 0)}")


if __name__ == "__main__":
    main()
