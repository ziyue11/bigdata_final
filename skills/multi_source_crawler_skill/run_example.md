# multi_source_crawler_skill 运行示例

## 示例请求

请完成 A 阶段 raw 数据采集：采集 NFRA、CSRC、东方财富新闻、东方财富股吧数据，输出 `data/raw/*.csv`，并生成运行日志和 raw 数据质量说明。

## 推荐执行步骤

```powershell
python src/crawler/run_crawlers.py
```

## 验证命令

```powershell
python -X utf8 -c "import csv; from pathlib import Path; paths=['data/raw/regulation_nfra_raw.csv','data/raw/regulation_csrc_raw.csv','data/raw/news_raw.csv','data/raw/comment_raw.csv']; 
for p in paths:
    with open(p, encoding='utf-8-sig', newline='') as f:
        r=csv.DictReader(f); rows=list(r)
    print(p, len(rows), r.fieldnames)"
```

## 预期输出

- `data/raw/regulation_nfra_raw.csv`
- `data/raw/regulation_csrc_raw.csv`
- `data/raw/news_raw.csv`
- `data/raw/comment_raw.csv`
- `outputs/logs/crawler_run.log`

raw 阶段只保证数据可追溯和字段完整，不做风险类型、风险等级、情绪、统一事件表或可视化。
