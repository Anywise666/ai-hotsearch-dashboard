#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 60s API 多平台实时热搜，保存原始数据到 raw/。
带重试与延时，规避 60s API 的短时限流（error code 1015）。
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
os.makedirs(RAW, exist_ok=True)

API = "https://60s.viki.moe/v2/{}"
PLATFORMS = ["weibo", "zhihu", "douyin", "bili", "toutiao", "baidu"]
# 部分平台路径与名称不同（百度实际是 /v2/baidu/hot）
ENDPOINTS = {"baidu": "baidu/hot"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; hot-aggregator/1.0)"}


def fetch(name, retries=4):
    url = API.format(ENDPOINTS.get(name, name))
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
            if data.get("code") == 200 and isinstance(data.get("data"), list):
                print("  [ok] %-8s %d 条" % (name, len(data["data"])))
                return data["data"]
            print("  [retry %d] %s -> %s" % (i + 1, name, str(data.get("code")) + ":" + str(data.get("message", ""))[:40]))
        except Exception as e:
            print("  [retry %d] %s -> %s" % (i + 1, name, repr(e)[:80]))
        time.sleep(3 * (i + 1))
    return None


def main():
    print("=== 抓取 60s API 实时热搜 ===")
    summary = {}
    for p in PLATFORMS:
        rows = fetch(p)
        summary[p] = len(rows) if rows else 0
        if rows:
            with open(os.path.join(RAW, p + ".json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump({"platform": p, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.gmtime(time.time() + 8 * 3600)), "data": rows},
                          f, ensure_ascii=False, indent=2)
        time.sleep(2)  # 平台间延时，避免限流
    print("=== 汇总:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
