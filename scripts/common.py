#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简报播客站的公共模块：配置加载 + 数据源适配。

数据契约（aihot 兼容结构）见 references/data-contract.md。
支持两种数据源模式：
  - aihot：从 api_base 拉取 /dailies/<date> 与 /items
  - local：读取 <local_data_dir>/<date>.json（内容为 report 对象或含 report 字段）
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(ROOT, "site.config.json")
UA = {"User-Agent": "ai-brief-podcast/1.0"}


def load_config():
    if not os.path.isfile(CONFIG_PATH):
        raise SystemExit(
            "缺少 site.config.json —— 请从 assets/site.config.example.json 复制到站点根目录并填写"
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def fetch_report(config, date):
    """返回符合数据契约的 report dict，无数据返回 None。"""
    mode = config.get("data_mode", "aihot")
    if mode == "aihot":
        base = config["api_base"].rstrip("/")
        try:
            j = _get_json(base + "/dailies/" + date)
        except Exception as e:
            print("  [fetch fail]", date, repr(e)[:120])
            return None
        return (j or {}).get("report")
    if mode == "local":
        p = os.path.join(ROOT, config.get("local_data_dir", "data"), date + ".json")
        if not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("report", d)
    raise SystemExit("未知 data_mode: " + str(mode))


def fetch_en_map(config):
    """返回 {item_id: originalTitle}，local 模式返回空字典（英文标题走数据契约内联字段）。"""
    if config.get("data_mode") != "aihot":
        return {}
    try:
        j = _get_json(config["api_base"].rstrip("/") + "/items?limit=100")
    except Exception:
        return {}
    import re
    out = {}
    for it in (j or {}).get("items", []):
        m = re.search(r"/items/([a-z0-9]+)", str((it.get("links") or {}).get("aihot")), re.I)
        aid = m.group(1) if m else it.get("id")
        if aid and it.get("originalTitle"):
            out[aid] = it["originalTitle"]
    return out


def audio_root():
    return os.path.join(ROOT, "audio")


def feed_path():
    return os.path.join(ROOT, "feed.xml")


def today_ymd():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
