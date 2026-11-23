#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简报双语播客音频生成器（配置驱动）
- 从 common.fetch_report 读取当天 report（数据契约见 references/data-contract.md）
- 为头条 + 每条卡片生成"中文(标题+摘要) → 英文(原题)"串读 mp3
- 生成 90 秒速览 brief_zh.mp3
- 写入 audio/YYYY-MM-DD/ + manifest.json，清理过期目录
依赖: pip install edge-tts
用法: python scripts/gen_audio.py [YYYY-MM-DD]
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import common

CFG = common.load_config()
AUDIO_ROOT = common.audio_root()
VOICE_ZH = CFG.get("voice_zh", "zh-CN-XiaoxiaoNeural")
VOICE_EN = CFG.get("voice_en", "en-US-JennyNeural")
KEEP_DAYS = int(CFG.get("keep_days", 30))
BRAND = CFG.get("brand_line", CFG.get("site_name", "今日简报"))


def clean_text(s):
    s = re.sub(r"[\u200b-\u200d\ufeff]", "", s or "")
    return re.sub(r"\s+", " ", s.replace("\n", " ").replace("\r", " ").replace("\t", " ")).strip()


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)[:40]


def item_id(url):
    if not url:
        return ""
    m = re.search(r"/items/([a-z0-9]+)", str(url), re.I)
    return m.group(1) if m else ""


async def synth(text, voice, out_path, retries=3):
    import edge_tts
    text = clean_text(text)
    if not text:
        return False
    for i in range(retries):
        try:
            comm = edge_tts.Communicate(text, voice, rate="+0%")
            await comm.save(out_path)
            if os.path.getsize(out_path) > 500:
                return True
        except Exception as e:
            print("    [tts retry %d] %s" % (i + 1, repr(e)[:100]))
            await asyncio.sleep(2 * (i + 1))
    return False


def build_tts_items(report, en_map):
    """构造待生成条目: {key, title, zh_text, en_text}"""
    items = []
    lead = report.get("lead") or {}
    lead_title = lead.get("title") or ""
    norm = lambda s: (s or "").replace("\u3000", "").replace(" ", "").lower()
    target = norm(lead_title)
    pools = []
    for s in report.get("sections", []):
        pools.extend(s.get("items", []))
    pools.extend(report.get("flashes", []))
    pools.extend(report.get("highlights", []))
    lead_url = ""
    for p in pools:
        if norm(p.get("title")) == target:
            links = p.get("links") or {}
            lead_url = links.get("original") or links.get("aihot") or ""
            break
    if lead_title:
        lid = item_id(lead_url) or "lead"
        items.append({
            "key": "lead",
            "title": lead_title,
            "zh_text": "今日头条。" + lead_title + "。" + (lead.get("leadParagraph") or lead.get("summary") or ""),
            "en_text": en_map.get(lid, lead.get("originalTitle", "")),
        })
    for sec in report.get("sections", []):
        for it in sec.get("items", []):
            links = it.get("links") or {}
            aid = item_id(links.get("aihot")) or it.get("id", "")
            key = safe_name(aid) if aid else ("t_" + safe_name((it.get("title") or "")[:20]))
            en = it.get("originalTitle") or en_map.get(aid, "")
            items.append({
                "key": key,
                "title": it.get("title") or "",
                "zh_text": (it.get("title") or "") + "。" + (it.get("summary") or ""),
                "en_text": en,
            })
    return items


def cut_cn(s, n):
    s = clean_text(s)
    return s if len(s) <= n else s[:n].rstrip("，。、；： ") + "…"


