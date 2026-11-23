# 全网有价值热搜聚合仪表盘

聚合微博、知乎、抖音、今日头条、百度五个公共平台的实时热搜，按"公共价值"筛选去重后，呈现为与 AI 晨报同风格的单文件仪表盘。

> 本项目由 [ai-brief-podcast 技能](https://github.com/Anywise666/ai-brief-podcast-skill) 构建，视觉风格对齐 [ai-news-dashboard](https://github.com/Anywise666/ai-news-dashboard)。技能的定位是"把每日简报变成可看、可听、可订阅的站点"，本项目是这套方法论在**热搜聚合**场景的第一次落地验证。

## 它解决什么问题

公共平台热搜信息密度低、娱乐八卦与广告占比高。本项目不追求"全"，而是从 200+ 条原始热搜里筛出约 40 条**真正有公共价值**的条目——科技、财经、社会民生、国际、科学体育，并按跨平台共振度识别真正的重大事件。

## 数据链路

```
60s API (5 平台)  →  fetch_hot.py  →  build_data.py  →  gen_site.py  →  index.html
   实时热搜            raw/*.json        data/*.json        单文件站点
```

| 环节 | 脚本 | 作用 |
|---|---|---|
| 抓取 | `scripts/fetch_hot.py` | 调用 60s API 拉取各平台热搜，带重试与延时规避限流（错误码 1015） |
| 筛选聚合 | `scripts/build_data.py` | 价值打分 → 语义去重 → 板块配额 → 生成符合技能数据契约的 `data/<日期>.json` |
| 建站 | `scripts/gen_site.py` | 基于技能模板，以 local 模式替换 `SITE_CFG` 生成 `index.html` |
| 一键更新 | `更新数据.sh` | 串联以上三步，每天跑一次即可刷新站点 |

## 筛选逻辑（"有价值"的定义）

所有权重、阈值、配额、关键词表都集中在根目录 **`config.json`**，可手动调节。

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
- 全局搜索、收藏/稍后读、已读标记、分享卡片
- 今日头条 + 5 板块全局编号，每条带来源平台、摘要与热度
- 90 秒速览（播客按钮在 local 模式下自动降级为浏览器语音朗读）

## 使用方法

**自动更新（已配置）**：`.github/workflows/daily-hotsearch.yml` 每天**早晚各一次**——早段北京 08:08 / 08:20 / 08:32，晚段 20:08 / 20:20 / 20:32。每段内 3 个错峰点配合"时段标记"幂等：同一时段成功一次后同段后续点自动跳过（失败重试保险），早晚两段互不干扰。也可在 Actions 页面手动触发，可选时段（am/pm）和 `force` 强制刷新。

**本地手动更新**：

```bash
bash 更新数据.sh
```

数据落盘在 `data/`（按日期累积成历史档案，日历可回看），`index.html` 为最终成品，双击即可本地查看；在线版见 https://anywise666.github.io/ai-hotsearch-dashboard/ 。

站点自包含：模板副本已随仓库提交在 `assets/`，任意机器（含 GitHub Actions 的 Linux 环境）都能独立重建，无需依赖本机技能目录。

## 文件结构

```
index.html              成品页面（单文件，自包含）
config.json             ★ 权重/阈值/配额/关键词 手动调参入口
更新数据.sh             一键更新入口
.github/workflows/      早晚各一次的自动更新工作流
data/                   站点数据契约（index.json + 每日 <日期>.json，逐日累积成历史档案）
                        另有 .stamp-<日期>-<am|pm> 时段标记文件（幂等用）
assets/                 仪表盘模板副本（保证任意机器可独立重建）
scripts/                抓取、筛选、建站脚本
  fetch_hot.py / build_data.py / gen_site.py   ← 核心链路
  common.py / gen_audio.py / gen_feed.py / ensure_today.sh
                                              ← 技能模板附带的播客/RSS 组件，为未来升级预留
raw/                    各平台原始快照（已 .gitignore，不入库）
```

## 已知限制

- 数据源为开源项目 [vikiboss/60s](https://github.com/vikiboss/60s) 的公共 API，存在短时限流；B 站端点在首次抓取时上游异常，当前用 5 个平台（B 站恢复后可在 `fetch_hot.py` 的 `PLATFORMS` 中启用）。
- 本地站数据不会自动刷新，需手动运行更新脚本；如需每日自动更新，可按技能的"可订阅站"档位配置 GitHub Actions 定时抓取推送。
- 摘要中偶见 `[N 张图片]` 等平台原始文本，属于数据自带内容，不影响使用。

## 与技能的关系

本项目是 [ai-brief-podcast](https://github.com/Anywise666/ai-brief-podcast-skill) 技能的落地实例：沿用了它的统一数据契约、`site.config.json` 参数化思路与 local 模式改造配方。如果说技能仓库是"方法论与模板"，本站就是一份可访问的在线演示。
