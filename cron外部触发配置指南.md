# 热搜播客：外部精准定时（cron-job.org + GitHub Actions）

## 原理

GitHub 自带定时（`schedule`）高峰期常被延迟，导致音频晚到。本方案用一个**免费的外部闹钟**（cron-job.org）按时区精准触发本仓库的 Actions，执行仍在 GitHub 的免费机器上进行。

```
cron-job.org（准时闹钟，按北京时间）
   └─ HTTP POST → GitHub Actions API → daily-hotsearch.yml 立即运行
                                          └─ 抓热搜 → 建站 → 生成音频 → 推送 → Pages 上线
```

- 执行端：GitHub Actions（本仓库 public，分钟数免费不限量）——**无需改动任何 workflow 代码**，`workflow_dispatch` 已配置好。
- 幂等安全：workflow 内有"时段标记"检查，同一时段成功一次后同段后续点自动跳过。GitHub 自带定时与外部闹钟可**并存互为冗余**，不会重复生成/推送。

## 第 1 步：生成 GitHub 访问令牌（PAT）

1. 打开 https://github.com/settings/personal-access-tokens/new （需登录 GitHub）。
2. 按如下填写：
   - **Token name**：`hotsearch-cron`
   - **Expiration**：选 1 年（到期需更新，否则触发会静默停止）
   - **Repository access**：选 `Only select repositories` → 勾选 `Anywise666/ai-hotsearch-dashboard`
   - **Permissions → Repository permissions** → `Actions`: 设为 **Read and write**（其余保持默认）
3. 点 Generate token，**立即复制保存**（只显示一次）。形如 `github_pat_11A...`。

> 安全：该令牌只授权这一个仓库的 Actions 读写，泄露影响面很小。不要提交到代码里。

## 第 2 步：注册 cron-job.org

主域名 `cron-job.org` 在国内可能打不开，请直接用控制台域名：

- 注册：https://console.cron-job.org/en/signup/
- 登录：https://console.cron-job.org/en/signin/

（已实测可访问。免费账号够用。）

## 第 3 步：建两个定时任务

登录后 `Create cronjob`，早、晚各建一个。参数如下——**两个任务只有"标题"和"时间"不同，其余完全相同**。

### 通用参数（两个任务都填这些）

| 字段 | 值 |
|---|---|
| URL | `https://api.github.com/repos/Anywise666/ai-hotsearch-dashboard/actions/workflows/daily-hotsearch.yml/dispatches` |
| Request method | `POST` |
| Schedule → Time zone | `Asia/Shanghai`（北京时间） |
| Advanced → Request headers | 见下方 4 行，**每行一条** |

Headers（逐行添加）：

```
Accept: application/vnd.github+json
Authorization: Bearer github_pat_替换成你的令牌
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

Request body（JSON）：

```json
{"ref":"main","inputs":{"slot":"am"}}
```

> 说明：`slot` 告诉 workflow 这是早段还是晚段。早任务填 `am`，晚任务填 `pm`。workflow 靠时段标记去重，所以与 GitHub 自带定时并存不会重复推送。

### 任务 A：早段

| 字段 | 值 |
|---|---|
| Title | 热搜播客-早 |
| Schedule | 每天 `08:10`（Asia/Shanghai） |
| Request body | `{"ref":"main","inputs":{"slot":"am"}}` |

### 任务 B：晚段

| 字段 | 值 |
|---|---|
| Title | 热搜播客-晚 |
| Schedule | 每天 `20:10`（Asia/Shanghai） |
| Request body | `{"ref":"main","inputs":{"slot":"pm"}}` |

> 时间设为 08:10 / 20:10，比 GitHub 自带的 08:08/20:08 稍晚一点点作保险；即使两者都触发，幂等检查也只跑一次。若想彻底以外部闹钟为准，可把 GitHub 工作流里的 `schedule` 段删掉（可选，非必须）。

## 第 4 步：验证

1. 在每个任务上点 **Test run / Execute now**。
2. 打开 https://github.com/Anywise666/ai-hotsearch-dashboard/actions ，应看到由 `workflow_dispatch` 触发的新运行记录。
3. 若返回码是 `204` = 触发成功；`401` = 令牌问题；`404` = URL 或仓库权限问题。

快速自测（本机终端，把令牌替换掉）：

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer github_pat_替换成你的令牌" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","inputs":{"slot":"am"}}' \
  https://api.github.com/repos/Anywise666/ai-hotsearch-dashboard/actions/workflows/daily-hotsearch.yml/dispatches
```

## 备选：easycron

若 console.cron-job.org 也打不开，可用 https://www.easycron.com （已实测可访问），参数完全相同。免费版有调用次数限制，每天 2 次通常够用。

## 后续维护

- **令牌到期**：Expiration 到期后触发会静默失败，记得续期并更新两个任务里的 Authorization 头。
- **失败通知**：cron-job.org 可配置失败邮件通知，建议开启。
- **本机兜底**：现有的 WorkBuddy 08:35 本机兜底可保留作第三重保险，也可以停用（三者都靠"线上音频是否已存在"判断，互不冲突）。
