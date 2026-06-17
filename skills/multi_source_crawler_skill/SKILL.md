---
name: multi-source-crawler
description: Build, run, and review reusable multi-source industry crawlers that collect raw CSV data for regulation, news, and public comments.
---

# Multi Source Crawler

Use this skill for raw data collection before cleaning, LLM extraction, risk scoring, analysis, or visualization.

## Reusable Layout

- Economy output: `data/economy/raw/*.csv`, logs in `outputs/economy/logs/`.
- Medical output: `data/medical/raw/*.csv`, logs in `outputs/medical/logs/`.
- The CLI may still accept `--industry finance`, but it maps to the `economy` directory.
- Keep industry-specific source selection in crawler modules or configs; keep raw field contracts shared.

## Medical Sources

Medical uses the same three source classes:

- Regulation: 卫健委处罚、市场监管处罚、药监处罚、信用中国处罚.
- News: 医疗健康新闻、医院管理新闻、医药监管新闻.
- Comments: 黑猫投诉、人民网健康评论、新闻评论、问政平台留言.

Run:

```bash
python src/crawler/crawl_medical.py
```

## Raw Field Contracts

Regulation:

`source,title,publish_time,decision_no,punished_entity,violation_text,penalty_text,penalty_amount_raw,agency,url,crawl_time`

News:

`source,title,publish_time,channel,content,url,crawl_time`

Comment:

`source,title,publish_time,stock_or_entity,content,read_count,comment_count,url,crawl_time`

## Quality Gate

- Raw CSVs exist and are UTF-8-sig or UTF-8 readable.
- Total effective records should be at least 1000 when required by the experiment.
- URLs are non-empty for retained records.
- Empty title plus empty body records are skipped.
- Logs and a handoff report record row counts, source strategy, failures, and known limitations.
- This stage must not generate cleaned files, LLM fields, risk scores, analysis tables, or visualizations.
