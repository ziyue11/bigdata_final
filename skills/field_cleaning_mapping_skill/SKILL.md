---
name: field-cleaning-mapping
description: Clean reusable regulation/news/comment raw CSVs and standardize fields for finance or medical industry pipelines.
---

# Field Cleaning Mapping

Use this skill after raw crawler output has passed review.

## Reusable Layout

- Economy input/output: `data/economy/raw/` -> `data/economy/processed/`.
- Medical input/output: `data/medical/raw/` -> `data/medical/processed/`.
- The CLI may still accept `--industry finance`, but it maps to `economy`.

Run:

```bash
python src/preprocess/run_preprocess.py --industry finance
python src/preprocess/run_preprocess.py --industry medical
```

## Scope

Read the current industry raw files:

- economy: `regulation_*_raw.csv`, `news_raw.csv`, `comment_raw.csv`
- medical: `medical_*_raw.csv`

Write:

- `regulation_cleaned.csv`
- `news_cleaned.csv`
- `comment_cleaned.csv`
- `outputs/<industry>/logs/preprocess_run.log`

Do not call LLMs, classify risk, score risk, analyze data, or visualize data.

## Processed Field Contracts

Regulation:

`record_id,source_type,source,title,event_date,entity_name,raw_text,penalty_amount,agency,region,url`

News:

`record_id,source_type,source,title,event_date,content,mentioned_entity,channel,url`

Comment:

`record_id,source_type,source,title,event_date,content,mentioned_entity,read_count,comment_count,url`

## Shared Rules

- Normalize dates to `YYYY-MM-DD`.
- Remove HTML, duplicate whitespace, and repeated line breaks.
- Parse penalty amount into numeric 万元 when possible; otherwise use `0`.
- Use conservative rule-based entity and region extraction.
- Regulation de-dup key: `source + title + url`.
- News/comment de-dup key: `title + url`.
- Remove records only when URL is empty, title and body are both empty, or text is obvious navigation/footer/disclaimer.
- Keep missing values and report non-empty rates.
- Entity and region are A-stage helpers; LLM extraction may revise them.

## Quality Gate

- `run_preprocess.py --industry <name>` completes without error.
- Output columns exactly match the contracts.
- No `risk_type`, `risk_level`, `sentiment`, or `risk_score` columns are created.
- Report states primary text fields:
  - regulation: `raw_text`
  - news: `content`
  - comment: `content`
