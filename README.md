# 全网有价值热搜聚合仪表盘

聚合微博、知乎、抖音、B 站、今日头条、百度六个公共平台的实时热搜，按"公共价值"筛选去重后，呈现为与 AI 晨报同风格的单文件仪表盘。

> 本项目由 [ai-brief-podcast 技能](https://github.com/Anywise666/ai-brief-podcast-skill) 构建，视觉风格对齐 [ai-news-dashboard](https://github.com/Anywise666/ai-news-dashboard)。技能的定位是"把每日简报变成可看、可听、可订阅的站点"，本项目是这套方法论在**热搜聚合**场景的第一次落地验证。

## 它解决什么问题

公共平台热搜信息密度低、娱乐八卦与广告占比高。本项目不追求"全"，而是从 200+ 条原始热搜里筛出约 40 条**真正有公共价值**的条目——科技、财经、社会民生、国际、科学体育，并按跨平台共振度识别真正的重大事件。

## 数据链路

```
60s API ──┐
          ├─ 多源回退 → fetch_hot.py → build_data.py → gen_site.py → index.html
DailyHot ─┘    (raw/*.json)   (降级兜底)    (data/*.json)    单文件站点
```

| 环节 | 脚本 | 作用 |
|---|---|---|
| 抓取 | `scripts/fetch_hot.py` | 6 平台热搜，**双源回退**（60s API → DailyHotApi）+ 重试延时，字段归一化；DNS 不可达立即跳过；全失败保留上轮 raw、绝不写空覆盖 |
| 筛选聚合 | `scripts/build_data.py` | 价值打分 → 语义去重 → 板块配额 → `data/<日期>.json`；抓取不足时**降级复用最近有效报告**，并清空当日音频强制重合成，避免旧音频配新报告 |
| 建站 | `scripts/gen_site.py` | 基于技能模板，以 local 模式替换 `SITE_CFG` 生成 `index.html` |
| 一键更新 | `更新数据.sh` | 串联以上三步，每天跑一次即可刷新站点 |

## 个性化权重（每个访客各自定制）

站点工具栏的 **「🎛 我的权重」** 面板，让**每个访客在自己的浏览器里定制权重**，互不干扰：

- 14 个滑块覆盖评分权重（主题/共振/权威/娱乐/热度）、过滤阈值、头条加权、各板块条数
- 拖动即**实时重排**当天及历史热搜，无需刷新、无需 GitHub 账号
- 权重保存在浏览器本地（随主题/字号等偏好一起），刷新不丢；「恢复默认」一键回到网站设置
- 原理：数据文件附带去重后的**完整候选池（207 条，含各项特征分）**与默认权重 `tuning`，浏览器端用 JS 复刻评分公式重算 `report`。config.json 仍是全站默认值，但不限制访客
- 边界：权重只影响排序/去留/板块配额/头条；板块归类由服务端关键词决定，面板不改

> 这是与"全站统一调参"并存的第二套机制：站主用 config.json 定默认；访客用面板覆盖自己的版本。

## 筛选逻辑（"有价值"的定义）

全站**默认**权重、阈值、配额、关键词表都集中在根目录 **`config.json`**，可手动调节（访客可在网页端用上面的面板临时覆盖）。

**在线调参（推荐）**：直接在 GitHub 网页编辑 config.json（[点这里](https://github.com/Anywise666/ai-hotsearch-dashboard/edit/main/config.json)）→ 提交到 main。工作流监听 config.json 的推送，**改完即自动强制重跑**，几十秒后在线站就用上新权重，无需手动触发或等定时。本地改完推送同理；也可本地跑 `bash 更新数据.sh` 立即看效果。

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `weights.topic` | 2 | 主题关键词命中权重 |
| `weights.cross` | 3 | **跨平台共振**权重（同一事件多平台出现，"公共价值"最强信号） |
| `weights.auth` | 1.5 | 权威信号（通报/政策/判死刑等）权重 |
| `weights.neg` | 3 | 娱乐八卦降权系数（越大过滤越狠） |
| `weights.hot_cap` / `hot_scale` | 3.0 / 1e6 | 热度加成上限与缩放基数 |
| `thresholds.min_score` | 4 | 入选最低综合分（调高=更严格） |
| `thresholds.max_neg` | 2 | 娱乐命中数达到此值即淘汰 |
| `thresholds.jaccard` | 0.42 | 语义去重阈值（调低=合并更激进） |
| `quota` | 8/8/9/8/7 | 各板块最多条数（控制均衡） |
| `lead_weights` | 2 / 1.5 | 头条选择的权威/跨平台加权 |
| `keywords` | — | 四组关键词表（板块正向词、娱乐降权词、权威词、事件去重特征词） |

综合分公式：`主题命中×topic + 跨平台×cross + 权威×auth − 娱乐×neg + 热度加成`。每条配置的 JSON 里带 `_说明` 字段解释用途。

首日实测：229 条原始热搜 → 40 条精选（科技 8 / 财经 8 / 社会 9 / 国际 8 / 科学体育 7）。

## 功能

- 深色/浅色主题、字号调节、日历档案（按日期回看历史）
- **全局搜索（覆盖全部历史 + 完整候选池）**：`data/search-index.json` 汇总每天的完整候选池（含未入选精选的条目）。输入关键字即可搜到任意历史日期的条目；点击结果跳转到该日并按**当前权重重排**——若该条入选则高亮定位，若当前权重下未入选则置顶提示卡显示，做到"搜到即可定位"。与访客个性化权重完全兼容。
- 收藏/稍后读、已读标记、分享卡片
- 今日头条 + 5 板块全局编号，每条带来源平台、摘要与热度
- 90 秒速览 + **双语播客/订阅**（2026-11-24 启用档位三）：每日自动生成 `audio/<日期>/` 中文串读 mp3（头条+各条+90 秒速览），并提供 `feed.xml` RSS 订阅。播客按钮优先播放预生成音频，缺失时降级为浏览器语音朗读
- 音频与报告**同源生成**：每条 id（`h+hash(title)`）既是报告条目 id，也是音频文件名/清单 key；前端提取不到站内链接 id 时回退用 `it.id` 兜底匹配，确保第三方原链的热搜也能对上音频、正常出声

## 使用方法

**自动更新（已配置）**：`.github/workflows/daily-hotsearch.yml` 每天**早晚各一次**——早段北京 08:08 / 08:20 / 08:32，晚段 20:08 / 20:20 / 20:32。每段内 3 个错峰点配合"时段标记"幂等：同一时段成功一次后同段后续点自动跳过（失败重试保险），早晚两段互不干扰。工作流在抓数建站后按天幂等生成当日播客音频 + 重建 RSS（早晚段均可补，避免早段 cron 丢触发时错过）。也可在 Actions 页面手动触发，可选时段（am/pm）和 `force` 强制刷新。

**播客本机兜底**：GitHub 云端 `schedule` 高峰期常被延迟/丢弃，故配 WorkBuddy 本机定时任务每天 **08:35** 执行 `scripts/ensure_today.sh`——检查线上当日音频，缺失则补跑（必要时自采数据）并推送。推送优先 `git push`，本机代理不通时自动降级走 GitHub REST API（`scripts/push_via_api.py`）。参数（站点 URL、音色、兜底时间等）在 `site.config.json`。

**本地手动更新**：

```bash
bash 更新数据.sh
```

数据落盘在 `data/`（按日期累积成历史档案，日历可回看），`index.html` 为最终成品，双击即可本地查看；在线版见 https://anywise666.github.io/ai-hotsearch-dashboard/ 。

站点自包含：模板副本已随仓库提交在 `assets/`，任意机器（含 GitHub Actions 的 Linux 环境）都能独立重建，无需依赖本机技能目录。

## 文件结构

```
index.html              成品页面（单文件，自包含）
config.json             ★ 全站默认权重/阈值/配额/关键词（站主调参入口）
site.config.json        ★ 播客/站点参数（站点 URL、音色、保留天数、兜底时间等）
assets/dashboard-template.html  站点 HTML 模板（gen_site.py 据此生成 index.html）
feed.xml               RSS 订阅源（含每日 90 秒速览音频）
audio/<日期>/          每日播客音频 + manifest.json（按日累积，保留 30 天）
更新数据.sh             一键更新入口
.github/workflows/      早晚各一次的自动更新工作流
data/                   站点数据契约（index.json + 每日 <日期>.json + search-index.json 全局搜索索引，逐日累积成历史档案）
                        另有 .stamp-<日期>-<am|pm> 时段标记文件（幂等用）
assets/                 仪表盘模板副本（保证任意机器可独立重建）
scripts/                抓取、筛选、建站脚本
  fetch_hot.py / build_data.py / gen_site.py   ← 核心链路（双源回退 / 降级兜底 / 建站）
  common.py / gen_audio.py / gen_feed.py       ← 播客/RSS 生成（已启用，配置见 site.config.json）
  ensure_today.sh / push_via_api.py            ← 本机 08:35 兜底：补跑播客 + git/API 双通道推送
cron外部触发配置指南.md   外部精准定时（cron-job.org）配置参考，不依赖本机在线
raw/                    各平台原始快照（已 .gitignore，不入库）
```

## 已知限制

- 数据源为开源项目 [vikiboss/60s](https://github.com/vikiboss/60s) 的公共 API，对 GitHub Actions 共享出口 IP 做 **IP 级限流**（返回 429 / 错误码 1027）；已内置 **60s → DailyHotApi 双源回退** 与抓取失败降级。备用源域名在部分网络下 DNS 不可达，此时会快速跳过；若当日两源都失败，则**降级沿用最近一期有效报告**（内容非当天最新），但流程不再失败、音频照常重合成。
- GitHub 云端 `schedule` 不保证准点（高峰可能延迟数小时甚至丢弃）。本机 08:35 兜底任务仍是备份；也可按 `cron外部触发配置指南.md` 用外部精准定时器（cron-job.org）触发，不依赖本机在线。
- 热搜数据源为中文，无英文原题，故播客仅生成中文音轨（`manifest.json` 中 `en` 字段为空），与 AI 晨报站的中英双语不同。
- 摘要中偶见 `[N 张图片]` 等平台原始文本，属于数据自带内容，不影响使用。

## 与技能的关系

本项目是 [ai-brief-podcast](https://github.com/Anywise666/ai-brief-podcast-skill) 技能的落地实例：沿用了它的统一数据契约、`site.config.json` 参数化思路与 local 模式改造配方。如果说技能仓库是"方法论与模板"，本站就是一份可访问的在线演示。
