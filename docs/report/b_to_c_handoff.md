# B 到 C 阶段交接说明

生成时间：2026-06-13

本文档由 B 角色编写，交接对象为 C 角色。B 阶段已完成三类 cleaned 数据的 LLM 风险字段抽取、统一风险事件表构建、风险评分、统计分析表生成和人工抽样审核。C 阶段只需要读取本文列出的 `data/processed/risk_event_table.csv` 与 `data/analysis/*.csv`，用于交互式风险预警看板展示。

## 一、B 阶段完成内容

B 阶段已完成：

1. 读取 A 阶段交付的三张 cleaned 表：
   - `data/processed/regulation_cleaned.csv`
   - `data/processed/news_cleaned.csv`
   - `data/processed/comment_cleaned.csv`
2. 对三类文本统一进行 LLM 风险字段抽取。
3. 构建统一风险事件表 `data/processed/risk_event_table.csv`。
4. 基于统一事件表生成 8 张分析结果表，供 C 看板直接使用。
5. 生成 50 条人工审核样本 `docs/manual_review/manual_review.csv`。

B 阶段不负责：

1. 修改 A 阶段 raw/cleaned 数据。
2. 重新爬取网页。
3. 开发 Streamlit 页面布局。
4. 替 C 手工调整图表样式。

## 二、核心数据概况

### 统一事件表

| 文件 | 行数 | 说明 |
|---|---:|---|
| `data/processed/risk_event_table.csv` | 1526 | 三源统一风险事件明细表 |

来源分布：

| source_type | 行数 | 含义 |
|---|---:|---|
| `regulation` | 226 | 监管处罚与行政处罚公告 |
| `news` | 200 | 财经新闻 |
| `comment` | 1100 | 股吧/投资者评论 |

时间范围：

| 字段 | 最小值 | 最大值 |
|---|---|---|
| `event_date` | 2024-05-23 | 2026-06-08 |

总览指标：

| 指标 | 数值 |
|---|---:|
| total_events | 1526 |
| regulation_events | 226 |
| news_events | 200 |
| comment_events | 1100 |
| high_risk_events | 61 |
| total_penalty_amount | 398553.094 |
| negative_sentiment_ratio | 0.8945 |

## 三、C 阶段主要输入文件

C 需要读取以下文件：

| 文件 | 行数 | 用途 |
|---|---:|---|
| `data/processed/risk_event_table.csv` | 1526 | 明细表、筛选联动、动态指标、风险评分分布 |
| `data/analysis/summary_stats.csv` | 7 | 顶部总览指标 |
| `data/analysis/risk_type_stats.csv` | 10 | 风险类型分布图 |
| `data/analysis/risk_time_trend.csv` | 21 | 时间趋势图 |
| `data/analysis/region_risk_stats.csv` | 27 | 地区风险排行 |
| `data/analysis/entity_risk_rank.csv` | 396 | 主体风险排行 |
| `data/analysis/sentiment_trend.csv` | 21 | 舆情趋势图 |
| `data/analysis/risk_relation_matrix.csv` | 42 | 主体类型-风险类型热力图 |
| `data/analysis/risk_warning_cases.csv` | 5 | 典型预警案例 |

辅助材料：

| 文件 | 行数 | 用途 |
|---|---:|---|
| `docs/manual_review/manual_review.csv` | 50 | 报告/PPT 中说明 LLM 抽取结果已做人工抽样审核 |

## 四、统一风险事件表字段说明

`data/processed/risk_event_table.csv` 字段如下：

`record_id,event_date,entity_name,entity_type,region,risk_type,risk_level,risk_score,sentiment,sentiment_score,violation_reason,impact_scope,penalty_amount,heat_score,summary,source_type,source,title,url,llm_confidence,manual_check`

