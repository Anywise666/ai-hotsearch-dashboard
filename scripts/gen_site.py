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

# 模板优先读仓库内副本（保证 GitHub Actions / 任意机器自包含），
# 找不到再回退到技能仓库原始路径（本地开发时可能更新模板）。
TPL_LOCAL = os.path.join(ROOT, "assets", "dashboard-template.html")
TPL_SKILL = "D:/Python Work/ai-brief-podcast-skill/assets/dashboard-template.html"
TPL = TPL_LOCAL if os.path.exists(TPL_LOCAL) else TPL_SKILL

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
  podcast: true,
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
      if(path.indexOf('/search-index')===0)
        return fetch('data/search-index.json',{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
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

# ---- 7) 个性化权重面板：CSS ----
TUNE_CSS = '''
  /* ===== 个性化权重面板 ===== */
  .tb-btn.tune{border-color:rgba(167,139,250,.5);color:#c4b5fd;background:rgba(167,139,250,.1)}
  .tb-btn.tune:hover{background:rgba(167,139,250,.2);border-color:#a78bfa}
  body.theme-light .tb-btn.tune{color:#6d28d9;border-color:#c4b5fd;background:rgba(167,139,250,.14)}
  .tune-modal{max-width:640px;max-height:86vh;overflow-y:auto}
  .tune-lead{font-size:12.5px;color:var(--mut);line-height:1.7;margin-bottom:6px}
  .tune-state{font-size:12px;padding:7px 11px;border-radius:9px;margin-bottom:14px;
    background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.3);color:#c4b5fd}
  body.theme-light .tune-state{color:#6d28d9}
  .tune-group{margin:16px 0 6px;font-size:13px;font-weight:800;color:var(--accent);
    border-bottom:1px solid var(--line);padding-bottom:6px}
  .tune-row{display:grid;grid-template-columns:1fr 130px 52px;gap:12px;align-items:center;
    padding:7px 0;font-size:13px}
  .tune-row .tl{color:var(--txt)}
  .tune-row .tl small{display:block;color:var(--mut);font-size:11px;font-weight:400}
  .tune-row input[type=range]{width:100%;accent-color:var(--accent);cursor:pointer}
  .tune-row .tval{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;
    color:#fbbf24;min-width:44px}
  body.theme-light .tune-row .tval{color:#b45309}
  .tune-foot{font-size:11.5px;color:var(--mut);margin-top:14px;line-height:1.6}
'''
html = html.replace('</style>', TUNE_CSS + '\n</style>', 1)

# ---- 7b) 全局搜索：命中高亮样式 ----
SEARCH_CSS = '''
  /* ===== 全局搜索命中高亮 ===== */
  .search-hit{outline:2px solid #fbbf24;outline-offset:3px;box-shadow:0 0 0 6px rgba(251,191,36,.14);animation:shpulse 1.4s ease-in-out 2}
  @keyframes shpulse{0%,100%{box-shadow:0 0 0 6px rgba(251,191,36,.10)}50%{box-shadow:0 0 0 12px rgba(251,191,36,.26)}}
  .search-hit-card{background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.45);border-radius:14px;padding:16px 18px;margin-bottom:18px}
  .search-hit-tag{font-size:11px;color:#fbbf24;font-weight:700;margin-bottom:7px}
  body.theme-light .search-hit-card{background:#fffbeb;border-color:#f59e0b}
  body.theme-light .search-hit-tag{color:#b45309}
  .sr-pool{font-size:10px;color:#a78bfa;margin-left:6px}
  body.theme-light .sr-pool{color:#6d28d9}
'''
html = html.replace('</style>', SEARCH_CSS + '\n</style>', 1)

# ---- 8) 个性化权重面板：工具栏按钮 ----
tune_btn = '    <button class="tb-btn tune" id="tuneBtn" title="定制你的专属权重">🎛 我的权重</button>\n'
anchor_tb = '    <button class="tb-btn" id="themeBtn"'
assert anchor_tb in html, "工具栏锚点未匹配"
html = html.replace(anchor_tb, tune_btn + anchor_tb, 1)

# ---- 9) 个性化权重面板：弹窗 DOM（放在订阅弹窗之后） ----
tune_dom = '''
  <!-- 个性化权重面板 -->
  <div class="modal-mask" id="tuneMask">
    <div class="modal tune-modal" role="dialog" aria-modal="true" aria-label="定制我的权重">
      <h3>🎛 定制我的权重</h3>
      <div class="tune-lead">这里调整只保存在你自己的浏览器里，不影响其他访客，也不会改动网站配置。拖动滑块即时重排热搜。</div>
      <div class="tune-state" id="tuneState">当前使用：网站默认权重</div>
      <div id="tuneBody"></div>
      <div class="tune-foot">说明：权重只影响排序、条目去留、板块配额与头条选拔；板块归类由服务端关键词决定，此处不改。</div>
      <div class="modal-acts">
        <button id="tuneReset">恢复默认</button>
        <button class="ghost" id="tuneClose">完成</button>
      </div>
    </div>
  </div>
'''
anchor_dom = '<div class="modal-mask" id="subMask">'
assert anchor_dom in html, "订阅弹窗锚点未匹配"
html = html.replace(anchor_dom, tune_dom + '\n' + anchor_dom, 1)

# ---- 10) 个性化权重面板：JS（重算 report + 面板交互 + 持久化）----
TUNE_JS = r'''
  // ===== 个性化权重：浏览器端按用户权重重算 report（不影响其他访客）=====
  var TUNE_DEFAULTS = __TUNE_DEFAULTS__;
  var TUNE_FIELDS = [
    {g:"评分权重", rows:[
      {k:"topic",     label:"主题匹配分",   hint:"命中价值主题词的加分",          min:0,max:6,step:0.5},
      {k:"cross",     label:"跨平台共振",   hint:"同一事件出现在多个平台的加分",  min:0,max:8,step:0.5},
      {k:"auth",      label:"权威信号",     hint:"官方/政策/披露等硬新闻加分",    min:0,max:6,step:0.5},
      {k:"neg",       label:"娱乐降权",     hint:"娱乐八卦命中的扣分",            min:0,max:8,step:0.5},
      {k:"hot_cap",   label:"热度加成上限", hint:"热度分最高加成",                min:0,max:6,step:0.5}
    ]},
    {g:"过滤阈值", rows:[
      {k:"min_score", label:"入选最低分",   hint:"综合分低于此值的条目被淘汰",    min:0,max:20,step:0.5},
      {k:"max_neg",   label:"娱乐淘汰线",   hint:"娱乐命中数达到此值直接淘汰",    min:0,max:6,step:1}
    ]},
    {g:"头条加权", rows:[
      {k:"lead_auth", label:"头条权威加权", hint:"选拔头条时的权威额外加权",      min:0,max:6,step:0.5},
      {k:"lead_cross",label:"头条共振加权", hint:"选拔头条时的共振额外加权",      min:0,max:6,step:0.5}
    ]},
    {g:"各板块条数", rows:[]}
  ];
  SECTIONS_META.forEach(function(m){
    TUNE_FIELDS[3].rows.push({k:"q_"+m.key, label:m.label, hint:"该板块最多展示条数", min:0,max:20,step:1});
  });

  function tuneDefaults(){
    var d=TUNE_DEFAULTS;
    return {
      topic:d.weights.topic, cross:d.weights.cross, auth:d.weights.auth,
      neg:d.weights.neg, hot_cap:d.weights.hot_cap,
      min_score:d.thresholds.min_score, max_neg:d.thresholds.max_neg,
      lead_auth:d.lead_weights.auth, lead_cross:d.lead_weights.cross
    };
  }
  function currentTune(report){
    var base=tuneDefaults();
    SECTIONS_META.forEach(function(m){ base["q_"+m.key]=TUNE_DEFAULTS.quota[m.key]; });
    if(report && report.tuning){
      var t=report.tuning;
      ["topic","cross","auth","neg","hot_cap"].forEach(function(k){ if(t.weights&&t.weights[k]!=null) base[k]=t.weights[k]; });
      if(t.thresholds){ if(t.thresholds.min_score!=null) base.min_score=t.thresholds.min_score; if(t.thresholds.max_neg!=null) base.max_neg=t.thresholds.max_neg; }
      if(t.lead_weights){ if(t.lead_weights.auth!=null) base.lead_auth=t.lead_weights.auth; if(t.lead_weights.cross!=null) base.lead_cross=t.lead_weights.cross; }
      SECTIONS_META.forEach(function(m){ if(t.quota&&t.quota[m.key]!=null) base["q_"+m.key]=t.quota[m.key]; });
    }
    // 用户本地覆盖（合并，防止配置新增字段后旧本地缺字段）
    if(PREFS.weights){
      Object.keys(base).forEach(function(k){ if(typeof PREFS.weights[k]==="number") base[k]=PREFS.weights[k]; });
    }
    return base;
  }
  function tuneFmtHot(n){
    n=Number(n)||0;
    if(n>=1e8) return (n/1e8).toFixed(2)+"亿";
    if(n>=1e4) return (n/1e4).toFixed(1)+"万";
    return String(Math.floor(n));
  }
  function tuneHash(s){ s=String(s||""); var h=0; for(var i=0;i<s.length;i++){ h=((h<<5)-h+s.charCodeAt(i))|0; } return h; }
  // 用 pool + 当前权重重算 report；无 pool 的历史/旧数据原样返回
  function retune(report, W){
    var pool=report && report.pool;
    if(!pool || !pool.length) return report;
    var scored=pool.map(function(m){
      var s=m.topic_score*W.topic + m.cross*W.cross + m.auth*W.auth - m.neg*W.neg
            + Math.min(W.hot_cap, Math.pow((m.maxhot||0)/1e6, 0.5));
      return Object.assign({}, m, {_s:s});
    });
    var buckets={}; SECTIONS_META.forEach(function(x){ buckets[x.key]=[]; });
    scored.filter(function(m){ return m.neg < W.max_neg && m._s >= W.min_score; })
      .sort(function(a,b){ return b._s-a._s; })
      .forEach(function(m){
        var q=W["q_"+m.topic]; if(q==null) q=0;
        if(buckets[m.topic] && buckets[m.topic].length<q) buckets[m.topic].push(m);
      });
    var all=[].concat.apply([], Object.keys(buckets).map(function(k){ return buckets[k]; }));
    var lead=all.length ? all.reduce(function(a,b){
      var sa=a._s+a.auth*W.lead_auth+a.cross*W.lead_cross;
      var sb=b._s+b.auth*W.lead_auth+b.cross*W.lead_cross;
      return sb>sa ? b : a;
    }) : null;
    var sections=[];
    SECTIONS_META.forEach(function(x){
      var items=buckets[x.key].map(function(m){
        var plat=(m.platform_names||[]).join(" / ");
        var sum=(m.desc||"").trim().slice(0,90);
        sum=(sum?sum+" · ":"")+"来源："+plat+"｜综合热度 "+tuneFmtHot(m.maxhot);
        return {title:m.title, summary:sum, originalTitle:"", source:{name:plat},
          id:"h"+Math.abs(tuneHash(m.title))%10000000000,
          links:{aihot:m.link, original:m.link}};
      });
      if(items.length) sections.push({key:x.key, label:x.label, items:items});
    });
    var rp=Object.assign({}, report, {sections:sections});
    rp.lead=lead ? {title:lead.title,
      leadParagraph:"来源："+(lead.platform_names||[]).join(" / ")+"｜综合热度 "+tuneFmtHot(lead.maxhot),
      originalTitle:"", links:{aihot:lead.link, original:lead.link}} : report.lead;
    return rp;
  }
  var TUNE_BUILT=false;
  function tuneBuildPanel(){
    if(TUNE_BUILT) return;
    var host=document.getElementById("tuneBody"); if(!host) return;
    var W=currentTune(STATE.rawReport||null);
    TUNE_FIELDS.forEach(function(grp){
      host.appendChild(el("div","tune-group",grp.g));
      grp.rows.forEach(function(f){
        var row=el("div","tune-row");
        var tl=el("div","tl"); tl.appendChild(document.createTextNode(f.label));
        if(f.hint) tl.appendChild(el("small",null,f.hint));
        var range=document.createElement("input"); range.type="range";
        range.min=f.min; range.max=f.max; range.step=f.step; range.value=W[f.k];
        range.setAttribute("data-k",f.k); range.setAttribute("data-step",f.step);
        var val=el("span","tval", Number(W[f.k]).toFixed(f.step<1?1:0));
        range.oninput=function(){
          var v=Number(range.value);
          val.textContent=v.toFixed(f.step<1?1:0);
          if(!PREFS.weights) PREFS.weights={};
          PREFS.weights[f.k]=v;
          savePrefs();
          tuneApplyAndRender();
        };
        row.appendChild(tl); row.appendChild(range); row.appendChild(val);
        host.appendChild(row);
      });
    });
    TUNE_BUILT=true;
  }
  function tuneSyncInputs(){
    var W=currentTune(STATE.rawReport||null);
    var inputs=document.querySelectorAll("#tuneBody input[type=range]");
    for(var i=0;i<inputs.length;i++){
      var inp=inputs[i], k=inp.getAttribute("data-k"), step=Number(inp.getAttribute("data-step"));
      if(typeof W[k]!=="number") continue;
      inp.value=W[k];
      var row=inp.parentNode, val=row.querySelector(".tval");
      if(val) val.textContent=Number(W[k]).toFixed(step<1?1:0);
    }
  }
  function tuneApplyAndRender(){
    if(!STATE.rawReport) return;
    var date=STATE.selectedDate;
    var W=currentTune(STATE.rawReport);
    var rp=retune(STATE.rawReport, W);
    REPORT_CACHE[date]=rp;
    renderReport(rp, date, date===STATE.today);
    tuneUpdateState();
  }
  function tuneUpdateState(){
    var custom=!!(PREFS.weights && Object.keys(PREFS.weights).length);
    var st=document.getElementById("tuneState");
    if(st) st.textContent = custom ? "当前使用：我的专属权重（已保存在本机浏览器，不影响其他访客）" : "当前使用：网站默认权重";
    var btn=document.getElementById("tuneBtn");
    if(btn) btn.classList.toggle("on", custom);
  }
  function tuneOpen(){ tuneBuildPanel(); tuneSyncInputs(); tuneUpdateState(); document.getElementById("tuneMask").classList.add("show"); }
  function tuneClose(){ document.getElementById("tuneMask").classList.remove("show"); }
  var tuneBtnEl=document.getElementById("tuneBtn");
  if(tuneBtnEl) tuneBtnEl.onclick=tuneOpen;
  var tuneCloseEl=document.getElementById("tuneClose");
  if(tuneCloseEl) tuneCloseEl.onclick=tuneClose;
  var tuneMaskEl=document.getElementById("tuneMask");
  if(tuneMaskEl) tuneMaskEl.onclick=function(e){ if(e.target===this) tuneClose(); };
  var tuneResetEl=document.getElementById("tuneReset");
  if(tuneResetEl) tuneResetEl.onclick=function(){
    PREFS.weights=null; savePrefs(); tuneSyncInputs(); tuneApplyAndRender(); toast("已恢复网站默认权重");
  };
  var _tuneEsc=document.addEventListener; // keep listener registration below aligned
  document.addEventListener("keydown",function(e){ if(e.key==="Escape"){ document.getElementById("tuneMask").classList.remove("show"); } });

  // ===== 全局搜索索引 + 命中重排定位 =====
  var GLOBAL_SEARCH_LOADED=false;
  async function loadGlobalSearch(){
    if(GLOBAL_SEARCH_LOADED) return;
    GLOBAL_SEARCH_LOADED=true;
    try{
      var j=await fetchJson('/search-index');
      if(!j || !j.items || !j.items.length) return;
      var seen={}; SEARCH_DOCS.forEach(function(d){ if(d.key) seen[d.key]=1; });
      j.items.forEach(function(x){
        if(!x || !x.date || !x.title) return;
        var k=x.key||itemKey(x.date,x.title);
        if(seen[k]) return; seen[k]=1;
        SEARCH_DOCS.push({date:x.date,title:x.title,summary:x.summary||'',
          section:x.section||'',url:x.url||'',key:k});
      });
    }catch(e){}
  }

  // 记住被点击的搜索结果标题；跳转到历史日期并重排后，高亮/置顶该条
  function applySearchFocus(){
    var title=STATE.searchFocusTitle;
    if(!title) return;
    var shownDate=STATE.selectedDate;
    var cards=document.querySelectorAll('#main .card h3 a');
    var target=null;
    for(var i=0;i<cards.length;i++){
      if((cards[i].textContent||'').trim()===String(title).trim()){ target=cards[i].closest('.card'); break; }
    }
    if(!target){
      // 头条位于 lead-card
      var lead=document.querySelector('#main .lead-card h3 a');
      if(lead && (lead.textContent||'').trim()===String(title).trim()) target=lead.closest('.lead-card');
    }
    if(target){
      target.classList.add('search-hit');
      try{ target.scrollIntoView({behavior:'smooth',block:'center'}); }catch(e){}
      STATE.searchFocusTitle=null;
    }else{
      // 该条在当前权重下未入选：以提示卡形式置顶，保证"搜到就能定位到"
      var main=document.getElementById('main');
      if(main && !document.getElementById('searchFocusCard')){
        var box=el('div','search-hit-card'); box.id='searchFocusCard';
        box.appendChild(el('div','search-hit-tag','🔍 搜索命中 · 当前权重下未入选精选，已为你置顶'));
        var h=el('h3'); var a=document.createElement('a'); a.textContent=title;
        a.href='#'; a.onclick=function(e){e.preventDefault();}; h.appendChild(a); box.appendChild(h);
        main.insertBefore(box, main.firstChild);
        try{ box.scrollIntoView({behavior:'smooth',block:'center'}); }catch(e){}
      }
      STATE.searchFocusTitle=null;
    }
  }
'''
# 注入默认值 JSON
import json as _json
_cfg_path = os.path.join(ROOT, "config.json")
_cfg = _json.load(open(_cfg_path, encoding="utf-8")) if os.path.exists(_cfg_path) else {}
_tune_defaults = {
    "weights": {k: _cfg.get("weights", {}).get(k, d) for k, d in
                {"topic": 2, "cross": 3, "auth": 1.5, "neg": 3, "hot_cap": 3.0}.items()},
    "thresholds": {"min_score": _cfg.get("thresholds", {}).get("min_score", 4),
                   "max_neg": _cfg.get("thresholds", {}).get("max_neg", 2)},
    "quota": _cfg.get("quota", {"tech": 8, "finance": 8, "society": 9, "world": 8, "science": 7}),
    "lead_weights": {"auth": _cfg.get("lead_weights", {}).get("auth", 2),
                     "cross": _cfg.get("lead_weights", {}).get("cross", 1.5)},
}
TUNE_JS = TUNE_JS.replace("__TUNE_DEFAULTS__", _json.dumps(_tune_defaults, ensure_ascii=False))

# PREFS 增加 weights 字段 + 启动时读回（否则刷新后本地权重丢失）
old_prefs = "  var PREFS = { theme:'dark', fs:'normal', rate:1, favs:{}, reads:{} };"
new_prefs = "  var PREFS = { theme:'dark', fs:'normal', rate:1, favs:{}, reads:{}, weights:null };"
assert old_prefs in html, "PREFS 初始化锚点未匹配"
html = html.replace(old_prefs, new_prefs, 1)
old_read = "      if(p.reads && typeof p.reads==='object') PREFS.reads=p.reads;"
new_read = old_read + "\n      if(p.weights && typeof p.weights==='object') PREFS.weights=p.weights;"
assert old_read in html, "PREFS 读取锚点未匹配"
html = html.replace(old_read, new_read, 1)

# selectDate：拿到 report 后按用户权重重算，再渲染；渲染后同步面板状态
old_sd = "      var report=await getReport(date);\n      REPORT_CACHE[date]=report;"
new_sd = """      var report=await getReport(date);
      STATE.rawReport=report;                              // 保留原始候选池供重算
      report=retune(report, currentTune(report));          // 按用户/默认权重重排
      REPORT_CACHE[date]=report;"""
assert old_sd in html, "selectDate 锚点未匹配"
html = html.replace(old_sd, new_sd, 1)

# renderReport 后同步权重按钮高亮状态（刷新后正确反映"我的权重"）
old_rr = "      renderReport(report, date, (date===STATE.today));"
new_rr = old_rr + "\n      if(typeof tuneUpdateState==='function') tuneUpdateState();"
assert old_rr in html, "renderReport 调用锚点未匹配"
html = html.replace(old_rr, new_rr, 1)

# 搜索命中高亮：在 renderReport 末尾统一触发（覆盖 selectDate 与调权重重绘两条路径）
old_foot = "    else foot.appendChild(el('span',null,'数据来源：'+src));\n  }\n\n  function showMainLoading"
new_foot = "    else foot.appendChild(el('span',null,'数据来源：'+src));\n    if(typeof applySearchFocus==='function') applySearchFocus();\n  }\n\n  function showMainLoading"
assert old_foot in html, "renderReport 末尾锚点未匹配"
html = html.replace(old_foot, new_foot, 1)

# 搜索结果点击：先记住标题，跳转/重排后再高亮定位
old_click = "        STATE.favMode=false; updateFavCount();\n        if(d.date) selectDate(d.date); else toast('该条目无可跳转日期');"
new_click = "        STATE.favMode=false; updateFavCount();\n        if(d.date){ STATE.searchFocusTitle=d.title; selectDate(d.date); } else toast('该条目无可跳转日期');"
assert old_click in html, "搜索点击锚点未匹配"
html = html.replace(old_click, new_click, 1)

# init()：加载全局搜索索引（覆盖全部历史 + 候选池），与索引加载并行不阻塞
old_init = "      await loadIndex();\n      await enPromise;\n      collectIndexDocs();   // 用 180 天头条建立搜索基线"
new_init = "      await loadIndex();\n      await enPromise;\n      collectIndexDocs();   // 用 180 天头条建立搜索基线\n      if(typeof loadGlobalSearch==='function') await loadGlobalSearch();  // 并入全量历史候选池"
assert old_init in html, "init 搜索加载锚点未匹配"
html = html.replace(old_init, new_init, 1)

# 把重算 JS 插到 init() 调用前（确保函数已定义）
anchor_init = "\n  init();\n})();"
assert anchor_init in html, "init 锚点未匹配"
html = html.replace(anchor_init, "\n" + TUNE_JS + "\n  init();\n})();", 1)

out = os.path.join(ROOT, "index.html")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print("已生成:", out, "|", len(html), "字符")
