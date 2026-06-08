from __future__ import annotations

import importlib
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
LOG_DIR = ROOT / "outputs" / "logs"
REPORT_DIR = ROOT / "docs" / "report"
LOG_FILE = LOG_DIR / "crawler_run.log"

TASKS = [
    {
        "module": "crawl_nfra",
        "csv": "regulation_nfra_raw.csv",
        "dedupe_keys": ["title", "url", "punished_entity", "violation_text", "penalty_text"],
        "fields": [
            "source",
            "title",
            "publish_time",
            "decision_no",
            "punished_entity",
            "violation_text",
            "penalty_text",
            "penalty_amount_raw",
            "agency",
            "url",
            "crawl_time",
        ],
        "name": "国家金融监督管理总局 NFRA 行政处罚/行政处罚信息公开表",
        "link": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemId=4113",
        "type": "监管处罚",
        "reason": "金融监管处罚直接反映银行、保险等机构违规风险，是本项目核心监管信号。",
    },
    {
        "module": "crawl_csrc",
        "csv": "regulation_csrc_raw.csv",
        "fields": [
            "source",
            "title",
            "publish_time",
            "party",
            "violation_text",
            "penalty_text",
            "penalty_amount_raw",
            "market_ban_raw",
            "url",
            "crawl_time",
        ],
        "name": "中国证监会 CSRC 行政处罚决定书",
        "link": "http://www.csrc.gov.cn/csrc/c101928/zfxxgk_zdgk.shtml",
        "type": "监管处罚",
        "reason": "证券市场处罚决定书覆盖上市公司、证券公司和相关责任主体违规事实。",
    },
    {
        "module": "crawl_eastmoney_news",
        "csv": "news_raw.csv",
        "fields": ["source", "title", "publish_time", "channel", "content", "url", "crawl_time"],
        "name": "东方财富财经新闻",
        "link": "https://finance.eastmoney.com/",
        "type": "财经新闻/媒体关注",
        "reason": "财经媒体报道可补充监管处罚以外的风险事件、市场关注和舆情线索。",
    },
    {
        "module": "crawl_eastmoney_guba",
        "csv": "comment_raw.csv",
        "fields": [
            "source",
            "title",
            "publish_time",
            "stock_or_entity",
            "content",
            "read_count",
            "comment_count",
            "url",
            "crawl_time",
        ],
        "name": "东方财富股吧",
        "link": "https://guba.eastmoney.com/",
        "type": "投资者评论/舆情",
        "reason": "投资者讨论可作为市场情绪和风险传闻的公开舆情补充。",
    },
]


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
        force=True,
    )


