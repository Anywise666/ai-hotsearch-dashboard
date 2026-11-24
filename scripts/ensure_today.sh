#!/usr/bin/env bash
# 热搜播客「本机兜底主力」：检查线上当天音频是否存在，缺失则本地补跑并推送。
# 由 WorkBuddy 定时任务在目标上线时段调用（每天 08:35）。
# 事实源：线上 audio/YYYY-MM-DD/brief_zh.mp3 的 HTTP 状态。
# 数据：热搜站数据在 data/<date>.json（本地模式），缺失时先尝试 git pull 同步，
#       仍无则本地自采（更新数据.sh）。推送：git push 优先，失败降级 GitHub API。
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$WORK" || { echo "PUSH_FAILED 无法进入站点目录"; exit 1; }
# 用相对路径读取配置，避免 Git Bash 的 /d/... 路径传给 Windows Python 无法识别
SITE=$(python -c "import json; c=json.load(open('site.config.json',encoding='utf-8')); print(c.get('site_url','').rstrip('/'))")
if [ -z "$SITE" ]; then echo "PUSH_FAILED site_url 未配置"; exit 1; fi

TODAY=$(python -c "from datetime import datetime,timedelta,timezone; print(datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d'))")
CHECK_URL="$SITE/audio/$TODAY/brief_zh.mp3"
echo "=== 热搜播客兜底检查: $TODAY ==="
echo "检查线上音频: $CHECK_URL"

status=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 20 "$CHECK_URL" || echo "000")
echo "HTTP 状态: $status"
if [ "$status" = "200" ]; then
  echo "ALREADY_OK 当天音频已在线，无需补跑"
  exit 0
fi

echo "当天音频缺失，开始本地补跑 ..."

# 1) 确保当天数据存在：先 git pull 同步云端已抓取的数据，失败则本地自采
DATA_FILE="data/$TODAY.json"
data_ready() {
  [ -f "$DATA_FILE" ] && python -c "
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
r=d.get('report',d)
sys.exit(0 if (r.get('lead') or {}).get('title') and r.get('sections') else 1)
" "$DATA_FILE" >/dev/null 2>&1
}

if ! data_ready; then
  echo "本地无当天数据，尝试 git pull 同步 ..."
  for i in 1 2 3; do
    out=$(GIT_HTTP_VERSION=HTTP/1.1 git pull origin main 2>&1)
    echo "  pull try $i: $(echo "$out" | tail -1)"
    if data_ready; then break; fi
    sleep 3
  done
fi

if ! data_ready; then
  echo "云端数据未同步，尝试本地自采（更新数据.sh）..."
  bash "$WORK/更新数据.sh" || { echo "DATA_FETCH_FAILED 数据自采失败"; exit 1; }
fi
if ! data_ready; then echo "DATA_FETCH_FAILED 仍无有效数据"; exit 1; fi
echo "DATA_OK 当天数据就绪"

# 数据就绪后再等待数据源完整写入（防半写），最多重试 5 次 × 60s
for i in 1 2 3 4 5; do
  if data_ready; then break; fi
  echo "  数据未就绪，等待重试 $i/5 ..."; sleep 60
done

# 2) 生成音频 + feed
python "$SCRIPT_DIR/gen_audio.py" "$TODAY" || { echo "GEN_FAILED"; exit 1; }
python "$SCRIPT_DIR/gen_feed.py" || { echo "FEED_FAILED"; exit 1; }

# 3) 提交（含当天数据、页面、音频、feed）
git add "data/$TODAY.json" "data/index.json" "data/search-index.json" index.html "audio/$TODAY" feed.xml
if git diff --cached --quiet; then
  echo "NO_CHANGES_SKIP 生成后无变化"
  exit 0
fi
git commit -m "Fallback hotsearch podcast audio + feed: $TODAY (local)" >/dev/null 2>&1 || true

# 4) 推送：git push 优先（HTTP/1.1），失败降级 GitHub API
pushed=0
for i in 1 2 3; do
  out=$(GIT_HTTP_VERSION=HTTP/1.1 git push origin HEAD:main 2>&1)
  echo "  git push try $i: $(echo "$out" | tail -1)"
  if echo "$out" | grep -qE "up-to-date|HEAD -> main|main -> main"; then pushed=1; break; fi
done
if [ "$pushed" != "1" ]; then
  echo "git push 不通，降级 GitHub API 推送 ..."
  api_out=$(python "$SCRIPT_DIR/push_via_api.py" 2>&1)
  echo "  $api_out"
  if echo "$api_out" | grep -qE "PUSH_OK|NO_CHANGES"; then pushed=1; fi
fi
if [ "$pushed" != "1" ]; then echo "PUSH_FAILED 推送未成功"; exit 1; fi

# 5) 复核上线
for i in $(seq 1 15); do
  sleep 6
  s=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 15 "$CHECK_URL" || echo "000")
  echo "复核 $i: HTTP $s"
  if [ "$s" = "200" ]; then echo "PUSH_OK 当天音频已上线: $CHECK_URL"; exit 0; fi
done
echo "PUSH_OK_PENDING Pages 部署延迟，稍后请手动复核"
exit 0
