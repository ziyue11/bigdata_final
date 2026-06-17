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
REPORT_PATH = LOG_DIR / "crawl_medical_comment_report.md"
CRAWL_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
TIMEOUT = (10, 20)
SLEEP_RANGE = (1.5, 3.0)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
COMMENT_FIELDS = [
    "source",
    "title",
    "publish_time",
    "stock_or_entity",
    "content",
    "read_count",
    "comment_count",
    "url",
    "crawl_time",
]


@dataclass
class CommentSource:
    name: str
    mode: str
    url: str
    max_pages: int
    item_limit: int


SOURCES = [
    CommentSource("新华网评论-最新评论", "xinhua", "https://www.news.cn/comments/wpgd/index.html", 1, 25),
    CommentSource("新华网评论-新华网评", "xinhua", "https://www.news.cn/comments/wpyc/index.html", 1, 25),
    CommentSource("新华网评论-新华网视评", "xinhua", "https://www.news.cn/comments/zt/xhwsp/index.html", 1, 40),
    CommentSource("新华网评论-学习网评", "xinhua", "https://www.news.cn/comments/xxwp/index.html", 1, 20),
    CommentSource("新华网评论-今日专家", "xinhua", "https://www.news.cn/comments/jrzj/index.html", 1, 20),
    CommentSource("新华网评论-青年话", "xinhua", "https://www.news.cn/comments/qyh/index.html", 1, 10),
    CommentSource("央广网评", "cnr", "https://news.cnr.cn/comment/cnrp/", 16, 140),
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


def absolute_url(base_url: str, href: str) -> str:
    return urllib.parse.urljoin(base_url, href)


def dedupe_rows(rows: list[dict]) -> list[dict]:
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


def extract_meta_value(text: str, meta_name: str) -> str:
    pattern = rf'<meta[^>]+name=["\']{re.escape(meta_name)}["\'][^>]+content=["\']([^"\']*)["\']'
    match = re.search(pattern, text, re.I)
    return clean_text(match.group(1)) if match else ""


def extract_paragraph_text(text: str) -> str:
    parts = []
    for segment in re.findall(r"<p[^>]*>(.*?)</p>", text, re.I | re.S):
        cleaned = clean_text(segment)
        if len(cleaned) >= 8:
            parts.append(cleaned)
    if not parts:
        for segment in re.findall(r"<div[^>]*class=[\"'][^\"']*(?:content|article|detail|main)[^\"']*[\"'][^>]*>(.*?)</div>", text, re.I | re.S):
            cleaned = clean_text(segment)
            if len(cleaned) >= 20:
                parts.append(cleaned)
    content = " ".join(parts)
    return re.sub(r"\s+", " ", content).strip()[:5000]


def guess_entity(title: str, content: str) -> str:
    text = f"{title} {content}"
    match = re.search(
        r"([\u4e00-\u9fa5A-Za-z0-9]{2,40}(?:医院|卫生院|诊所|医保局|药监局|卫健委|制药|药业|医药|药房|医疗器械|公司|平台))",
        text,
    )
    return match.group(1) if match else ""


def parse_xinhua_list(source: CommentSource) -> list[dict]:
    text = request_text(source.url)
    rows = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
        full_url = absolute_url(source.url, href)
        if "/comments/" not in full_url or not full_url.endswith("/c.html"):
            continue
        title = clean_text(label)
        if len(title) < 6:
            continue
        rows.append({"title": title, "url": full_url})
    return dedupe_rows(rows)


def cnr_page_url(base_url: str, page_index: int) -> str:
    if page_index == 0:
        return base_url
    return urllib.parse.urljoin(base_url, f"index_{page_index}.html")


def parse_cnr_list(source: CommentSource, page_index: int) -> list[dict]:
    text = request_text(cnr_page_url(source.url, page_index))
    rows = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
        full_url = absolute_url(source.url, href)
        if "/newscenter/comment/cnrp/" not in full_url or not full_url.endswith(".shtml"):
            continue
        title = clean_text(label)
        if len(title) < 6:
            continue
        rows.append({"title": title, "url": full_url})
    return dedupe_rows(rows)


def parse_detail(source_name: str, title_hint: str, url: str) -> dict:
    text = request_text(url)
    title = extract_meta_value(text, "title") or title_hint
    if not title:
        page_title = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        title = clean_text(page_title.group(1)) if page_title else title_hint
    title = re.sub(r"[_\-|].*$", "", title).strip() or title_hint
    publish_time = extract_meta_value(text, "publishdate")
    content = extract_paragraph_text(text) or title
    entity = guess_entity(title, content)
    return {
        "source": source_name,
        "title": title[:200],
        "publish_time": publish_time,
        "stock_or_entity": entity,
        "content": content,
        "read_count": "",
        "comment_count": "",
        "url": url,
        "crawl_time": CRAWL_TIME,
    }


def append_rows(path: Path, rows: list[dict]) -> None:
    existing = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    merged = dedupe_rows(existing + rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        for row in merged:
            writer.writerow({field: row.get(field, "") for field in COMMENT_FIELDS})


def reset_output(path: Path) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.DictWriter(f, fieldnames=COMMENT_FIELDS).writeheader()


def write_report(results: list[dict], total: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Medical Comment Crawl Report",
        "",
        f"Generated at: {CRAWL_TIME}",
        "",
        "| Source | URL | Status | Rows | Error |",
        "|---|---|---|---:|---|",
    ]
    for item in results:
        lines.append(f"| {item['name']} | {item['url']} | {item['status']} | {item['count']} | {item['error']} |")
    lines.extend(
        [
            "",
            f"Output file: `data/medical/raw/medical_comment_raw.csv`",
            f"Total rows written: {total}",
            "Note: these rows come from official commentary/opinion columns under the current news sites because stable public user-comment APIs were not exposed on article detail pages.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def crawl_source(source: CommentSource, max_items_per_source: int) -> list[dict]:
    source_limit = min(max_items_per_source, source.item_limit)
    detail_rows = []
    if source.mode == "xinhua":
        candidates = parse_xinhua_list(source)
    else:
        candidates = []
        for page_index in range(source.max_pages):
            page_rows = parse_cnr_list(source, page_index)
            if not page_rows:
                break
            candidates.extend(page_rows)
            candidates = dedupe_rows(candidates)
            if len(candidates) >= source_limit:
                break
    for item in candidates[:source_limit]:
        try:
            detail_rows.append(parse_detail(source.name, item["title"], item["url"]))
        except Exception:
            continue
    return dedupe_rows(detail_rows)[:source_limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items-per-source", type=int, default=80)
    args = parser.parse_args()

    output_path = RAW_DIR / "medical_comment_raw.csv"
    reset_output(output_path)

    results = []
    for source in SOURCES:
        try:
            rows = crawl_source(source, args.max_items_per_source)
            append_rows(output_path, rows)
            results.append({"name": source.name, "url": source.url, "status": "success", "count": len(rows), "error": ""})
        except Exception as exc:
            results.append({"name": source.name, "url": source.url, "status": "failed", "count": 0, "error": str(exc).replace("|", "/")[:300]})
        total = 0
        if output_path.exists():
            with output_path.open("r", encoding="utf-8-sig", newline="") as f:
                total = len(list(csv.DictReader(f)))
        write_report(results, total)

    total = 0
    if output_path.exists():
        with output_path.open("r", encoding="utf-8-sig", newline="") as f:
            total = len(list(csv.DictReader(f)))
    print(f"Medical comment crawl finished: {total} rows. Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