def build_brief_script(report, date):
    """90 秒速览中文串读稿：开场 + 头条 + 各板块首条 + 收尾（约 400 字）。"""
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        dcn = "%d年%d月%d日" % (dt.year, dt.month, dt.day)
    except Exception:
        dcn = date
    parts = ["欢迎收听今日" + BRAND + "速览，%s。" % dcn]
    lead = report.get("lead") or {}
    sections = [s for s in (report.get("sections") or []) if s.get("items")]
    parts.append("以下是今天最值得关注的 %d 条资讯。" % (1 + len(sections)))
    lt = cut_cn(lead.get("title") or "", 34)
    lp = cut_cn(lead.get("leadParagraph") or lead.get("summary") or "", 48)
    if lt:
        parts.append("今日头条。" + lt + ("。" + lp if lp else ""))
    for sec in sections:
        it = (sec.get("items") or [{}])[0]
        label = clean_text(sec.get("label") or sec.get("title") or sec.get("name") or "")
        t = cut_cn(it.get("title") or "", 32)
        sm = cut_cn(it.get("summary") or "", 26)
        seg = (label + "。" if label else "") + t
        if sm:
            seg += "。" + sm
        parts.append(seg)
    outro = "以上就是今天的" + BRAND + "速览，更多详细内容请查看简报页面。感谢收听。"
    body = "".join(parts)
    if len(body) + len(outro) > 430:
        body = body[:430 - len(outro)]
        p = body.rfind("。")
        if p > 180:
            body = body[:p + 1]
        body = body.rstrip("，。、；： ")
    return body + "。" + outro if body else outro


def cleanup_old():
    try:
        dirs = sorted([d for d in os.listdir(AUDIO_ROOT) if re.match(r"^\d{4}-\d{2}-\d{2}$", d)])
        cutoff = (datetime.now(timezone(timedelta(hours=8))) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
        for d in dirs:
            if d < cutoff:
                import shutil
                shutil.rmtree(os.path.join(AUDIO_ROOT, d), ignore_errors=True)
                print("  [cleanup] removed", d)
    except Exception as e:
        print("  [cleanup skip]", repr(e)[:100])


async def main():
    date = sys.argv[1] if len(sys.argv) > 1 else common.today_ymd()
    print("=== 简报播客音频生成:", date, "===")
    report = common.fetch_report(CFG, date)
    if not report:
        print("!! 该日期无 report，退出")
        return
    outdir = os.path.join(AUDIO_ROOT, date)
    os.makedirs(outdir, exist_ok=True)

    en_map = common.fetch_en_map(CFG)
    print("  英文原题映射:", len(en_map), "条")
    items = build_tts_items(report, en_map)
    print("  待生成条目:", len(items), "条")

    manifest = {"date": date, "generatedAt": datetime.now(timezone.utc).isoformat(), "items": {}}
    ok_zh = ok_en = 0
    for idx, it in enumerate(items):
        key = it["key"]
        zh_file, en_file = key + "_zh.mp3", key + "_en.mp3"
        entry = {"title": it["title"]}
        if await synth(it["zh_text"], VOICE_ZH, os.path.join(outdir, zh_file)):
            entry["zh"] = zh_file
            ok_zh += 1
        if it["en_text"]:
            en_script = "Original headline. " + clean_text(it["en_text"])
            if await synth(en_script, VOICE_EN, os.path.join(outdir, en_file)):
                entry["en"] = en_file
                ok_en += 1
        manifest["items"][key] = entry
        print("  [%02d/%02d] %s | zh:%s en:%s" % (
            idx + 1, len(items), it["title"][:22],
            "Y" if "zh" in entry else "N", "Y" if "en" in entry else "-"))

    brief_script = build_brief_script(report, date)
    if await synth(brief_script, VOICE_ZH, os.path.join(outdir, "brief_zh.mp3")):
        manifest["brief"] = "brief_zh.mp3"
        print("  [brief] 速览稿 %d 字" % len(brief_script))
    else:
        print("  [brief] 生成失败，前端将回退 TTS")

    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    cleanup_old()
    total_size = sum(os.path.getsize(os.path.join(outdir, f))
                     for f in os.listdir(outdir) if f.endswith(".mp3"))
    print("=== 完成: 中文 %d / 英文 %d, 总大小 %.1f KB ===" % (ok_zh, ok_en, total_size / 1024))
    print("MANIFEST:", json.dumps({"date": date, "count": len(items), "zh": ok_zh, "en": ok_en}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
