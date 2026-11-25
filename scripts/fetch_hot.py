#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取多平台实时热搜，保存原始数据到 raw/。
带重试、延时与多源回退，规避热搜 API 的短时限流（60s 返回 429/1027）。

数据源（按顺序回退）：
  1) 60s API      https://60s.viki.moe/v2/<platform>
  2) DailyHotApi  https://api-hot.imsyy.top/<platform>

字段归一化：不同源的 hot/hot_value、url/link、desc/detail 统一为
  {title, hot_value, link, desc}，与 build_data.py 的数据契约一致。
某平台所有源都失败时，保留上一轮 raw 文件，绝不写空覆盖。
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
os.makedirs(RAW, exist_ok=True)

PLATFORMS = ["weibo", "zhihu", "douyin", "bili", "toutiao", "baidu"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; hot-aggregator/1.0)",
      "Accept": "application/json"}

# 每个源的平台端点映射。url 模板中 {p} 替换为映射后的端点名。
SOURCES = [
    {
        "name": "60s",
        "endpoint": {
            "weibo": "weibo", "zhihu": "zhihu", "douyin": "douyin",
            "bili": "bili", "toutiao": "toutiao", "baidu": "baidu/hot",
        },
        "url": "https://60s.viki.moe/v2/{p}",
    },
    {
        "name": "dailyhot",
        "endpoint": {
            "weibo": "weibo", "zhihu": "zhihu", "douyin": "douyin",
            "bili": "bilibili", "toutiao": "toutiao", "baidu": "baidu",
        },
        "url": "https://api-hot.imsyy.top/{p}",
    },
]


def normalize(data):
    """把不同源条目统一为 {title, hot_value, link, desc}。"""
    out = []
    for r in data or []:
        title = str(r.get("title") or "").strip()
        if not title:
            continue
        hot = (r.get("hot_value") or r.get("hot") or r.get("score")
               or r.get("hot_value_desc") or "0")
        link = r.get("link") or r.get("url") or r.get("mobileUrl") or ""
        desc = r.get("desc") or r.get("detail") or r.get("description") or ""
        out.append({"title": title, "hot_value": hot, "link": link, "desc": desc})
    return out


def fetch_one(url, retries=3):
    """单端点带重试抓取，成功返回 data 数组，失败返回 None。"""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
            if data.get("code") == 200 and isinstance(data.get("data"), list):
                return data["data"]
            print("    [retry %d] %s -> code=%s %s" % (
                i + 1, url, data.get("code"), str(data.get("message", ""))[:40]))
        except Exception as e:
            print("    [retry %d] %s -> %s" % (i + 1, url, repr(e)[:80]))
        time.sleep(2 * (i + 1))
    return None


def fetch_platform(name):
    """按源顺序回退抓取某平台，返回归一化条目或 None。"""
    for src in SOURCES:
        ep = src["endpoint"].get(name)
        if not ep:
            continue
        url = src["url"].format(p=ep)
        print("  [%s] %s" % (src["name"], url))
        data = fetch_one(url)
        if data:
            rows = normalize(data)
            print("    [ok] %-8s via %s: %d 条" % (name, src["name"], len(rows)))
            return rows
    return None


def main():
    print("=== 抓取多平台实时热搜（60s → DailyHotApi 回退）===")
    summary = {}
    for p in PLATFORMS:
        rows = fetch_platform(p)
        if rows:
            payload = {
                "platform": p,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.gmtime(time.time() + 8 * 3600)),
                "data": rows,
            }
            with open(os.path.join(RAW, p + ".json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            summary[p] = len(rows)
        else:
            old = os.path.join(RAW, p + ".json")
            if os.path.exists(old):
                try:
                    n = len(json.load(open(old, encoding="utf-8")).get("data", []))
                    summary[p] = "keep:%d" % n
                    print("    [keep] %-8s 所有源失败，保留上轮 %d 条" % (p, n))
                except Exception:
                    summary[p] = 0
            else:
                summary[p] = 0
        time.sleep(1.5)  # 平台间延时，避免限流
    print("=== 汇总:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
