#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于技能 dashboard-template.html 生成"全网有价值热搜聚合"单文件站点。
改造点（local 模式）：
  1) 顶部 SITE_CFG：品牌 + 5 板块 + dataMode:'local'
  2) fetchJson()：local 模式下读 data/index.json 与 data/<date>.json
  3) 静态品牌文字：hero、图例、订阅说明等改为热搜语境
  4) HOT_WORDS 换成热搜价值词，让日历高亮更有意义
  5) 因无预生成 mp3，播客按钮自动走浏览器 TTS（保留可用）
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL = "D:/Python Work/ai-brief-podcast-skill/assets/dashboard-template.html"

html = open(TPL, encoding="utf-8").read()

# ---- 1) 替换 SITE_CFG ----
old_cfg_start = html.index("var SITE_CFG = {")
old_cfg_end = html.index("};", old_cfg_start) + 2
new_cfg = '''var SITE_CFG = {
  dataMode: "local",
  apiBase: "",
  brand: "全网有价值热搜",
  brandEn: "HOT PULSE",
  dataCredit: "60s API · 多平台实时热搜",
  docTitle: "全网有价值热搜 · 聚合档案",
  sections: [
    {key:"tech",     label:"科技·AI·数码",   color:"#38bdf8"},
    {key:"finance",  label:"财经·市场",       color:"#34d399"},
    {key:"society",  label:"社会·民生",       color:"#fbbf24"},
    {key:"world",    label:"国际·时政",       color:"#fb7185"},
    {key:"science",  label:"科学·文化·体育", color:"#a78bfa"}
  ]
};'''
html = html[:old_cfg_start] + new_cfg + html[old_cfg_end:]

# ---- 2) 替换 HOT_WORDS（日历重大事件高亮）----
hw_start = html.index("var HOT_WORDS = [")
hw_end = html.index("];", hw_start) + 2
new_hw = '''var HOT_WORDS = [
    {w:"死刑", s:3},{w:"间谍", s:3},{w:"新政", s:3},{w:"重大", s:3},{w:"突破", s:3},
    {w:"发布", s:2},{w:"调整", s:2},{w:"首次", s:2},{w:"判", s:2},{w:"通报", s:2},
    {w:"暴涨", s:2},{w:"暴跌", s:2},{w:"G20", s:2},{w:"APEC", s:2},{w:"中美", s:2},
    {w:"央行", s:2},{w:"国常会", s:3},{w:"医保", s:2},{w:"AI", s:1},{w:"黄金", s:1},
    {w:"A股", s:1},{w:"原油", s:1},{w:"特朗普", s:1},{w:"透露", s:1}
  ];'''
html = html[:hw_start] + new_hw + html[hw_end:]

# ---- 3) 改造 fetchJson（local 模式）----
old_fetch = '''  function fetchJson(path){
    return fetch(BASE + path, {cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
  }'''
new_fetch = '''  function fetchJson(path){
    if(SITE_CFG.dataMode === 'local'){
      if(path.indexOf('/dailies?')===0)
        return fetch('data/index.json',{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
      var m = path.match(/\\/dailies\\/(\\d{4}-\\d{2}-\\d{2})/);
      if(m)
        return fetch('data/'+m[1]+'.json',{cache:"no-store"}).then(function(r){return r.ok?r.json().then(function(j){return {report:j};}):null;}).catch(function(){return null;});
      return Promise.resolve(null);
    }
    return fetch(BASE + path, {cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
  }'''
assert old_fetch in html, "fetchJson 未匹配"
html = html.replace(old_fetch, new_fetch)

# ---- 4) 静态品牌文字改造 ----
repls = {
    '<div class="kicker">AI HOT · 每日晨报档案 <span class="badge" id="dayBadge">实时</span></div>':
        '<div class="kicker">HOT PULSE · 全网热搜聚合 <span class="badge" id="dayBadge">实时</span></div>',
    '<h1 id="heroDate">AI 晨报</h1>':
        '<h1 id="heroDate">全网有价值热搜</h1>',
    '<span class="li"><i class="sw have"></i>有日报</span>':
        '<span class="li"><i class="sw have"></i>有数据</span>',
    "BRAND_EN + ' · 每日简报档案 '": "'HOT PULSE · 全网热搜聚合 '",
    "if (_hero && _hero.textContent.trim() === 'AI 晨报')": "if (_hero && _hero.textContent.trim() === '全网有价值热搜')",
    "BRAND_EN+' · 每日简报'": "BRAND_EN+' · 热搜聚合'",
    "showMainLoading('正在加载 '+date+' 的日报…')": "showMainLoading('正在加载 '+date+' 的热搜…')",
    "textContent='分享本日日报'": "textContent='分享本日热搜'",
    "toast('速览音频未就绪，请先打开当天日报')": "toast('速览音频未就绪，请先打开当天热搜')",
    "sub+=' · 日报生成于 '+fG(report.generatedAt)": "sub+=' · 数据采集于 '+fG(report.generatedAt)",
    "sub+=' · 正在回看历史日报'": "sub+=' · 正在回看历史热搜'",
}
for a, b in repls.items():
    if a in html:
        html = html.replace(a, b)
    else:
        print("[warn] 未匹配:", a[:50])

# ---- 5) 订阅弹窗文案改为说明（本应用无 RSS，保留按钮但改为数据源说明）----
html = html.replace("把本简报的速览播客加到你的播客客户端，每天自动更新一期。复制下面的订阅地址，在播客 App 里「添加订阅 / 输入 RSS 链接」即可。",
                    "本页聚合微博 / 知乎 / 抖音 / 今日头条 / 百度 五大平台的实时热搜，经主题打分、跨平台共振加权、去重筛选后呈现。数据由 60s API 提供。")

# ---- 6) 注入 generatedAt（报告无此字段时，用当天采集时间）----
# 数据契约 report 未带 generatedAt，补一个让页脚显示采集时间
needle = 'var report ='
# 不改 getReport 逻辑，改为在数据 JSON 里加 generatedAt（在 build_data 已可加）；此处兜底提示
html = html.replace('<div class="kicker">HOT PULSE · 全网热搜聚合 <span class="badge" id="dayBadge">实时</span></div>',
                    '<div class="kicker">HOT PULSE · 全网热搜聚合 <span class="badge" id="dayBadge">实时</span></div>\n    <p class="sub" style="margin-top:8px">筛选有价值的公共热点 · 5 平台聚合 · 主题打分 + 跨平台共振</p>', 1)

out = os.path.join(ROOT, "index.html")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print("已生成:", out, "|", len(html), "字符")
