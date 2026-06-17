---
name: llm-risk-extract-analysis
description: Extract reusable risk fields, build a unified risk event table, and generate analysis CSVs for finance or medical industry projects.
---

# LLM Risk Extract Analysis

Use this skill after `regulation_cleaned.csv`, `news_cleaned.csv`, and `comment_cleaned.csv` exist.

## Reusable Layout

- Economy: `data/economy/processed/` and `data/economy/analysis/`.
- Medical: `data/medical/processed/` and `data/medical/analysis/`.
- The CLI may still accept `--industry finance`, but it maps to `economy`.

Run the three data-mining steps:

```bash
python src/llm_extract/extract_risk_fields.py --industry medical --fallback auto
python src/llm_extract/build_risk_event_table.py --industry medical
python src/analysis/run_analysis.py --industry medical
```

`--fallback auto` calls the configured LLM when an API key is available; otherwise it uses deterministic rule extraction. Use `--fallback llm` to require a model call, or `--fallback rule` for reproducible offline experiments.

## Output Contracts

`llm_extracted.csv`:

`entity_name,entity_type,region,risk_type,risk_level,sentiment,sentiment_score,violation_reason,impact_scope,summary,llm_confidence,record_id,source_type,url`

`risk_event_table.csv`:

`record_id,event_date,entity_name,entity_type,region,risk_type,risk_level,risk_score,sentiment,sentiment_score,violation_reason,impact_scope,penalty_amount,heat_score,summary,source_type,source,title,url,llm_confidence,manual_check`

Analysis outputs:

- `summary_stats.csv`
- `risk_type_stats.csv`
- `risk_time_trend.csv`
- `region_risk_stats.csv`
- `entity_risk_rank.csv`
- `sentiment_trend.csv`
- `risk_relation_matrix.csv`
- `risk_warning_cases.csv`

## Industry-Specific Parts

- Prompt templates live in `src/llm_extract/prompt_templates.py`.
- Medical risk taxonomy includes 医疗质量、药品安全、医疗器械、医保合规、价格收费、广告宣传、数据隐私、医患纠纷、经营管理、舆情等风险.
- Finance risk taxonomy stays separate in the finance prompt.

## Quality Gate

- `llm_extracted.csv` has one row per cleaned record unless model failures are intentionally recorded.
- `risk_event_table.csv` row count matches extracted rows.
- All 8 analysis CSVs are generated.
- Visualization is not part of this skill.
