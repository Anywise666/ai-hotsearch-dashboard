#!/usr/bin/env bash
# 一键刷新热搜数据：抓取 → 筛选聚合 → 重建页面
# 用法：bash 更新数据.sh
set -e
cd "$(dirname "$0")"
echo "① 抓取多平台实时热搜（含百度 /v2/baidu/hot）..."
python scripts/fetch_hot.py
echo "② 筛选聚合 → 数据契约（索引自动累加历史日期）..."
python scripts/build_data.py
echo "③ 重建单文件页面..."
python scripts/gen_site.py
echo "✅ 完成。刷新浏览器即可看到最新热搜。"
