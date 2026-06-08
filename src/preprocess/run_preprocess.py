import logging
from datetime import datetime
from pathlib import Path

from clean_comment import clean_comment
from clean_news import clean_news
from clean_regulation import clean_regulation


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
LOG_PATH = ROOT / "outputs" / "logs" / "preprocess_run.log"
REPORT_PATH = ROOT / "docs" / "report" / "a_stage2_preprocess_review.md"


def main():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    logging.info("Start A stage2 preprocessing")

    stats = [
        clean_regulation(RAW_DIR, PROCESSED_DIR / "regulation_cleaned.csv"),
        clean_news(RAW_DIR, PROCESSED_DIR / "news_cleaned.csv"),
        clean_comment(RAW_DIR, PROCESSED_DIR / "comment_cleaned.csv"),
    ]

    for item in stats:
        logging.info(
            "%s raw=%s output=%s invalid_removed=%s duplicate_removed=%s fields=%s",
            item["name"],
            item["raw_count"],
            item["output_count"],
            item["invalid_removed"],
            item["duplicate_removed"],
            ",".join(item["fields"]),
        )
    _write_report(stats)
    logging.info("Finished A stage2 preprocessing")


def _pct(value):
    return f"{value * 100:.2f}%"


def _write_report(stats):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    by_name = {item["name"]: item for item in stats}
    lines = [
        "# A 角色第二阶段 raw 数据清洗与字段标准化说明",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "本阶段只完成 raw 数据单源清洗、字段标准化、去重和基础质量统计；未进行 LLM 抽取、风险评分、risk_event_table.csv 生成、数据分析或可视化。",
        "",
        "## 一、输入输出文件说明",
        "",
        "| 类型 | 文件 | 说明 |",
        "|---|---|---|",
        "| 输入 | data/raw/regulation_nfra_raw.csv | NFRA 行政处罚 raw 数据 |",
        "| 输入 | data/raw/regulation_csrc_raw.csv | CSRC 行政处罚 raw 数据 |",
        "| 输入 | data/raw/news_raw.csv | 财经新闻 raw 数据 |",
        "| 输入 | data/raw/comment_raw.csv | 股吧评论 raw 数据 |",
        "| 输出 | data/processed/regulation_cleaned.csv | 合并后的监管处罚清洗表 |",
        "| 输出 | data/processed/news_cleaned.csv | 新闻清洗表 |",
        "| 输出 | data/processed/comment_cleaned.csv | 评论清洗表 |",
        "| 日志 | outputs/logs/preprocess_run.log | 本次预处理运行日志 |",
        "",
        "## 二、字段映射说明",
        "",
        "### regulation_cleaned.csv",
        "",
        "| processed 字段 | raw 来源 | 清洗规则 |",
        "|---|---|---|",
        "| record_id | 生成 | 按输出顺序生成 REG_000001 稳定编号 |",
        "| source_type | 固定值 | 固定为 regulation |",
        "| source | source | 保留 NFRA / CSRC |",
        "| title | title | 去 HTML 和多余空格 |",
        "| event_date | publish_time | 标准化为 YYYY-MM-DD |",
        "| entity_name | NFRA punished_entity；CSRC party | 为空时从 title/raw_text 用机构后缀规则粗提取 |",
        "| raw_text | violation_text、penalty_text | NFRA 合并 violation_text + penalty_text；CSRC 合并正文和处罚段，统一清洗文本 |",
        "| penalty_amount | penalty_amount_raw、penalty_text、violation_text | 解析罚款语境金额，统一为万元；无法解析填 0 |",
        "| agency | NFRA agency；CSRC 推断 | CSRC 缺失时填中国证监会 |",
        "| region | agency、title、raw_text | 用省市关键词粗提取，提取不到留空 |",
        "| url | url | 保留原链接，空链接记录删除 |",
        "",
        "### news_cleaned.csv",
        "",
        "| processed 字段 | raw 来源 | 清洗规则 |",
        "|---|---|---|",
        "| record_id | 生成 | 按输出顺序生成 NEWS_000001 稳定编号 |",
        "| source_type | 固定值 | 固定为 news |",
        "| source | source | 保留原来源 |",
        "| title | title | 去 HTML 和多余空格 |",
        "| event_date | publish_time | 标准化为 YYYY-MM-DD |",
        "| content | content | 去 HTML、多余空格和重复换行 |",
        "| mentioned_entity | title、content | 用机构/公司后缀规则粗提取，提取不到留空 |",
        "| channel | channel | 保留原频道 |",
        "| url | url | 保留原链接，空链接记录删除 |",
        "",
        "### comment_cleaned.csv",
        "",
        "| processed 字段 | raw 来源 | 清洗规则 |",
        "|---|---|---|",
        "| record_id | 生成 | 按输出顺序生成 COMM_000001 稳定编号 |",
        "| source_type | 固定值 | 固定为 comment |",
        "| source | source | 保留原来源 |",
        "| title | title | 去 HTML 和多余空格 |",
        "| event_date | publish_time | 标准化为 YYYY-MM-DD；无年份时用 crawl_time 年份补齐 |",
        "| content | content、title | 优先 content，空时用 title 补充 |",
        "| mentioned_entity | stock_or_entity、title、content | 优先 stock_or_entity，空时用后缀规则粗提取 |",
        "| read_count | read_count | 转整数，无法解析填 0 |",
        "| comment_count | comment_count | 转整数，无法解析填 0 |",
        "| url | url | 保留原链接，空链接记录删除 |",
        "",
        "## 三、清洗规则说明",
        "",
        "- 日期标准化规则：优先按 `YYYY-MM-DD HH:MM:SS`、`YYYY-MM-DD HH:MM`、`YYYY-MM-DD`、`YYYY年MM月DD日` 解析；评论中 `MM-DD HH:MM` 或 `MM-DD` 这类无年份日期使用同记录 `crawl_time` 的年份补齐。",
        "- 金额解析规则：从 `penalty_amount_raw`、`penalty_text`、`violation_text` 拼接文本中，只抓取“罚款、处以、并处、罚金”附近的金额，统一换算为万元；`1.2亿元` 记为 `12000`，`50万元` 记为 `50`，`500000元` 记为 `50`；无法解析填 `0`。",
        "- 文本清洗规则：HTML 实体反转义，删除 script/style/HTML 标签，压缩多余空格，重复换行合并为单个换行。",
        "- 去重规则：regulation 按 `source + title + url` 去重；news 和 comment 按 `title + url` 去重。",
        "- 缺失值处理规则：除空 url、标题与正文同时为空、明显导航/页脚/免责声明短文本外，不因字段缺失删除记录；缺失字段保留为空。金额无法解析时填 `0`。",
        "- 地区/主体粗提取规则：主体使用“银行、证券、保险、集团、股份、公司、基金、信托、期货”等后缀的短语保守提取；地区使用省市和计划单列市关键词从 agency、title、正文中匹配。二者都只作为 B 阶段前的规则粗提取结果。",
        "",
        "## 四、数据质量统计",
        "",
        "| processed CSV | 行数 | 字段名 | event_date 非空率 | url 非空率 | raw_text/content 非空率 | entity_name/mentioned_entity 非空率 | penalty_amount 可解析数量 | 去重前数量 | 去重后数量 | 去重删除 | 删除无效记录 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in stats:
        lines.append(
            "| {name} | {output_count} | {fields} | {date_rate} | {url_rate} | {text_rate} | {entity_rate} | {penalty_count} | {before_dedup} | {output_count} | {duplicate_removed} | {invalid_removed} |".format(
                name=item["name"],
                output_count=item["output_count"],
                fields=", ".join(item["fields"]),
                date_rate=_pct(item["event_date_non_empty_rate"]),
                url_rate=_pct(item["url_non_empty_rate"]),
                text_rate=_pct(item["text_non_empty_rate"]),
                entity_rate=_pct(item["entity_non_empty_rate"]),
                penalty_count=item["penalty_amount_parsed_count"],
                before_dedup=item["after_invalid_count"],
                duplicate_removed=item["duplicate_removed"],
                invalid_removed=item["invalid_removed"],
            )
        )
    lines.extend(
        [
            "",
            "## 五、交接给 B 的说明",
            "",
            "- `regulation_cleaned.csv` 中 `raw_text` 是后续 LLM 抽取风险字段的主要文本。",
            "- `news_cleaned.csv` 中 `content` 是后续 LLM 判断主体、风险类型、情绪的主要文本。",
            "- `comment_cleaned.csv` 中 `content` 是后续 LLM 判断舆情情绪的主要文本。",
            "- 当前阶段的 `entity_name`、`mentioned_entity`、`region` 只是规则粗提取，不保证完全准确，B 阶段需要 LLM 进一步修正。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
