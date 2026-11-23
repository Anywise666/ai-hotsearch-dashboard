#!/usr/bin/env bash
# 一键刷新热搜数据：抓取 → 筛选聚合 → 重建页面
# 用法：bash 更新数据.sh
set -e
cd "$(dirname "$0")"
echo "① 抓取 5 平台实时热搜..."
python scripts/fetch_hot.py || true
echo "② 补抓百度热搜..."
curl -s -m 25 "https://60s.viki.moe/v2/baidu/hot" -o raw/baidu_raw.json
python -c "
import json
d=json.load(open('raw/baidu_raw.json',encoding='utf-8'))
if d.get('code')==200 and d.get('data'):
    json.dump({'platform':'baidu','fetched_at':d.get('message',''),'data':d['data']},open('raw/baidu.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print('  百度',len(d['data']),'条')
import os
os.path.exists('raw/baidu_raw.json') and os.remove('raw/baidu_raw.json')
"
echo "③ 筛选聚合 → 数据契约..."
python scripts/build_data.py
echo "④ 重建单文件页面..."
python scripts/gen_site.py
echo "✅ 完成。刷新浏览器即可看到最新热搜。"