| 字段 | 含义 | C 使用建议 |
|---|---|---|
| `record_id` | 原始记录 ID，保留 A 阶段编号 | 可作为事件唯一标识 |
| `event_date` | 事件日期，格式为 `YYYY-MM-DD` | 时间筛选、趋势图 |
| `entity_name` | LLM 抽取的风险主体 | 明细表、主体排行、关键词搜索 |
| `entity_type` | 主体类型 | 主体类型筛选、关系热力图 |
| `region` | 地区 | 地区筛选、地区排行 |
| `risk_type` | 风险类型 | 风险类型筛选、柱状图 |
| `risk_level` | 风险等级：高/中/低 | 风险等级筛选、颜色编码 |
| `risk_score` | 0-100 风险分 | 排序、Top N、分布图 |
| `sentiment` | 情绪倾向：正面/中性/负面 | 舆情筛选、负面比例 |
| `sentiment_score` | 情绪分，范围约为 -1 到 1 | 舆情趋势图 |
| `violation_reason` | 违规原因或核心风险点 | 明细表、案例说明 |
| `impact_scope` | 影响范围 | 明细表、报告文字说明 |
| `penalty_amount` | 处罚金额，单位万元；新闻/评论为 0 | 金额指标、处罚金额排行 |
| `heat_score` | 热度分 | 风险评分解释、评论热度辅助指标 |
| `summary` | 事件摘要 | 明细表、典型案例 |
| `source_type` | 数据来源类型：`regulation/news/comment` | 必须作为来源筛选口径 |
| `source` | 来源网站或机构 | 明细表来源列 |
| `title` | 原始标题 | 明细表、搜索 |
| `url` | 原文链接 | 明细表跳转 |
| `llm_confidence` | LLM 置信度 | 可选展示，不建议作为主筛选项 |
| `manual_check` | 人工审核状态 | 默认用于审核流程说明 |

## 五、风险类型与来源口径

### 风险类型

`risk_type` 固定在以下 10 类中：

```text
合规风险
信贷风险
信息披露风险
内部控制风险
市场操纵风险
消费者权益风险
经营风险
流动性风险
舆情风险
其他风险
```

### 来源类型

C 看板筛选器请使用以下英文值，不要使用中文别名过滤：

```text
regulation
news
comment
```

显示时可以映射为：

| source_type | 展示名 |
|---|---|
| `regulation` | 监管处罚 |
| `news` | 财经新闻 |
| `comment` | 投资者评论 |

## 六、分析结果表字段说明

### 1. `summary_stats.csv`

字段：

`metric,value`

包含指标：

| metric | 含义 |
|---|---|
| `total_events` | 总风险事件数 |
| `regulation_events` | 监管处罚事件数 |
| `news_events` | 新闻事件数 |
| `comment_events` | 评论事件数 |
| `high_risk_events` | 高风险事件数 |
| `total_penalty_amount` | 总处罚金额，单位万元 |
| `negative_sentiment_ratio` | 负面情绪占比 |

### 2. `risk_type_stats.csv`

字段：

`risk_type,event_count,total_penalty_amount,avg_risk_score,high_risk_count`

用于展示不同风险类型的事件数量、处罚金额、平均风险分和高风险数量。

### 3. `risk_time_trend.csv`

字段：

`month,regulation_count,news_count,comment_count,high_risk_count,total_penalty_amount,avg_risk_score`

用于折线图或双轴图。当前共有 21 个月份，可支撑趋势展示。

### 4. `region_risk_stats.csv`

字段：

`region,event_count,total_penalty_amount,high_risk_count,avg_risk_score`

用于地区风险排行。建议过滤或弱化 `未知` 地区，以免影响展示效果。

### 5. `entity_risk_rank.csv`

字段：

`entity_name,entity_type,region,event_count,total_penalty_amount,avg_risk_score,risk_level`

用于主体 Top N 排行。建议默认按 `avg_risk_score` 或 `event_count` 排序，并允许切换排序指标。

### 6. `sentiment_trend.csv`

字段：

`month,negative_news_count,negative_comment_count,negative_ratio,avg_sentiment_score`

用于舆情趋势图。注意该表只统计 news/comment 中负面事件，监管处罚不计入负面新闻或负面评论数量。

### 7. `risk_relation_matrix.csv`

字段：

`entity_type,risk_type,event_count,avg_risk_score`

用于主体类型-风险类型热力图。