def _dedupe(rows: list[dict], fields: list[str], keys: list[str] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for field in fields:
        if field not in df.columns:
            df[field] = ""
    df = df[fields].fillna("")
    before = len(df)
    subset = keys or ["title", "url"]
    df = df.drop_duplicates(subset=subset, keep="first")
    df.attrs["duplicate_count"] = before - len(df)
    return df


def _nonnull_rate(df: pd.DataFrame, field: str) -> str:
    if len(df) == 0 or field not in df.columns:
        return "0.00%"
    rate = (df[field].astype(str).str.strip() != "").mean() * 100
    return f"{rate:.2f}%"


def _run_one(task: dict) -> dict:
    logging.info("start crawler module=%s", task["module"])
    try:
        module = importlib.import_module(task["module"])
        rows = module.crawl()
        status = "成功" if rows else "失败或无有效数据"
        stats = getattr(module, "CRAWL_STATS", {})
    except Exception as exc:
        rows = []
        status = "失败"
        stats = {"failed_pages": 1, "skipped_pages": 0, "notes": [str(exc)]}
        logging.exception("crawler failed module=%s", task["module"])

    df = _dedupe(rows, task["fields"], task.get("dedupe_keys"))
    out_path = RAW_DIR / task["csv"]
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logging.info(
        "finish crawler module=%s rows=%s duplicates=%s failed=%s skipped=%s csv=%s",
        task["module"],
        len(df),
        df.attrs.get("duplicate_count", 0),
        stats.get("failed_pages", 0),
        stats.get("skipped_pages", 0),
        out_path,
    )
    return {
        **task,
        "rows": len(df),
        "df": df,
        "status": status,
        "duplicate_count": df.attrs.get("duplicate_count", 0),
        "failed_pages": stats.get("failed_pages", 0),
        "skipped_pages": stats.get("skipped_pages", 0),
        "notes": stats.get("notes", []),
        "path": out_path,
    }


def _build_report(results: list[dict]) -> str:
    lines: list[str] = []
    total = sum(r["rows"] for r in results)
    lines.extend(
        [
            "# A 角色第一阶段爬虫内容说明",
            "",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "本阶段只完成公开数据源确认、原始网页采集、raw CSV 输出和文字版说明；未进行 processed 清洗、LLM 字段抽取、风险评分或可视化。",
            "",
            "## 一、数据源总览",
            "",
            "| 数据源名称 | 网站链接 | 数据类型 | 选择理由 | 采集字段 | 采集条数 | 是否成功 | 问题说明 |",
            "|---|---|---|---|---|---:|---|---|",
        ]
    )
    for r in results:
        notes = "；".join(r["notes"][:3])
        if r["module"] == "crawl_eastmoney_guba" and not notes:
            notes = "详情页可能存在动态渲染，正文为空时使用帖子标题补充 content。"
        if not notes:
            notes = "无明显问题。"
        fields = ", ".join(r["fields"])
        lines.append(
            f"| {r['name']} | {r['link']} | {r['type']} | {r['reason']} | {fields} | {r['rows']} | {r['status']} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## 二、各数据源内容说明",
            "",
            "1. NFRA 爬取国家金融监督管理总局行政处罚栏目公开列表接口 `/cbircweb/DocInfo/SelectDocByItemIdAndChild`，并访问详情接口 `/cbircweb/DocInfo/SelectByDocId`。优先解析详情页 Word HTML 表格中的行政处罚信息公开表字段。",
            "2. CSRC 爬取中国证监会政府信息公开的行政处罚栏目列表页及详情页。详情页正文作为长文本保存，A 阶段只做简单关键词段落和金额/禁入规则粗抽。",
            "3. 新闻源爬取东方财富财经频道中与金融、银行、证券、保险、上市公司、处罚、违规、监管、风险、舆情等关键词相关的公开新闻列表和详情正文。",
            "4. 股吧/评论源爬取东方财富股吧中银行、券商、保险/金融控股和互联网券商代表标的的公开帖子列表。由于详情正文动态渲染不稳定，本阶段按备用规则使用列表页字段，并用帖子标题补充 content 字段。",
            "5. 后续项目作用：NFRA 和 CSRC 用作监管处罚事实来源；财经新闻用于补充媒体关注和风险事件背景；股吧评论用于补充投资者情绪、传闻和市场关注度。",
            "",
            "## 三、字段对应关系说明",
            "",
            "### NFRA",
            "",
            "- `source` 固定为 NFRA；`title` 来自列表/详情标题；`publish_time` 来自发布时间或处罚决定日期；`url` 为详情页公开链接；`crawl_time` 为本次采集时间。",
            "- `decision_no` 对应“行政处罚决定书文号/处罚文号/决定书文号”；`punished_entity` 对应“被处罚当事人/当事人名称”；`violation_text` 对应“主要违法违规事实/主要违法违规行为”；`penalty_text` 对应“行政处罚决定/行政处罚内容”；`agency` 对应“作出处罚决定的机关名称/作出决定机关”。",
            "- `penalty_amount_raw` 只用简单正则从处罚内容中粗提取“罚款/没收...万元/元”片段，后续仍需人工或 LLM 精抽确认。",
            "",
            "### CSRC",
            "",
            "- `title`、`publish_time`、`url` 从列表页和详情页直接爬取；`violation_text` 暂存详情正文全文，保证长文本不丢失。",
            "- `penalty_text` 仅保存包含“处罚、罚款、警告、没收、决定、市场禁入”等关键词的段落，属于规则粗抽。",
            "- `party`、`penalty_amount_raw`、`market_ban_raw` 使用简单正则尝试提取，提取不到允许为空，留给后续 LLM 抽取。",
            "",
            "### 新闻和评论",
            "",
            "- 新闻 `channel` 来自爬取频道；`content` 来自详情页正文。",
            "- 股吧 `stock_or_entity` 来自论坛标的名称和代码；`read_count`、`comment_count` 来自列表页数字字段；`content` 本阶段使用帖子标题补充，原因是详情正文动态渲染不稳定。",
            "",
            "## 四、数据质量初步统计",
            "",
            f"总有效 raw 数据量：{total} 条。",
            "",
            "| CSV | 行数 | 字段名 | title 非空率 | url 非空率 | publish_time 非空率 | content/raw text/violation_text 非空率 | 重复数据数量 | 失败页面 | 跳过页面 |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in results:
        df = r["df"]
        text_field = "content" if "content" in df.columns else "violation_text"
        lines.append(
            f"| {r['csv']} | {r['rows']} | {', '.join(r['fields'])} | {_nonnull_rate(df, 'title')} | {_nonnull_rate(df, 'url')} | {_nonnull_rate(df, 'publish_time')} | {_nonnull_rate(df, text_field)} | {r['duplicate_count']} | {r['failed_pages']} | {r['skipped_pages']} |"
        )

    lines.extend(
        [
            "",
            "## 阶段边界说明",
            "",
            "- 当前未生成 `regulation_cleaned.csv`、`risk_event_table.csv` 或任何 processed 层文件。",
            "- 当前未调用 LLM，未进行风险评分，未生成可视化。",
            "- 若总有效数据少于 1000 条，原因通常是公开列表分页、详情页反爬/动态渲染、或本次为课程实验控制请求频率；具体以运行日志和上表数量为准。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    _ensure_dirs()
    _setup_logging()
    logging.info("crawler run started")
    results = [_run_one(task) for task in TASKS]
    report = _build_report(results)
    report_path = REPORT_DIR / "a_stage1_crawler_review.md"
    report_path.write_text(report, encoding="utf-8")
    logging.info("report written path=%s", report_path)
    print("Crawler run completed.")
    for result in results:
        print(f"{result['csv']}: {result['rows']} rows, status={result['status']}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
