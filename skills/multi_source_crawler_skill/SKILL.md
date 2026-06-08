---
name: multi-source-crawler
description: Build, run, and review multi-source financial risk crawlers that collect raw CSV data for regulatory penalties, financial news, and investor comments. Use when a project needs A-stage data acquisition, crawler source selection, raw field contracts, crawl logs, manual review notes, or reproducible data collection into data/raw/*.csv.
---

# Multi Source Crawler

Use this skill for A-stage raw data collection before any cleaning, LLM extraction, risk scoring, analysis, or visualization.

## Scope

Produce raw CSV files only:

- `data/raw/regulation_nfra_raw.csv`
- `data/raw/regulation_csrc_raw.csv`
- `data/raw/news_raw.csv`
- `data/raw/comment_raw.csv`

Do not generate processed CSVs, `risk_event_table.csv`, risk labels, sentiment, charts, or analysis tables.

## Workflow

1. Confirm sources and field contracts.
   - Prefer stable public pages or public JSON endpoints.
   - Keep 2-4 reliable sources if a site is unstable.
   - Record source URLs, source choice rationale, crawl strategy, and known limitations.

2. Implement source-specific crawler modules.
   - Put crawlers under `src/crawler/`.
   - Keep one source per file when possible.
   - Add a `run_crawlers.py` entrypoint that creates `data/raw/` and writes all raw CSVs.

3. Preserve raw semantics.
   - Save source-provided fields with minimal parsing.
   - Keep `crawl_time` for traceability.
   - Do not normalize dates beyond what is needed to store source values.
   - Do not infer risk type, risk level, sentiment, or final entity fields.

4. Validate raw output.
   - Check row counts, exact columns, non-empty title/url rates, duplicate counts, and failed/skipped pages.
   - Open several rows from each source and inspect title, text, URL, and time fields.
   - Write run logs under `outputs/logs/`.

5. Write handoff notes.
   - Explain source websites, fields, strategy, row counts, and problems.
   - Make clear that raw files are the input to preprocessing, not B-stage LLM extraction.

## Raw Field Contracts

### NFRA regulation

`source,title,publish_time,decision_no,punished_entity,violation_text,penalty_text,penalty_amount_raw,agency,url,crawl_time`

### CSRC regulation

`source,title,publish_time,party,violation_text,penalty_text,penalty_amount_raw,market_ban_raw,url,crawl_time`

### News

`source,title,publish_time,channel,content,url,crawl_time`

### Comment

`source,title,publish_time,stock_or_entity,content,read_count,comment_count,url,crawl_time`

## Quality Gate

Before handing off:

- All required raw CSVs exist and use UTF-8-sig or UTF-8 readable encoding.
- Total effective records should be at least 1000 when source availability allows.
- URLs are non-empty for retained records.
- Empty title plus empty body records are removed or marked as skipped.
- `run_crawlers.py` can reproduce the raw files.
- Logs capture start time, end time, output paths, row counts, and errors.

## Report Checklist

Include:

- Source website links.
- Data source type and selection reason.
- Crawled fields and row counts.
- Whether each source succeeded.
- Failed/skipped page counts.
- Known anti-crawl or dynamic rendering issues.
- Statement that no processed data, LLM extraction, scoring, or visualization was done in this stage.
