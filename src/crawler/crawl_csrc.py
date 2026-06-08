from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE = "CSRC"
BASE_URL = "http://www.csrc.gov.cn"
LIST_API = f"{BASE_URL}/searchList/28de6b87eda140cb93de4dd10d11867d"
REFERER_URL = f"{BASE_URL}/csrc/c101928/zfxxgk_zdgk.shtml"
TARGET_ROWS = 150
PAGE_SIZE = 10
CRAWL_STATS = {"failed_pages": 0, "skipped_pages": 0, "notes": []}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _get(session: requests.Session, url: str) -> requests.Response:
    resp = session.get(url, timeout=15)
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": REFERER_URL,
        }
    )
    return session


def _list_urls(session: requests.Session) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    page = 1
    while len(items) < TARGET_ROWS:
        try:
            resp = session.get(
                LIST_API,
                params={
                    "_isAgg": "true",
                    "_isJson": "true",
                    "_pageSize": PAGE_SIZE,
                    "_template": "index",
                    "_rangeTimeGte": "",
                    "_channelName": "",
                    "page": page,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            results = data.get("results") or []
            if not results:
                break
            for result in results:
                title = _clean(result.get("title"))
                full_url = urljoin(BASE_URL, result.get("url") or "")
                if not title or full_url in seen:
                    continue
                if "csrc.gov.cn" not in full_url or "content.shtml" not in full_url:
                    continue
                if full_url in seen:
                    continue
                seen.add(full_url)
                publish_time = _clean(result.get("publishedTimeStr"))
                items.append({"title": title, "url": full_url, "publish_time": publish_time})
                if len(items) >= TARGET_ROWS:
                    break
            page += 1
        except Exception as exc:
            CRAWL_STATS["failed_pages"] += 1
            CRAWL_STATS["notes"].append(f"CSRC list failed page={page}: {exc}")
            break
    CRAWL_STATS["notes"].append("CSRC 行政处罚列表改用公开 searchList JSON 接口分页采集，避免误抓政府信息公开年报区。")
    return items[:TARGET_ROWS]


def _paragraphs_with_keywords(text: str) -> str:
    paragraphs = re.split(r"(?<=[。！？；;])\s*", text)
    kept = [
        p
        for p in paragraphs
        if any(k in p for k in ["处罚", "罚款", "警告", "没收", "决定", "市场禁入"])
    ]
    return " ".join(kept[:20])


def _detail(session: requests.Session, item: dict) -> dict:
    url = item["url"]
    title = item.get("title", "")
    publish_time = item.get("publish_time", "")
    content = ""
    try:
        resp = _get(session, url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        meta_name = soup.find("meta", attrs={"name": "ArticleTitle"}) or soup.find("meta", attrs={"name": "Name"})
        page_title = _clean(meta_name.get("content") if meta_name else "")
        if not page_title:
            page_title = _clean((soup.find("h1") or "").get_text(" ", strip=True))
        title = page_title or title
        text_blocks = []
        for selector in [".content", ".article", ".TRS_Editor", "#zoom", ".detail-news", "p"]:
            nodes = soup.select(selector)
            if nodes:
                text_blocks = [_clean(n.get_text(" ", strip=True)) for n in nodes]
                break
        content = _clean(" ".join([t for t in text_blocks if t]))
        if not publish_time:
            page_text = soup.get_text(" ", strip=True)
            date_match = re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}", page_text)
            if date_match:
                publish_time = date_match.group(0).replace("年", "-").replace("月", "-").replace("日", "")
    except Exception as exc:
        CRAWL_STATS["failed_pages"] += 1
        CRAWL_STATS["notes"].append(f"CSRC detail failed {url}: {exc}")

    amount_match = re.search(r"(?:罚款|没收)[^。；;]*?(?:万元|元)", content)
    ban_match = re.search(r"市场禁入[^。；;]*?(?:年|终身|措施)", content)
    party_match = re.search(r"(?:当事人|被处罚人|申请人|涉案主体)[:： ]?([^，。；;\n]{2,80})", content)
    return {
        "source": SOURCE,
        "title": title,
        "publish_time": publish_time,
        "party": _clean(party_match.group(1)) if party_match else "",
        "violation_text": content,
        "penalty_text": _paragraphs_with_keywords(content),
        "penalty_amount_raw": amount_match.group(0) if amount_match else "",
        "market_ban_raw": ban_match.group(0) if ban_match else "",
        "url": url,
        "crawl_time": _now(),
    }


def crawl() -> list[dict]:
    """
    返回当前网站的原始数据列表。
    每条数据是一个 dict。
    """
    CRAWL_STATS.update({"failed_pages": 0, "skipped_pages": 0, "notes": []})
    session = _session()
    results: list[dict] = []
    for item in _list_urls(session):
        results.append(_detail(session, item))
        time.sleep(0.05)
    return results
