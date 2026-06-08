# A 到 B 阶段交接说明

生成时间：2026-06-08

本文档汇总 A 角色已完成的数据采集、人工审核、raw 清洗与字段标准化结果，供 B 阶段进行 LLM 抽取、主体修正、风险类型判断、情绪判断和后续事件表构建使用。

## 一、A 阶段已完成内容

A 阶段已完成以下工作：

1. 采集并人工审核 raw 数据。
2. 对 raw 数据进行单源清洗、字段标准化、日期标准化、文本清洗、去重和基础质量统计。
3. 生成 B 阶段可直接读取的 processed CSV。

A 阶段未做以下工作：

1. 未调用 LLM。
2. 未生成 `risk_event_table.csv`。
3. 未做主观风险分类、风险评分、情绪判断。
4. 未做数据分析和可视化。

## 二、B 阶段输入文件

| 文件 | 行数 | 说明 |
|---|---:|---|
| `data/processed/regulation_cleaned.csv` | 226 | 监管处罚清洗表，合并 NFRA 与 CSRC 数据 |
| `data/processed/news_cleaned.csv` | 200 | 财经新闻清洗表 |
| `data/processed/comment_cleaned.csv` | 1100 | 股吧评论清洗表 |

原始 raw 文件仍保留在 `data/raw/`，如需追溯可读取：

| 文件 | raw 行数 | 说明 |
|---|---:|---|
| `data/raw/regulation_nfra_raw.csv` | 150 | NFRA 行政处罚 raw 数据 |
| `data/raw/regulation_csrc_raw.csv` | 150 | CSRC 行政处罚 raw 数据 |
| `data/raw/news_raw.csv` | 200 | 财经新闻 raw 数据 |
| `data/raw/comment_raw.csv` | 1100 | 股吧评论 raw 数据 |

## 三、processed 字段说明

### regulation_cleaned.csv

字段固定为：

`record_id,source_type,source,title,event_date,entity_name,raw_text,penalty_amount,agency,region,url`

| 字段 | 说明 | B 阶段使用建议 |
|---|---|---|
| `record_id` | `REG_000001` 格式稳定编号 | 可作为监管记录主键 |
| `source_type` | 固定为 `regulation` | 区分数据类型 |
| `source` | `NFRA` 或 `CSRC` | 判断监管来源 |
| `title` | 清洗后的标题 | 可辅助主体和事件判断 |
| `event_date` | `YYYY-MM-DD` 日期 | 可作为事件时间 |
| `entity_name` | A 阶段规则粗提取主体 | 仅供参考，B 阶段需用 LLM 修正 |
| `raw_text` | 违规事实和处罚内容清洗文本 | B 阶段抽取风险字段的主要文本 |
| `penalty_amount` | 罚款金额，单位万元 | 无法解析为 `0`，可作为结构化参考 |
| `agency` | 监管机构 | 可辅助地区和监管来源判断 |
| `region` | A 阶段关键词粗提取地区 | 仅供参考，B 阶段可修正 |
| `url` | 原始链接 | 溯源字段 |

### news_cleaned.csv

字段固定为：

`record_id,source_type,source,title,event_date,content,mentioned_entity,channel,url`

| 字段 | 说明 | B 阶段使用建议 |
|---|---|---|
| `record_id` | `NEWS_000001` 格式稳定编号 | 可作为新闻记录主键 |
| `source_type` | 固定为 `news` | 区分数据类型 |
| `source` | 原新闻来源 | 作为来源参考 |
| `title` | 清洗后的标题 | 辅助判断主体和事件 |
| `event_date` | `YYYY-MM-DD` 日期 | 可作为新闻发布时间 |
| `content` | 清洗后的正文 | B 阶段判断主体、风险类型、情绪的主要文本 |
| `mentioned_entity` | A 阶段规则粗提取主体 | 提取率较低，B 阶段需重点用 LLM 修正 |
| `channel` | 原频道 | 来源辅助字段 |
| `url` | 原始链接 | 溯源字段 |

### comment_cleaned.csv

字段固定为：

