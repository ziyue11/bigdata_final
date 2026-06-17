from __future__ import annotations

import argparse
import csv
import html
import random
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "medical" / "raw"
LOG_DIR = ROOT / "data" / "medical" / "logs"
REPORT_PATH = LOG_DIR / "crawl_medical_report.md"
CRAWL_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
TIMEOUT = (10, 20)
SLEEP_RANGE = (1.5, 3.0)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
NEWS_FIELDS = ["source", "title", "publish_time", "channel", "content", "url", "crawl_time"]


@dataclass
class NewsSource:
    name: str
    channel: str
    mode: str
    url: str
    max_pages: int


NEWS_SOURCES = [
    NewsSource("新华健康-首页", "医疗健康新闻", "xinhua", "https://www.news.cn/health/", 1),
    NewsSource("新华健康-大健康", "医疗健康新闻", "xinhua", "https://www.news.cn/health/djk/index.html", 1),
    NewsSource("新华健康-科普汇", "医疗健康新闻", "xinhua", "https://www.news.cn/health/kph/index.html", 1),
    NewsSource("新华健康-视屏区", "医疗健康新闻", "xinhua", "https://www.news.cn/health/spq/index.html", 1),
    NewsSource("新华健康-权威发布", "医疗健康新闻", "xinhua", "https://www.news.cn/health/qwfb/index.html", 1),
    NewsSource("新华健康-重要资讯", "医疗健康新闻", "xinhua", "https://www.news.cn/health/zyzy/index.html", 1),
    NewsSource("新华健康-热点专题", "医疗健康新闻", "xinhua", "https://www.news.cn/health/rdzt/index.html", 1),
    NewsSource("央广网健康-央广", "医疗健康新闻", "cnr", "https://health.cnr.cn/yg/", 30),
    NewsSource("央广网健康-健康今日热点", "医疗健康新闻", "cnr", "https://health.cnr.cn/jkjrjd/", 30),
    NewsSource("央广网健康-医药企业", "医疗健康新闻", "cnr", "https://health.cnr.cn/yyqy/", 10),
    NewsSource("央广网健康-医药资讯", "医疗健康新闻", "cnr", "https://health.cnr.cn/yyzx/", 8),
    NewsSource("央广网健康-名医陪你", "医疗健康新闻", "cnr", "https://health.cnr.cn/mypy/", 3),
    NewsSource("央广网健康-何问中西", "医疗健康新闻", "cnr", "https://health.cnr.cn/jkzt/hwzx/", 1),
    NewsSource("央广网健康-苗岭名医", "医疗健康新闻", "cnr", "https://health.cnr.cn/mlm/", 4),
]


def polite_sleep() -> None:
    time.sleep(random.uniform(*SLEEP_RANGE))


def request_text(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    polite_sleep()
    return response.text


def clean_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_date(text: str) -> str:
    match = re.search(r"(20\d{2})[-./年](\d{1,2})[-./月](\d{1,2})", text)
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def absolute_url(base_url: str, href: str) -> str:
    return urllib.parse.urljoin(base_url, href)


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for row in rows:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        key = (title, url)
        if not title or not url or key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def parse_xinhua_page(source: NewsSource, url: str) -> list[dict]:
    text = request_text(url)
    rows = []
    for href, label in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.S | re.I):
        clean_label = clean_text(label)
        full_url = absolute_url(url, href)
        if "/health/" not in full_url or not full_url.endswith("/c.html") or len(clean_label) < 8:
            continue
        rows.append(
            {
                "source": source.name,
                "title": clean_label,
                "publish_time": extract_date(full_url) or extract_date(clean_label),
                "channel": source.channel,
                "content": clean_label,
                "url": full_url,
                "crawl_time": CRAWL_TIME,
            }
        )
    return dedupe(rows)


def cnr_page_url(base_url: str, page_index: int) -> str:
    if page_index == 0:
        return base_url
    return urllib.parse.urljoin(base_url, f"index_{page_index}.html")


