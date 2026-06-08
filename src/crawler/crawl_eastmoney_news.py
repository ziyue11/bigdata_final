from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE = "东方财富新闻"
BASE_URL = "https://finance.eastmoney.com"
FAST_NEWS_API = "https://newsapi.eastmoney.com/kuaixun/v2/api/list"
CHANNELS = {
    "金融监管": ["https://finance.eastmoney.com/a/cjjsp.html"],
    "上市公司": ["https://finance.eastmoney.com/a/cssgs.html"],
    "银行": ["https://finance.eastmoney.com/a/cywjh.html"],
    "证券聚焦": ["https://finance.eastmoney.com/a/czqyw.html"],
    "财经导读": ["https://finance.eastmoney.com/a/ccjdd.html"],
    "公司资讯": ["https://stock.eastmoney.com/a/cgsxw.html"],
}
KEYWORDS = [
    "金融",
    "银行",
    "证券",
    "保险",
    "上市公司",
    "处罚",
    "违规",
    "监管",
    "风险",
    "舆情",
    "信托",
    "券商",
    "股市",
    "A股",
    "港股",
    "公司",
    "公告",
    "减持",
    "暴跌",
    "熔断",
    "退市",
    "ST",
]
TARGET_ROWS = 200
CRAWL_STATS = {"failed_pages": 0, "skipped_pages": 0, "notes": []}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return session


def _get(session: requests.Session, url: str) -> requests.Response:
    resp = session.get(url, timeout=15)
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp


def _expand_pages(url: str) -> list[str]:
    if url.endswith(".html"):
        prefix = url[:-5]
        return [url] + [f"{prefix}_{i}.html" for i in range(2, 8)]
    return [url]


def _list_items(session: requests.Session) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for column in ["104", "102", "101", "100"]:
        for page in range(1, 16):
            try:
                resp = session.get(
                    FAST_NEWS_API,
                    params={"column": column, "limit": 20, "p": page},
                    timeout=15,
                    headers={"Referer": BASE_URL},
                )
                resp.raise_for_status()
                for news in resp.json().get("news", []):
                    title = _clean(news.get("title"))
                    full_url = news.get("url_w") or news.get("url_unique") or ""
                    digest = _clean(news.get("digest"))
                    if not title or not full_url or full_url in seen:
                        continue
                    if "eastmoney.com/a/" not in full_url or not full_url.endswith(".html"):
                        continue
                    if not any(k in f"{title} {digest}" for k in KEYWORDS):
                        continue
                    seen.add(full_url)
                    items.append(
                        {
                            "source": SOURCE,
                            "title": title,
                            "publish_time": _clean(news.get("showtime")),
                            "channel": f"东方财富快讯{column}",
                            "content_fallback": digest,
                            "url": full_url,
                        }
                    )
                    if len(items) >= TARGET_ROWS:
                        CRAWL_STATS["notes"].append(f"东方财富新闻优先使用公开快讯 API 补足 {TARGET_ROWS} 条，再访问详情页采正文。")
                        return items
            except Exception as exc:
                CRAWL_STATS["failed_pages"] += 1
                CRAWL_STATS["notes"].append(f"Eastmoney news API failed column={column} page={page}: {exc}")

    for channel, urls in CHANNELS.items():
        for seed_url in urls:
            for page_url in _expand_pages(seed_url):
                try:
                    resp = _get(session, page_url)
                    if resp.status_code != 200:
                        CRAWL_STATS["skipped_pages"] += 1
                        continue
                    soup = BeautifulSoup(resp.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        title = _clean(a.get_text(" ", strip=True))
                        href = a["href"]
                        full_url = urljoin(page_url, href)
                        if not title or full_url in seen:
                            continue
                        if "eastmoney.com/a/" not in full_url or not full_url.endswith(".html"):
                            continue
                        if not any(k in title for k in KEYWORDS):
                            continue
                        seen.add(full_url)
                        parent_text = _clean(a.parent.get_text(" ", strip=True) if a.parent else "")
                        date_match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2})?", parent_text)
                        items.append(
                            {
                                "source": SOURCE,
                                "title": title,
                                "publish_time": date_match.group(0) if date_match else "",
                                "channel": channel,
                                "content_fallback": "",
                                "url": full_url,
                            }
                        )
                        if len(items) >= TARGET_ROWS:
                            return items
                except Exception as exc:
                    CRAWL_STATS["failed_pages"] += 1
                    CRAWL_STATS["notes"].append(f"Eastmoney news list failed {page_url}: {exc}")
    return items[:TARGET_ROWS]


def _detail(session: requests.Session, item: dict) -> dict:
    content = ""
    publish_time = item.get("publish_time", "")
    title = item.get("title", "")
    try:
        resp = _get(session, item["url"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        page_title = _clean((soup.find("h1") or soup.find("title") or "").get_text(" ", strip=True))
        title = page_title or title
        text_candidates = []
        for selector in ["#ContentBody", ".Body", ".content", ".article", "p"]:
            nodes = soup.select(selector)
            if nodes:
                text_candidates = [_clean(n.get_text(" ", strip=True)) for n in nodes]
                break
        content = _clean(" ".join(t for t in text_candidates if t)) or item.get("content_fallback", "")
        if not publish_time:
            page_text = soup.get_text(" ", strip=True)
            date_match = re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?(?:\s+\d{1,2}:\d{2})?", page_text)
            if date_match:
                publish_time = date_match.group(0).replace("年", "-").replace("月", "-").replace("日", "")
    except Exception as exc:
        CRAWL_STATS["failed_pages"] += 1
        CRAWL_STATS["notes"].append(f"Eastmoney news detail failed {item.get('url')}: {exc}")
    return {
        "source": SOURCE,
        "title": title,
        "publish_time": publish_time,
        "channel": item.get("channel", ""),
        "content": content or item.get("content_fallback", ""),
        "url": item.get("url", ""),
        "crawl_time": _now(),
    }


def crawl() -> list[dict]:
    """
    返回当前网站的原始数据列表。
    每条数据是一个 dict。
    """
    CRAWL_STATS.update({"failed_pages": 0, "skipped_pages": 0, "notes": []})
    session = _session()
    results = []
    for item in _list_items(session):
        detail = _detail(session, item)
        if any(k in f"{detail['title']} {detail['content']}" for k in KEYWORDS):
            results.append(detail)
        time.sleep(0.05)
    return results[:TARGET_ROWS]