### 8. `risk_warning_cases.csv`

字段：

`entity_name,warning_reason,evidence_sources,risk_score,suggested_action`

用于典型预警案例展示。建议作为页面下方案例区，不替代主图表。

## 七、风险评分规则说明

B 阶段使用可解释规则计算 `risk_score`，范围限制在 0-100。

公式口径：

```text
risk_score = 基础分 + 风险等级分 + 处罚金额分 + 负面情绪分 + 热度分 + 重复出现分
```

其中：

| 分项 | 含义 |
|---|---|
| 基础分 | 每条事件固定基础风险 |
| 风险等级分 | 高/中/低分别对应不同加分 |
| 处罚金额分 | 监管处罚按 `penalty_amount` 计算，新闻和评论为 0 |
| 负面情绪分 | `sentiment=负面` 时按 `sentiment_score` 加权 |
| 热度分 | 新闻给固定热度，评论根据阅读数/评论数折算，监管处罚较低 |
| 重复出现分 | 同一主体多次出现时增加风险分 |

C 展示时可以说明该分数是课程实验中的可解释综合评分，不是金融投资建议。

## 八、人工审核说明

B 已生成：

`docs/manual_review/manual_review.csv`

字段：

`record_id,entity_name,risk_type,risk_level,sentiment,summary,is_correct,manual_correction`

说明：

1. 随机抽取 50 条 LLM 抽取结果用于人工审核。
2. 审核重点包括主体识别、风险类型、风险等级、情绪倾向和摘要合理性。
3. C 可在报告/PPT 中引用“B 阶段已对 LLM 抽取结果进行 50 条人工抽样审核”。

## 九、C 看板实现建议

建议 C 的看板优先基于 `risk_event_table.csv` 做动态筛选，再用 `analysis/*.csv` 做全局视图。

必须保留的筛选器：

1. 时间范围：`event_date`
2. 来源类型：`source_type`
3. 风险类型：`risk_type`
4. 风险等级：`risk_level`
5. 地区：`region`
6. 主体类型：`entity_type`
7. 关键词：`entity_name/title/summary/violation_reason`

建议展示模块：

1. 顶部指标卡：总事件数、高风险事件数、总处罚金额、负面情绪占比。
2. 时间趋势：读取 `risk_time_trend.csv` 或对筛选后的 `risk_event_table.csv` 动态聚合。
3. 风险类型分布：读取 `risk_type_stats.csv`。
4. 地区排行：读取 `region_risk_stats.csv`。
5. 主体排行：读取 `entity_risk_rank.csv`。
6. 舆情趋势：读取 `sentiment_trend.csv`。
7. 主体类型-风险类型热力图：读取 `risk_relation_matrix.csv`。
8. 事件明细表：直接读取 `risk_event_table.csv`，并保留 `url` 跳转。

## 十、已知注意事项

1. `source_type` 使用英文值，C 过滤时不要写成 `监管处罚/新闻舆情/评论`。
2. `penalty_amount` 单位为万元；新闻和评论没有处罚金额，统一为 0。
3. 评论数据中部分 `entity_name` 可能为“未知”或泛化主体，这是短文本舆情的正常限制。
4. `REG_000210` 为超长处罚决定书，B 阶段根据原文做了人工兜底结构化记录，`llm_confidence=0.8`。
5. `risk_score` 是课程实验中的综合风险分，不代表真实金融投资建议。
6. 若 C 做动态筛选后的顶部指标，建议直接从筛选后的 `risk_event_table.csv` 重新计算，而不是固定使用 `summary_stats.csv`。

## 十一、交接结论

B 阶段已完成三源 cleaned 数据到统一风险事件表和分析表的转换。C 阶段可以直接基于以下两类数据开发交互式风险预警看板：

```text
data/processed/risk_event_table.csv
data/analysis/*.csv
```

当前数据已经覆盖监管处罚、财经新闻、投资者评论三类来源，共 1526 条事件，能够支撑多维筛选、趋势展示、地区和主体排行、风险类型结构分析、舆情联动和事件明细溯源。
