import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from clean_comment import clean_comment
from clean_news import clean_news
from clean_regulation import clean_regulation

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline_paths import processed_dir, raw_dir, report_dir, output_dir  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", default="finance", help="finance or medical")
    args = parser.parse_args()
    industry = args.industry.strip().lower()

    raw_path = raw_dir(industry)
    processed_path = processed_dir(industry)
    log_path = output_dir(industry) / "logs" / "preprocess_run.log"
    report_path = report_dir(industry) / "a_stage2_preprocess_review.md"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    logging.info("Start preprocessing industry=%s raw_dir=%s", industry, raw_path)

    stats = [
        clean_regulation(raw_path, processed_path / "regulation_cleaned.csv"),
        clean_news(raw_path, processed_path / "news_cleaned.csv"),
        clean_comment(raw_path, processed_path / "comment_cleaned.csv"),
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
    _write_report(stats, industry, raw_path, processed_path, log_path, report_path)
    logging.info("Finished preprocessing industry=%s", industry)
    print(f"Preprocess completed for {industry}: {processed_path}")


def _pct(value):
    return f"{value * 100:.2f}%"


def _write_report(stats, industry, raw_path, processed_path, log_path, report_path):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {industry} raw 数据清洗与字段标准化说明",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "本阶段只完成 raw 数据清洗、字段标准化、去重和基础质量统计；未做 LLM 抽取、风险评分、统计分析或可视化。",
        "",
        "## 输入输出",
        "",
        f"- 输入目录：`{raw_path}`",
        f"- 输出目录：`{processed_path}`",
        f"- 日志文件：`{log_path}`",
        "",
        "## 质量统计",
        "",
        "| processed CSV | 行数 | 字段 | event_date 非空率 | url 非空率 | raw_text/content 非空率 | entity 非空率 | 金额解析数 | 去重删除 | 无效删除 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in stats:
        lines.append(
            "| {name} | {output_count} | {fields} | {date_rate} | {url_rate} | {text_rate} | {entity_rate} | {penalty_count} | {duplicate_removed} | {invalid_removed} |".format(
                name=item["name"],
                output_count=item["output_count"],
                fields=", ".join(item["fields"]),
                date_rate=_pct(item["event_date_non_empty_rate"]),
                url_rate=_pct(item["url_non_empty_rate"]),
                text_rate=_pct(item["text_non_empty_rate"]),
                entity_rate=_pct(item["entity_non_empty_rate"]),
                penalty_count=item["penalty_amount_parsed_count"],
                duplicate_removed=item["duplicate_removed"],
                invalid_removed=item["invalid_removed"],
            )
        )
    lines.extend(
        [
            "",
            "## 交接说明",
            "",
            "- `regulation_cleaned.csv` 的主文本字段是 `raw_text`。",
            "- `news_cleaned.csv` 和 `comment_cleaned.csv` 的主文本字段是 `content`。",
            "- `entity_name`、`mentioned_entity`、`region` 是规则粗抽取，后续 LLM 阶段需要修正。",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
