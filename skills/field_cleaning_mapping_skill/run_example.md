# field_cleaning_mapping_skill 运行示例

## 示例请求

请完成 A 阶段 raw 数据清洗和字段标准化：读取 `data/raw/*.csv`，输出三个 `data/processed/*_cleaned.csv`，并生成日志和交接说明。

## 推荐执行步骤

```powershell
python src/preprocess/run_preprocess.py
```

## 验证命令

```powershell
python -X utf8 -c "import csv; checks={
 'data/processed/regulation_cleaned.csv':['record_id','source_type','source','title','event_date','entity_name','raw_text','penalty_amount','agency','region','url'],
 'data/processed/news_cleaned.csv':['record_id','source_type','source','title','event_date','content','mentioned_entity','channel','url'],
 'data/processed/comment_cleaned.csv':['record_id','source_type','source','title','event_date','content','mentioned_entity','read_count','comment_count','url']};
for p, expected in checks.items():
    with open(p, encoding='utf-8-sig', newline='') as f:
        r=csv.DictReader(f); rows=list(r)
    print(p, r.fieldnames == expected, len(rows))"
```

## 预期输出

- `data/processed/regulation_cleaned.csv`
- `data/processed/news_cleaned.csv`
- `data/processed/comment_cleaned.csv`
- `outputs/logs/preprocess_run.log`

本阶段不生成 `risk_event_table.csv`，不生成风险类型、风险等级、情绪或风险评分字段。
