from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE = "东方财富股吧"
BASE_URL = "https://guba.eastmoney.com"
FORUMS = {
    "平安银行": "000001",
    "浦发银行": "600000",
    "招商银行": "600036",
    "兴业银行": "601166",
    "民生银行": "600016",
    "工商银行": "601398",
    "中国银行": "601988",
    "中信证券": "600030",
    "华泰证券": "601688",
    "国泰君安": "601211",
    "中国平安": "601318",
    "中国太保": "601601",
    "新华保险": "601336",
    "东方财富": "300059",
}
MAX_ROWS = 1100
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


def _parse_count(text: str) -> str:
    match = re.search(r"\d+(?:\.\d+)?[万千]?", text or "")
    return match.group(0) if match else ""


def _list_items(session: requests.Session) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for entity, code in FORUMS.items():
        for page in range(1, 11):
            url = f"{BASE_URL}/list,{code}_{page}.html" if page > 1 else f"{BASE_URL}/list,{code}.html"
            try:
                resp = session.get(url, timeout=15)
                if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding
                if resp.status_code != 200:
                    CRAWL_STATS["skipped_pages"] += 1
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                rows = soup.select("div.articleh, tr")
                if not rows:
                    rows = soup.find_all("div")
                for row in rows:
                    a = row.find("a", href=True)
                    if not a:
                        continue
                    title = _clean(a.get_text(" ", strip=True))
                    href = a["href"]
                    full_url = urljoin(BASE_URL, href)
                    if not title or full_url in seen or "news," not in full_url:
                        continue
                    seen.add(full_url)
                    row_text = _clean(row.get_text(" ", strip=True))
                    nums = re.findall(r"\d+(?:\.\d+)?[万千]?", row_text)
                    date_match = re.search(r"\d{2}-\d{2}\s+\d{2}:\d{2}|\d{4}-\d{2}-\d{2}", row_text)
                    items.append(
                        {
                            "title": title,
                            "publish_time": date_match.group(0) if date_match else "",
                            "stock_or_entity": f"{entity}({code})",
                            "content": title,
                            "read_count": nums[0] if len(nums) >= 1 else "",
                            "comment_count": nums[1] if len(nums) >= 2 else "",
                            "url": full_url,
                        }
                    )
                    if len(items) >= MAX_ROWS:
                        return items
            except Exception as exc:
                CRAWL_STATS["failed_pages"] += 1
                CRAWL_STATS["notes"].append(f"Eastmoney guba list failed {url}: {exc}")
            time.sleep(0.03)
    return items


def _detail(session: requests.Session, item: dict) -> dict:
    content = item.get("content", "")
    publish_time = item.get("publish_time", "")
    try:
        resp = session.get(item["url"], timeout=12)
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        if resp.status_code != 200:
            CRAWL_STATS["skipped_pages"] += 1
        else:
            soup = BeautifulSoup(resp.text, "lxml")
            detail_text = ""
            for selector in [".newstext", ".stockcodec", ".article-body", ".detail_body", "div"]:
                nodes = soup.select(selector)
                candidates = [_clean(n.get_text(" ", strip=True)) for n in nodes]
                candidates = [c for c in candidates if len(c) > 20]
                if candidates:
                    detail_text = max(candidates, key=len)
                    break
            if detail_text:
                content = detail_text
            if not publish_time:
                page_text = soup.get_text(" ", strip=True)
                date_match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\d{2}-\d{2}\s+\d{2}:\d{2}", page_text)
                if date_match:
                    publish_time = date_match.group(0)
    except Exception as exc:
        CRAWL_STATS["failed_pages"] += 1
        CRAWL_STATS["notes"].append(f"Eastmoney guba detail failed {item.get('url')}: {exc}")
    return {
        "source": SOURCE,
        "title": item.get("title", ""),
        "publish_time": publish_time,
        "stock_or_entity": item.get("stock_or_entity", ""),
        "content": content,
        "read_count": item.get("read_count", ""),
        "comment_count": item.get("comment_count", ""),
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
    rows = []
    for item in _list_items(session):
        # 股吧详情页经常动态渲染。A 阶段优先保证公开列表字段可复现，
        # content 使用帖子标题补充；后续审核通过后再决定是否深化详情正文采集。
        rows.append(
            {
                "source": SOURCE,
                "title": item.get("title", ""),
                "publish_time": item.get("publish_time", ""),
                "stock_or_entity": item.get("stock_or_entity", ""),
                "content": item.get("content", ""),
                "read_count": item.get("read_count", ""),
                "comment_count": item.get("comment_count", ""),
                "url": item.get("url", ""),
                "crawl_time": _now(),
            }
        )
        time.sleep(0.03)
    CRAWL_STATS["notes"].append("股吧详情正文动态渲染不稳定，本次按备用规则使用列表页字段，并用帖子标题补充 content。")
    return rows[:MAX_ROWS]