`record_id,source_type,source,title,event_date,content,mentioned_entity,read_count,comment_count,url`

| 字段 | 说明 | B 阶段使用建议 |
|---|---|---|
| `record_id` | `COMM_000001` 格式稳定编号 | 可作为评论记录主键 |
| `source_type` | 固定为 `comment` | 区分数据类型 |
| `source` | 原评论来源 | 作为来源参考 |
| `title` | 清洗后的标题 | 辅助判断舆情主题 |
| `event_date` | `YYYY-MM-DD` 日期 | 可作为评论发布时间 |
| `content` | 优先正文，正文为空时用标题补充 | B 阶段判断舆情情绪的主要文本 |
| `mentioned_entity` | 优先来自 `stock_or_entity`，否则规则粗提取 | 可作为主体初值，仍建议校验 |
| `read_count` | 阅读数，无法解析为 `0` | 可作为热度参考 |
| `comment_count` | 评论数，无法解析为 `0` | 可作为热度参考 |
| `url` | 原始链接 | 溯源字段 |

## 四、清洗规则摘要

| 规则 | A 阶段处理方式 |
|---|---|
| 编码 | 所有 processed CSV 使用 UTF-8-sig |
| 日期 | 统一为 `YYYY-MM-DD`；评论中无年份日期用 `crawl_time` 年份补齐 |
| 文本 | 去 HTML、去多余空格、合并重复换行 |
| 金额 | 从罚款语境中解析金额并统一为万元；无法解析填 `0` |
| 去重 | regulation 按 `source + title + url`；news/comment 按 `title + url` |
| 无效记录 | 删除空 url、标题和正文同时为空、明显导航/页脚/免责声明短文本 |
| 缺失值 | 除明显无效记录外不随意删除，缺失字段保留为空 |
| 主体粗提取 | 使用“银行、证券、保险、集团、股份、公司、基金、信托、期货”等后缀保守提取 |
| 地区粗提取 | 从监管机构、标题、正文中匹配省市关键词 |

## 五、数据质量统计

| 文件 | 行数 | event_date 非空率 | url 非空率 | 主文本非空率 | 主体字段非空率 | penalty_amount 可解析数量 |
|---|---:|---:|---:|---:|---:|---:|
| `regulation_cleaned.csv` | 226 | 100.00% | 100.00% | 100.00% | 94.25% | 210 |
| `news_cleaned.csv` | 200 | 100.00% | 100.00% | 100.00% | 0.00% | 不适用 |
| `comment_cleaned.csv` | 1100 | 100.00% | 100.00% | 100.00% | 100.00% | 不适用 |

去重和删除情况：

| 文件 | raw/合并后数量 | 删除无效记录 | 去重删除 | processed 数量 |
|---|---:|---:|---:|---:|
| `regulation_cleaned.csv` | 300 | 0 | 74 | 226 |
| `news_cleaned.csv` | 200 | 0 | 0 | 200 |
| `comment_cleaned.csv` | 1100 | 0 | 0 | 1100 |

## 六、给 B 阶段的重点提醒

1. `regulation_cleaned.csv` 中 `raw_text` 是后续 LLM 抽取风险字段的主要文本。
2. `news_cleaned.csv` 中 `content` 是后续 LLM 判断主体、风险类型、情绪的主要文本。
3. `comment_cleaned.csv` 中 `content` 是后续 LLM 判断舆情情绪的主要文本。
4. A 阶段的 `entity_name`、`mentioned_entity`、`region` 只是规则粗提取，不保证完全准确，B 阶段需要 LLM 进一步修正。
5. 新闻数据的 `mentioned_entity` 非空率为 0.00%，说明规则未能稳定抽到新闻主体，B 阶段应重点从 `title + content` 中重新识别主体。
6. 监管数据的 `penalty_amount` 单位已经统一为万元；为避免误伤，无法解析的金额填 `0`，不代表一定没有处罚金额。
7. 后续如生成统一事件表，建议保留原始 `record_id` 和 `url`，方便从结果回溯到 A 阶段清洗数据和原网页。
