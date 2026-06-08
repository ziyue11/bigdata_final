---
name: field-cleaning-mapping
description: Clean raw financial risk CSVs and standardize fields for A-stage preprocessing. Use when raw regulation, news, or comment CSVs need date normalization, text cleaning, de-duplication, penalty amount parsing, conservative entity/region extraction, quality statistics, preprocess logs, and processed outputs under data/processed/*_cleaned.csv.
---

# Field Cleaning Mapping

Use this skill for A-stage single-source cleaning and field standardization after raw crawler output has passed manual review.

## Scope

Read:

- `data/raw/regulation_nfra_raw.csv`
- `data/raw/regulation_csrc_raw.csv`
- `data/raw/news_raw.csv`
- `data/raw/comment_raw.csv`

Write:

- `data/processed/regulation_cleaned.csv`
- `data/processed/news_cleaned.csv`
- `data/processed/comment_cleaned.csv`
- `outputs/logs/preprocess_run.log`

Do not call LLMs, generate `risk_event_table.csv`, classify risk, score risk, judge sentiment, analyze data, or visualize data.

## Workflow

1. Inspect raw CSV headers and samples.
   - Do not assume column names.
   - Confirm raw fields match the contracts before coding.

2. Implement or update preprocess modules.
   - `src/preprocess/clean_regulation.py`
   - `src/preprocess/clean_news.py`
   - `src/preprocess/clean_comment.py`
   - `src/preprocess/run_preprocess.py`

3. Apply deterministic cleaning only.
   - Normalize dates to `YYYY-MM-DD`.
   - Remove HTML, duplicate whitespace, and repeated line breaks.
   - Parse penalty amount into numeric 万元.
   - Use conservative rule-based entity and region extraction.
   - Preserve missing values unless the record is clearly invalid.

4. Validate output.
   - Check exact field names and order.
   - Check UTF-8-sig encoding.
   - Check row counts, non-empty rates, duplicate removal, invalid removal, and penalty parse count.
   - Confirm no B-stage fields were created.

5. Write handoff documentation.
   - Explain input/output files, field mapping, cleaning rules, data quality statistics, and B-stage caveats.

## Processed Field Contracts

### regulation_cleaned.csv

`record_id,source_type,source,title,event_date,entity_name,raw_text,penalty_amount,agency,region,url`

Rules:

- `record_id`: `REG_000001` stable sequence.
- `source_type`: fixed `regulation`.
- `source`: preserve source such as `NFRA` or `CSRC`.
- `event_date`: normalize `publish_time`.
- `entity_name`: NFRA uses `punished_entity`; CSRC uses `party`; if empty, conservatively extract from title/text.
- `raw_text`: NFRA merges `violation_text + penalty_text`; CSRC uses `violation_text` and may merge `penalty_text`.
- `penalty_amount`: parse from `penalty_amount_raw`, `penalty_text`, `violation_text`; unit is 万元; unparsed value is `0` or empty, but document the choice.
- `agency`: NFRA uses `agency`; CSRC defaults to `中国证监会` when missing.
- `region`: rough province/city keyword extraction from agency/title/text.

### news_cleaned.csv

`record_id,source_type,source,title,event_date,content,mentioned_entity,channel,url`

Rules:

- `record_id`: `NEWS_000001` stable sequence.
- `source_type`: fixed `news`.
- `content`: cleaned body text.
- `mentioned_entity`: conservative suffix-based institution/company extraction; empty is allowed.

### comment_cleaned.csv

`record_id,source_type,source,title,event_date,content,mentioned_entity,read_count,comment_count,url`

Rules:

- `record_id`: `COMM_000001` stable sequence.
- `source_type`: fixed `comment`.
- `content`: prefer `content`; use `title` when content is empty.
- `mentioned_entity`: prefer `stock_or_entity`; otherwise conservative extraction.
- `read_count` and `comment_count`: numeric, unparsed value is `0`.

## Shared Cleaning Rules

- CSV output must use UTF-8-sig.
- Date output must be `YYYY-MM-DD`; fill year from `crawl_time` for comment dates like `06-08 10:36`.
- Regulation de-dup key: `source + title + url`.
- News de-dup key: `title + url`.
- Comment de-dup key: `title + url`.
- Remove records only when url is empty, title and body are both empty, or the body is obviously navigation/footer/disclaimer text.
- Keep missing values and report missing/non-empty rates.
- Entity and region extraction are rough A-stage helpers; B-stage LLM must revise them.

## Quality Gate

Before handoff:

- `run_preprocess.py` completes without error.
- Output columns exactly match the contracts above.
- No columns named `risk_type`, `risk_level`, `sentiment`, or `risk_score` exist.
- `outputs/logs/preprocess_run.log` contains row counts and removal counts.
- A handoff document tells B which text field is primary:
  - regulation: `raw_text`
  - news: `content`
  - comment: `content`
