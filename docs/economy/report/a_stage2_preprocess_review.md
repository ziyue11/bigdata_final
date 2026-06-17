# economy raw 数据清洗与字段标准化说明

生成时间：2026-06-16 22:20:03

本阶段只完成 raw 数据清洗、字段标准化、去重和基础质量统计；未做 LLM 抽取、风险评分、统计分析或可视化。

## 输入输出

- 输入目录：`C:\Users\ziyue\Desktop\bupt\大三下\大数据技术基础\期末实验\bigdata_final\data\economy\raw`
- 输出目录：`C:\Users\ziyue\Desktop\bupt\大三下\大数据技术基础\期末实验\bigdata_final\data\economy\processed`
- 日志文件：`C:\Users\ziyue\Desktop\bupt\大三下\大数据技术基础\期末实验\bigdata_final\outputs\economy\logs\preprocess_run.log`

## 质量统计

| processed CSV | 行数 | 字段 | event_date 非空率 | url 非空率 | raw_text/content 非空率 | entity 非空率 | 金额解析数 | 去重删除 | 无效删除 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| regulation_cleaned.csv | 226 | record_id, source_type, source, title, event_date, entity_name, raw_text, penalty_amount, agency, region, url | 100.00% | 100.00% | 100.00% | 94.25% | 210 | 74 | 0 |
| news_cleaned.csv | 200 | record_id, source_type, source, title, event_date, content, mentioned_entity, channel, url | 100.00% | 100.00% | 100.00% | 0.00% |  | 0 | 0 |
| comment_cleaned.csv | 1100 | record_id, source_type, source, title, event_date, content, mentioned_entity, read_count, comment_count, url | 100.00% | 100.00% | 100.00% | 100.00% |  | 0 | 0 |

## 交接说明

- `regulation_cleaned.csv` 的主文本字段是 `raw_text`。
- `news_cleaned.csv` 和 `comment_cleaned.csv` 的主文本字段是 `content`。
- `entity_name`、`mentioned_entity`、`region` 是规则粗抽取，后续 LLM 阶段需要修正。
