#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 60s API 多平台热搜 → 筛选"有价值"条目 → 聚合成技能的 local 数据契约。

输出：
  data/<date>.json   report 对象（lead + sections + flashes ...）
  data/index.json    日历索引（{items:[{date,leadTitle,leadParagraph}]}）

筛选逻辑：
  1) 高价值主题关键词加权；娱乐/饭圈/玩梗/探店降权；
  2) 跨平台共振加分（同一事件出现在多个平台）；
  3) 相似标题去重合并，保留最高热度 + 来源平台列表；
  4) 按 综合分 排序，分入 5 个板块。
"""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

PLATFORM_NAMES = {
    "weibo": "微博", "zhihu": "知乎", "douyin": "抖音",
    "toutiao": "今日头条", "baidu": "百度", "bili": "哔哩哔哩",
}

# 主题分类：(板块key, 板块label, 关键词列表)
TOPICS = [
    ("tech", "科技·AI·数码", [
        "AI", "人工智能", "大模型", "DeepSeek", "Gemini", "GPT", "算法", "芯片", "半导体", "算力",
        "智能", "机器人", "数码", "手机", "华为", "小米", "特斯拉", "新能源", "自动驾驶", "电池",
        "开源", "模型", "数据中心", "量子", "卫星", "航天", "火箭", "歼", "战机", "导弹", "无人机",
        "Gemini", "互联网", "科技", "编程", "操作系统", "6G", "5G", "光刻",
    ]),
    ("finance", "财经·市场", [
        "股", "A股", "沪指", "黄金", "金价", "美元", "汇率", "经济", "市场", "消费", "融资", "上市",
        "IPO", "基金", "楼市", "房价", "利率", "关税", "贸易", "GDP", "通胀", "油价", "成品油",
        "交易所", "保证金", "KOSPI", "华尔街", "超卖", "指数", "投资", "物价", "茶业", "工厂",
    ]),
    ("society", "社会·民生", [
        "医保", "医疗", "医院", "药", "血压", "健康", "教育", "学校", "高校", "学生", "高考", "国考",
        "公务员", "工资", "就业", "退休", "养老", "住房", "交通", "食品", "安全", "通报", "警方",
        "判", "死刑", "间谍", "泄密", "受贿", "行贿", "诈骗", "反诈", "辟谣", "骑手", "外卖",
        "马拉松", "气压", "天气", "台风", "地震", "洪水", "消防", "火灾", "事故", "维权", "业主",
    ]),
    ("world", "国际·时政", [
        "特朗普", "美国", "日本", "高市", "石破茂", "APEC", "中美", "俄", "乌克兰", "以色列", "越南",
        "国际", "外交", "关税", "战争", "开打", "谈判", "联合国", "欧盟", "韩国", "朝鲜", "台湾",
        "领空", "军演", "制裁", "元首", "访华", "国情", "人民日报", "环球时报", "权威数读",
    ]),
    ("science", "科学·文化·体育", [
        "黎曼猜想", "数学", "科学", "研究", "院士", "博士", "论文", "吉尼斯", "纪录", "诺贝尔",
        "考古", "历史", "文物", "博物馆", "樊振东", "乒乓球", "CBA", "篮球", "夺冠", "比赛",
        "国乒", "奥运", "足球", "网球", "游", "马拉松", "世界工厂", "空间站", "月球",
    ]),
]

# 娱乐/低价值降权关键词（命中即降分；命中多个基本淘汰）
ENTERTAIN_NEG = [
    "榜一", "送了", "爱豆", "饭圈", "粉丝", "团宠", "回应", "恋情", "单身", "生日会", "生日",
    "手势舞", "挑战", "追剧", "首播", "辣评", "第7集", "封神", "打戏", "婚礼变葬礼", "虐麻",
    "顶流", "NPC", "炸鸡", "美食", "探店", "好吃", "穿搭", "晚霞", "浪漫", "松弛感", "跳舞",
    "广场舞", "直播热度", "被镜头切到", "求合影", "认成", "烂梗", "女博士卧底", "上门服务",
    "为什么大便", "体重", "排泄物", "炸鸡店", "treetree", "kissmysoul", "斗破", "两京十五日",
]

# 强正向信号：权威媒体/硬新闻动词
AUTHORITY_POS = ["通报", "判死刑", "间谍", "泄密", "新政", "政策", "发布", "调整", "进医保", "回应", "官方", "权威", "披露"]

LEVEL_LABEL = {3: "高", 2: "中", 1: "低"}

# 高辨识度实体短语：不同平台描述同一事件时几乎都会带上
ENTITY_KEYS = [
    "间谍", "泄密", "情报", "判死刑", "获死刑", "私闯果园", "糟蹋苹果", "现货黄金", "3600美元",
    "方力申", "香港游到澳门",
    "樊振东", "约内斯库", "黎曼猜想", "融资保证金", "稳股市", "成品油价", "Gemini",
    "DeepSeek", "KOSPI", "高市早苗", "石破茂", "吉尼斯", "庞众望", "抗癌药", "进医保",
    "treetree", "外卖骑手电摩", "割断高空作业", "国考",
]


def norm(s):
    s = re.sub(r"[?？!！,，。、:：;；\"'\s]", "", str(s or ""))
    return s.lower()


def load_rows():
    rows = []
    for f in sorted(os.listdir(RAW)):
        if not f.endswith(".json") or f.endswith("_raw.json"):
            continue
        d = json.load(open(os.path.join(RAW, f), encoding="utf-8"))
        plat = d.get("platform")
        for r in d.get("data", []):
            title = str(r.get("title") or "").strip()
            if not title:
                continue
            hot = r.get("hot_value") or r.get("score") or r.get("hot_value_desc") or "0"
            m = re.search(r"[\d.]+", str(hot).replace(",", ""))
            hotnum = float(m.group()) if m else 0
            if "万" in str(hot):
                hotnum *= 10000
            link = r.get("link") or r.get("url") or ""
            desc = r.get("desc") or r.get("detail") or ""
            rows.append({"title": title, "hot": hotnum, "hot_raw": str(hot), "platform": plat, "link": link, "desc": str(desc)})
    return rows


def classify(title):
    """返回 (板块key, 板块label, 正向分)。"""
    t = title
    best_key, best_label, best_score = "society", "社会·民生", 0
    for key, label, words in TOPICS:
        s = sum(1 for w in words if w.lower() in t.lower())
        if s > best_score:
            best_score, best_key, best_label = s, key, label
    return best_key, best_label, best_score


def ent_penalty(title):
    return sum(1 for w in ENTERTAIN_NEG if w in title)


def authority_bonus(title):
    return sum(1 for w in AUTHORITY_POS if w in title)


def bigrams(s):
    """中文二元组集合，用于语义相似度（Jaccard）。"""
    s = norm(s)
    if len(s) < 2:
        return {s}
    return set(s[i:i + 2] for i in range(len(s) - 1))


def dedup_and_score(rows):
    """相似标题合并 + 评分（含二元组 Jaccard 相似度去重）。"""
    grams = [bigrams(r["title"]) for r in rows]
    groups = []
    used = [False] * len(rows)
    for i, r in enumerate(rows):
        if used[i]:
            continue
        key = norm(r["title"])
        grp = [r]
        used[i] = True
        for j in range(i + 1, len(rows)):
            if used[j]:
                continue
            k2 = norm(rows[j]["title"])
            same = key == k2
            contain = (len(key) >= 8 and len(k2) >= 8 and (key in k2 or k2 in key)
                       and min(len(key), len(k2)) / max(len(key), len(k2)) > 0.6)
            # Jaccard 相似度：捕捉不同措辞但同一事件（如"间谍死刑"两种表述）
            g1, g2 = grams[i], grams[j]
            jac = len(g1 & g2) / len(g1 | g2) if (g1 | g2) else 0
            # 关键实体短语强特征：命中相同短语视为同一事件
            entity_hits = sum(1 for kw in ENTITY_KEYS if kw in r["title"] and kw in rows[j]["title"])
            similar = jac >= 0.42 or entity_hits >= 1
            if same or contain or similar:
                grp.append(rows[j])
                used[j] = True
        groups.append(grp)
    out = []
    for grp in groups:
        plats = sorted(set(g["platform"] for g in grp))
        title = max(grp, key=lambda g: g["hot"])["title"]
        desc = next((g["desc"] for g in grp if g["desc"]), "")
        link = max(grp, key=lambda g: g["hot"])["link"]
        maxhot = max(g["hot"] for g in grp)
        key, label, topic_score = classify(title)
        neg = max(ent_penalty(g["title"]) for g in grp)
        auth = authority_bonus(title)
        cross = len(plats)  # 跨平台数
        # 综合分：主题 + 跨平台*3 + 权威*1.5 - 娱乐*3；热度取对数缩放
        score = topic_score * 2 + cross * 3 + auth * 1.5 - neg * 3
        score += min(3.0, (maxhot / 1e6) ** 0.5)  # 热度温和加成，最高+3
        out.append({
            "title": title, "desc": desc, "link": link, "platforms": plats,
            "platform_names": [PLATFORM_NAMES.get(p, p) for p in plats],
            "maxhot": maxhot, "topic": key, "topic_label": label,
            "topic_score": topic_score, "neg": neg, "auth": auth, "cross": cross,
            "score": score,
        })
    return out


def main():
    date = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 8 * 3600))  # 北京时间今天
    rows = load_rows()
    print("原始条目:", len(rows), "日期:", date)
    merged = dedup_and_score(rows)
    print("去重后:", len(merged), "条")

    # 分层：保留非娱乐向的；score 阈值切分
    kept = [m for m in merged if m["neg"] < 2 and m["score"] >= 4]
    # 板块额度，避免单一板块过多
    quota = {"tech": 8, "finance": 8, "society": 9, "world": 8, "science": 7}
    buckets = {k: [] for k in quota}
    for m in sorted(kept, key=lambda x: -x["score"]):
        k = m["topic"]
        if len(buckets[k]) < quota[k]:
            buckets[k].append(m)
    total = sum(len(v) for v in buckets.values())
    print("精选条目:", total, "条 | 分板块:", {k: len(v) for k, v in buckets.items()})

    # 构造 lead：优先跨平台共振多 + 权威硬新闻（score + 额外权威加权）
    allsel = [m for v in buckets.values() for m in v]
    allsel.sort(key=lambda x: -x["score"])
    lead = max(allsel, key=lambda m: (m["score"] + m["auth"] * 2 + m["cross"] * 1.5)) if allsel else None

    def item_of(m):
        plat = " / ".join(m["platform_names"])
        summary = m["desc"].strip()[:90] if m["desc"] else ""
        summary = (summary + " · " if summary else "") + "来源：" + plat + "｜综合热度 " + fmt_hot(m["maxhot"])
        return {
            "title": m["title"], "summary": summary, "originalTitle": "",
            "source": {"name": " / ".join(m["platform_names"])},
            "id": "h" + str(abs(hash(m["title"])) % 10**10),
            "links": {"aihot": m["link"], "original": m["link"]},
        }

    sections = []
    for key, label, _ in TOPICS:
        items = sorted(buckets.get(key, []), key=lambda x: -x["score"])
        if items:
            sections.append({"key": key, "label": label,
                             "items": [item_of(m) for m in items]})

    report = {
        "date": date,
        "windowStart": date + "T00:00:00+08:00",
        "windowEnd": date + "T23:59:59+08:00",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.gmtime(time.time() + 8 * 3600)),
        "lead": {
            "title": lead["title"] if lead else "今日暂无精选热搜",
            "leadParagraph": ("来源：" + " / ".join(lead["platform_names"]) +
                              "｜综合热度 " + fmt_hot(lead["maxhot"])) if lead else "",
            "originalTitle": "",
            "links": {"aihot": lead["link"] if lead else "", "original": lead["link"] if lead else ""},
        } if lead else {"title": "今日暂无精选热搜", "leadParagraph": ""},
        "sections": sections,
        "flashes": [],
        "highlights": [],
        "attribution": {"name": "60s API · 多平台实时热搜（筛选聚合）"},
        "links": {"aihot": "https://60s.viki.moe"},
    }

    with open(os.path.join(DATA, date + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    idx = {"items": [{"date": date, "leadTitle": report["lead"]["title"],
                      "leadParagraph": report["lead"]["leadParagraph"]}]}
    with open(os.path.join(DATA, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

    # 明细存一份便于审阅筛选质量
    with open(os.path.join(DATA, "_selected_debug.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump([{k: m[k] for k in ("title", "score", "topic_label", "cross", "neg", "platform_names")}
                   for m in sorted(allsel, key=lambda x: -x["score"])], f, ensure_ascii=False, indent=2)

    print("已写入 data/%s.json + data/index.json" % date)
    print("\n=== 今日头条:", report["lead"]["title"])
    for s in sections:
        print("\n[%s] %d条" % (s["label"], len(s["items"])))
        for it in s["items"]:
            print("  -", it["title"][:46])


def fmt_hot(n):
    if n >= 1e8:
        return "%.2f亿" % (n / 1e8)
    if n >= 1e4:
        return "%.1f万" % (n / 1e4)
    return str(int(n))


if __name__ == "__main__":
    main()
