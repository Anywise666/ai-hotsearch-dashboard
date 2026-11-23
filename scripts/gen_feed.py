#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简报播客 RSS 生成（配置驱动，纯标准库）
- 扫描 audio/YYYY-MM-DD/manifest.json，生成 RSS 2.0 + iTunes
- 每期 enclosure 指向 brief_zh.mp3，pubDate 用配置的北京时间
- 输出 site 根目录 feed.xml
用法: python scripts/gen_feed.py
"""
import os
import re
import json
import html
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import common

CFG = common.load_config()
AUDIO_ROOT = common.audio_root()
FEED_PATH = common.feed_path()
SITE = CFG.get("site_url", "").rstrip("/")
SITE_NAME = CFG.get("site_name", "每日简报")
BRAND = CFG.get("brand_line", SITE_NAME)
SITE_DESC = CFG.get("site_desc", "每天一期简报速览播客。")
AUTHOR = CFG.get("podcast_author", BRAND)
CATEGORY = CFG.get("podcast_category", "Technology")
MAX_EPISODES = int(CFG.get("max_episodes", 60))
PUB_H = int(CFG.get("pub_hour", 8))
PUB_M = int(CFG.get("pub_minute", 30))


def fetch_lead(date):
    try:
        r = common.fetch_report(CFG, date) or {}
        return ((r.get("lead") or {}).get("title") or "")
    except Exception:
        return ""


def pub_date_of(date):
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        dt = d.replace(hour=PUB_H, minute=PUB_M, tzinfo=timezone(timedelta(hours=8)))
        return format_datetime(dt)
    except Exception:
        return format_datetime(datetime.now(timezone.utc))


def esc(s):
    return html.escape(str(s or ""), quote=False)


def cdata(s):
    return "<![CDATA[" + str(s or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def build():
    dates = sorted([d for d in os.listdir(AUDIO_ROOT)
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", d)
                    and os.path.isfile(os.path.join(AUDIO_ROOT, d, "manifest.json"))]) if os.path.isdir(AUDIO_ROOT) else []
    dates = [d for d in dates if d <= datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")]
    dates = dates[-MAX_EPISODES:][::-1]
    print("  可订阅期数:", len(dates))

    items = []
    for date in dates:
        mpath = os.path.join(AUDIO_ROOT, date, "manifest.json")
        try:
            m = json.load(open(mpath, encoding="utf-8"))
        except Exception:
            continue
        brief = m.get("brief")
        items_meta = m.get("items") or {}
        audio_file = brief
        if not audio_file and items_meta:
            audio_file = (items_meta.get("lead") or {}).get("zh")
        if not audio_file:
            continue
        audio_url = SITE + "/audio/" + date + "/" + audio_file
        abs_url = SITE + "/index.html"
        hd = datetime.strptime(date, "%Y-%m-%d")
        title = BRAND + "速览 · " + hd.strftime("%m月%d日")
        lead_title = fetch_lead(date)
        desc = "速览当天要点。"
        if lead_title:
            desc += " 今日头条：" + lead_title
        desc += " 完整简报：" + abs_url
        guid = re.sub(r"[^A-Za-z0-9]", "-", SITE) + "-" + date
        item = """    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{desc}</description>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub}</pubDate>
      <enclosure url="{audio}" length="{length}" type="audio/mpeg" />
      <itunes:duration>90</itunes:duration>
      <itunes:title>{title}</itunes:title>
      <itunes:summary>{desc}</itunes:summary>
      <itunes:episodeType>full</itunes:episodeType>
    </item>""".format(
            title=cdata(title), link=esc(abs_url), desc=cdata(desc), guid=esc(guid),
            pub=pub_date_of(date), audio=esc(audio_url),
            length=os.path.getsize(os.path.join(AUDIO_ROOT, date, audio_file)))
        items.append(item)
        print("    -", date, "| brief:", bool(brief))

    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{name}</title>
    <link>{site}</link>
    <description>{desc}</description>
    <language>zh-CN</language>
    <itunes:author>{author}</itunes:author>
    <itunes:summary>{desc}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="{cat}" />
    <atom:link href="{site}/feed.xml" rel="self" type="application/rss+xml" />
    <ttl>60</ttl>
{items}
  </channel>
</rss>
""".format(name=esc(SITE_NAME), site=esc(SITE), desc=cdata(SITE_DESC),
           author=esc(AUTHOR), cat=esc(CATEGORY), items="\n".join(items))

    with open(FEED_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(rss)
    print("=== feed.xml 已生成:", FEED_PATH, "|", len(items), "期 ===")
    return len(items)


if __name__ == "__main__":
    build()