def parse_cnr_page(source: NewsSource, url: str) -> list[dict]:
    text = request_text(url)
    rows = []
    for href, label in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.S | re.I):
        clean_label = clean_text(label)
        full_url = absolute_url(url, href)
        if "2014jkpd" not in full_url or not full_url.endswith(".shtml") or len(clean_label) < 8:
            continue
        rows.append(
            {
                "source": source.name,
                "title": clean_label[:120],
                "publish_time": extract_date(clean_label) or extract_date(full_url),
                "channel": source.channel,
                "content": clean_label,
                "url": full_url,
                "crawl_time": CRAWL_TIME,
            }
        )
    return dedupe(rows)


def crawl_xinhua(source: NewsSource, max_items_per_source: int) -> list[dict]:
    return parse_xinhua_page(source, source.url)[:max_items_per_source]


def crawl_cnr(source: NewsSource, max_items_per_source: int) -> list[dict]:
    rows = []
    for page_index in range(source.max_pages):
        page_url = cnr_page_url(source.url, page_index)
        try:
            page_rows = parse_cnr_page(source, page_url)
        except Exception:
            break
        if not page_rows:
            break
        rows.extend(page_rows)
        rows = dedupe(rows)
        if len(rows) >= max_items_per_source:
            break
    return rows[:max_items_per_source]


def crawl_source(source: NewsSource, max_items_per_source: int) -> list[dict]:
    if source.mode == "cnr":
        return crawl_cnr(source, max_items_per_source)
    return crawl_xinhua(source, max_items_per_source)


def reset_outputs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with (RAW_DIR / "medical_news_raw.csv").open("w", encoding="utf-8-sig", newline="") as f:
        csv.DictWriter(f, fieldnames=NEWS_FIELDS).writeheader()


def append_rows(path: Path, rows: list[dict]) -> None:
    existing = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    merged = dedupe(existing + rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NEWS_FIELDS)
        writer.writeheader()
        for row in merged:
            writer.writerow({field: row.get(field, "") for field in NEWS_FIELDS})


def delete_zero_raw_files() -> None:
    for filename in [
        "medical_comment_raw.csv",
        "medical_drug_device_raw.csv",
        "medical_regulation_raw.csv",
    ]:
        path = RAW_DIR / filename
        if path.exists() and path.stat().st_size <= 4:
            path.unlink()


def write_report(results: list[dict]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 医疗新闻爬虫运行报告",
        "",
        f"生成时间：{CRAWL_TIME}",
        "",
        "| 数据源 | URL | 状态 | 条数 | 失败原因 |",
        "|---|---|---|---:|---|",
    ]
    for item in results:
        lines.append(f"| {item['name']} | {item['url']} | {item['status']} | {item['count']} | {item['error']} |")
    lines.extend(
        [
            "",
            "输出文件：`data/raw/medical_news_raw.csv`。",
            "已删除 0 条的 `medical_comment_raw.csv`、`medical_drug_device_raw.csv`、`medical_insurance_raw.csv`、`medical_regulation_raw.csv`。",
            "人民网健康、健康中国在当前环境下没有稳定可用的批量新闻列表，本轮未作为默认数据源。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items-per-source", type=int, default=250)
    parser.add_argument("--min-items-per-source", type=int, default=10)
    args = parser.parse_args()

    reset_outputs()
    delete_zero_raw_files()

    output_path = RAW_DIR / "medical_news_raw.csv"
    results = []
    for source in NEWS_SOURCES:
        try:
            rows = crawl_source(source, args.max_items_per_source)
            if len(rows) < args.min_items_per_source:
                results.append({"name": source.name, "url": source.url, "status": "discarded", "count": len(rows), "error": f"row count < {args.min_items_per_source}"})
            else:
                append_rows(output_path, rows)
                results.append({"name": source.name, "url": source.url, "status": "success", "count": len(rows), "error": ""})
        except Exception as exc:
            results.append({"name": source.name, "url": source.url, "status": "failed", "count": 0, "error": str(exc).replace("|", "/")[:300]})
        write_report(results)

    total = 0
    if output_path.exists():
        with output_path.open("r", encoding="utf-8-sig", newline="") as f:
            total = len(list(csv.DictReader(f)))
    print(f"Medical news crawl finished: {total} rows. Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
