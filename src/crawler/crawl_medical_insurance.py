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
REPORT_PATH = LOG_DIR / "crawl_medical_insurance_report.md"
CRAWL_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
TIMEOUT = (10, 20)
SLEEP_RANGE = (1.5, 3.0)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
FIELDS = [
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
]


@dataclass
class InsuranceSource:
    name: str
    url: str
    agency: str


SOURCES = [
    InsuranceSource("国家医保局-医保动态", "https://www.nhsa.gov.cn/col/col14/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-地方医保动态", "https://www.nhsa.gov.cn/col/col15/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-打击骗保", "https://www.nhsa.gov.cn/col/col20/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-统计数据", "https://www.nhsa.gov.cn/col/col7/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-媒体报道", "https://www.nhsa.gov.cn/col/col46/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-政策法规", "https://www.nhsa.gov.cn/col/col53/index.html", "国家医疗保障局"),
    InsuranceSource("国家医保局-公共服务", "https://www.nhsa.gov.cn/col/col114/index.html", "国家医疗保障局"),
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


def parse_links(base_url: str, html_text: str, max_items_per_source: int) -> list[dict]:
    rows = []
    for href, label in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html_text, re.S | re.I):
        title = clean_text(label)
        full_url = urllib.parse.urljoin(base_url, href)
        if len(title) < 8 or "/art/" not in full_url:
            continue
        publish_time = extract_date(title) or extract_date(full_url)
        rows.append(
            {
                "title": title,
                "publish_time": publish_time,
                "url": full_url,
            }
        )
        if len(rows) >= max_items_per_source:
            break
    return dedupe(rows)


def crawl_source(source: InsuranceSource, max_items_per_source: int) -> list[dict]:
    html_text = request_text(source.url)
    rows = []
    for item in parse_links(source.url, html_text, max_items_per_source):
        content = f"{source.name} {item['title']}"
        rows.append(
            {
                "source": source.name,
                "title": item["title"],
                "publish_time": item["publish_time"],
                "decision_no": "",
                "punished_entity": "",
                "violation_text": content,
                "penalty_text": content,
                "penalty_amount_raw": "",
                "agency": source.agency,
                "url": item["url"],
                "crawl_time": CRAWL_TIME,
            }
        )
    return dedupe(rows)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def write_report(results: list[dict]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 医保局原始数据爬取报告",
        "",
        f"生成时间：{CRAWL_TIME}",
        "",
        "| 数据源 | URL | 状态 | 条数 | 失败原因 |",
        "|---|---|---|---:|---|",
    ]
    for item in results:
        lines.append(f"| {item['name']} | {item['url']} | {item['status']} | {item['count']} | {item['error']} |")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items-per-source", type=int, default=50)
    parser.add_argument("--min-items-per-source", type=int, default=10)
    args = parser.parse_args()

    results = []
    all_rows = []
    for source in SOURCES:
        try:
            rows = crawl_source(source, args.max_items_per_source)
            if len(rows) < args.min_items_per_source:
                results.append({"name": source.name, "url": source.url, "status": "discarded", "count": len(rows), "error": f"row count < {args.min_items_per_source}"})
            else:
                all_rows.extend(rows)
                all_rows = dedupe(all_rows)
                results.append({"name": source.name, "url": source.url, "status": "success", "count": len(rows), "error": ""})
        except Exception as exc:
            results.append({"name": source.name, "url": source.url, "status": "failed", "count": 0, "error": str(exc).replace("|", "/")[:300]})
        write_report(results)

    output_path = RAW_DIR / "medical_insurance_raw.csv"
    write_csv(output_path, all_rows)
    print(f"Medical insurance crawl finished: {len(all_rows)} rows. Output: {output_path}")


if __name__ == "__main__":
    main()
