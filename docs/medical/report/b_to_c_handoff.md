# 医疗项目 B 到 C 交接文档

生成时间：2026-06-17

## 1. 交接范围

本次已完成：

- 多源文本数据采集
- 清洗与标准化
- 风险字段抽取
- 统一事件表构建
- 统计分析表生成

未完成：

- 可视化看板开发

C 角色可直接基于 `data/medical/processed/` 和 `data/medical/analysis/` 开发看板。

## 2. 目录结构

医疗项目目录：

- `data/medical/raw/`
- `data/medical/processed/`
- `data/medical/analysis/`
- `data/medical/logs/`
- `docs/medical/report/`

复用主逻辑代码：

- `src/pipeline_paths.py`
- `src/preprocess/`
- `src/llm_extract/`
- `src/analysis/`

医疗个性化代码：

- `src/crawler/crawl_medical.py`
- `src/crawler/crawl_medical_insurance.py`
- `src/crawler/crawl_medical_comment.py`
- `src/llm_extract/prompt_templates.py` 中的医疗提示词

## 3. 当前数据结果

### 3.1 raw 层

| 文件 | 条数 | 说明 |
|---|---:|---|
| `data/medical/raw/medical_insurance_raw.csv` | 313 | 医保监管公开网页数据 |
| `data/medical/raw/medical_news_raw.csv` | 801 | 医疗新闻公开网页数据 |
| `data/medical/raw/medical_comment_raw.csv` | 224 | 同站公开评论 / 网评 / 视评栏目 |

### 3.2 processed 层

| 文件 | 条数 | 说明 |
|---|---:|---|
| `data/medical/processed/regulation_cleaned.csv` | 313 | 监管类标准化结果 |
| `data/medical/processed/news_cleaned.csv` | 801 | 新闻标准化结果 |
| `data/medical/processed/comment_cleaned.csv` | 224 | 评论标准化结果 |
| `data/medical/processed/llm_extracted.csv` | 1338 | 风险字段抽取结果 |
| `data/medical/processed/risk_event_table.csv` | 1338 | 主事件表 |

### 3.3 analysis 层

已生成 8 张分析表：

- `summary_stats.csv`
- `risk_type_stats.csv`
- `risk_time_trend.csv`
- `region_risk_stats.csv`
- `entity_risk_rank.csv`
- `sentiment_trend.csv`
- `risk_relation_matrix.csv`
- `risk_warning_cases.csv`

关键汇总：

- 总事件数：`1338`
- 监管事件：`313`
- 新闻事件：`801`
- 评论事件：`224`
- 高风险事件：`83`

## 4. C 角色优先使用文件

### 4.1 主事实表

首选文件：

- `data/medical/processed/risk_event_table.csv`

关键字段：

- `record_id`
- `event_date`
- `entity_name`
- `entity_type`
- `region`
- `risk_type`
- `risk_level`
- `risk_score`
- `sentiment`
- `sentiment_score`
- `penalty_amount`
- `heat_score`
- `summary`
- `source_type`
- `source`
- `title`
- `url`
- `manual_check`

### 4.2 直接驱动图表的分析表

- 总览卡片：`summary_stats.csv`
- 风险类型图：`risk_type_stats.csv`
- 时间趋势图：`risk_time_trend.csv`
- 地区图：`region_risk_stats.csv`
- 主体排行：`entity_risk_rank.csv`
- 舆情趋势：`sentiment_trend.csv`
- 关系矩阵：`risk_relation_matrix.csv`
- 预警案例：`risk_warning_cases.csv`

## 5. 枚举值约定

`risk_event_table.csv` 中 `source_type` 固定为：

- `regulation`
- `news`
- `comment`

当前医疗项目中的 `risk_level` 使用英文枚举：

- `high`
- `medium`
- `low`

## 6. 运行命令

医疗采集：

```bash
python src/crawler/crawl_medical.py
python src/crawler/crawl_medical_insurance.py
python src/crawler/crawl_medical_comment.py
```

医疗清洗：

```bash
python src/preprocess/run_preprocess.py --industry medical
```

医疗数据挖掘：

```bash
python src/llm_extract/extract_risk_fields.py --industry medical --fallback rule
python src/llm_extract/build_risk_event_table.py --industry medical
python src/analysis/run_analysis.py --industry medical
```

## 7. 已知限制

- 当前评论数据来自新闻站点公开评论 / 网评 / 视评栏目，不是每篇医疗新闻详情页下的原生用户回帖。
- 部分事件仍存在 `entity_name = unknown_entity`，可视化时建议单独折叠或过滤。
- `risk_warning_cases.csv` 更适合做“预警案例卡片”，不适合直接当明细表替代主事件表。

## 8. 看板实现建议

- 主数据源优先读取 `risk_event_table.csv`
- 聚合图优先读取 `analysis/*.csv`
- 对 `unknown_entity` 做单独处理
- 在“数据说明”中注明评论源属于公开评论栏目
