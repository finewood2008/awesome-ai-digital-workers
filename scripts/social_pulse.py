#!/usr/bin/env python3
"""
Social Pulse — 监控已收录项目在社媒上的讨论热度
检索 X/Twitter, Reddit, Hacker News, V2EX 上的提及和讨论
"""

import json
import os
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

DATA_DIR = "data"
PROJECTS_PATH = os.path.join(DATA_DIR, "projects.json")
SOCIAL_PATH = os.path.join(DATA_DIR, "social-pulse.json")
ALERTS_PATH = os.path.join(DATA_DIR, "alerts")

CST = timezone(timedelta(hours=8))


def load_json(path: str, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def search_hackernews(query: str, limit: int = 5) -> list:
    """搜索 Hacker News"""
    try:
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={urllib.parse.quote(query)}&tags=story&hitsPerPage={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            results = []
            for hit in data.get("hits", []):
                results.append({
                    "title": hit.get("title", ""),
                    "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "date": hit.get("created_at", "")[:10],
                    "source": "HackerNews",
                })
            return results
    except Exception as e:
        print(f"    ⚠️ HN search failed: {e}")
    return []


def search_reddit(query: str, limit: int = 5) -> list:
    """搜索 Reddit"""
    try:
        url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query)}&sort=new&limit={limit}&t=week"
        req = urllib.request.Request(url, headers={"User-Agent": "AIDWBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            results = []
            for post in data.get("data", {}).get("children", []):
                d = post.get("data", {})
                results.append({
                    "title": d.get("title", ""),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "points": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "subreddit": d.get("subreddit", ""),
                    "date": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "source": "Reddit",
                })
            return results
    except Exception as e:
        print(f"    ⚠️ Reddit search failed: {e}")
    return []


def search_github_discussions(owner: str, repo: str) -> dict:
    """获取 GitHub 仓库的讨论和 issue 活跃度"""
    stats = {"open_issues": 0, "recent_issues": 0, "discussions": False}
    try:
        # 最近 7 天的 issues
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/issues",
             "--method", "GET", "-f", f"since={since}", "-f", "per_page=30", "-f", "state=all"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            issues = json.loads(result.stdout)
            stats["recent_issues"] = len(issues) if isinstance(issues, list) else 0

        # 检查是否有 Discussions
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".has_discussions_enabled"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            stats["discussions"] = result.stdout.strip() == "true"
    except Exception:
        pass
    return stats


def main():
    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    print(f"💬 Social Pulse — {today_str}")

    projects = load_json(PROJECTS_PATH, [])
    if not projects:
        print("  ⚠️ No projects to monitor")
        return

    social_data = load_json(SOCIAL_PATH, {})
    alerts = []

    # 通用关键词搜索（大范围）
    general_queries = [
        "openclaw agent",
        "hermes agent AI",
        "AI digital worker open source",
        "AI agent framework 2026",
    ]

    print("  🌐 General social search...")
    general_mentions = []
    for query in general_queries:
        print(f"    🔎 HN: {query}")
        general_mentions.extend(search_hackernews(query, 3))
        print(f"    🔎 Reddit: {query}")
        general_mentions.extend(search_reddit(query, 3))

    # 每个已收录项目单独搜索
    print(f"\n  📦 Monitoring {len(projects)} projects...")
    for p in projects:
        name = p.get("name", "")
        url = p.get("url", "")
        owner = p.get("owner", "")

        parts = url.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        repo_owner, repo_name = parts[-2], parts[-1]

        print(f"  🔍 {name}...")

        mentions = []

        # HN 搜索
        hn_results = search_hackernews(name, 3)
        mentions.extend(hn_results)

        # Reddit 搜索
        reddit_results = search_reddit(f"{name} {repo_owner}", 3)
        mentions.extend(reddit_results)

        # GitHub discussions/issues 活跃度
        gh_stats = search_github_discussions(repo_owner, repo_name)

        # 计算社媒热度分
        total_points = sum(m.get("points", 0) for m in mentions)
        total_comments = sum(m.get("comments", 0) for m in mentions)
        mention_count = len(mentions)

        pulse = {
            "date": today_str,
            "mentions": mention_count,
            "total_points": total_points,
            "total_comments": total_comments,
            "recent_issues_7d": gh_stats["recent_issues"],
            "has_discussions": gh_stats["discussions"],
            "top_mentions": sorted(mentions, key=lambda x: x.get("points", 0), reverse=True)[:5],
        }

        # 更新社媒数据
        if url not in social_data:
            social_data[url] = []
        social_data[url].append(pulse)
        # 只保留最近 30 天数据
        social_data[url] = social_data[url][-30:]

        # 热度预警
        if total_points > 100 or mention_count >= 5:
            alerts.append({
                "name": name,
                "url": url,
                "mentions": mention_count,
                "total_points": total_points,
                "reason": f"社媒热度高：{mention_count}条提及，{total_points}总分",
            })

        # 更新项目数据
        p["social_pulse"] = {
            "mentions_today": mention_count,
            "points_today": total_points,
            "last_checked": today_str,
        }

        status = "🔥" if total_points > 50 else "💬" if mention_count > 0 else "🔇"
        print(f"    {status} 提及:{mention_count} 总分:{total_points} Issues(7d):{gh_stats['recent_issues']}")

    # 保存
    save_json(PROJECTS_PATH, projects)
    save_json(SOCIAL_PATH, social_data)

    if alerts:
        os.makedirs(ALERTS_PATH, exist_ok=True)
        save_json(os.path.join(ALERTS_PATH, f"{today_str}-social.json"), alerts)
        print(f"\n🚨 {len(alerts)} 个项目社媒热度异常:")
        for a in alerts:
            print(f"  🔥 {a['name']} — {a['reason']}")

    if general_mentions:
        save_json(os.path.join(DATA_DIR, "general-mentions.json"), general_mentions)
        print(f"\n📡 通用关键词发现 {len(general_mentions)} 条社媒提及")


if __name__ == "__main__":
    main()
