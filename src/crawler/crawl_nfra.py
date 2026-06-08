from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE = "NFRA"
BASE_URL = "https://www.nfra.gov.cn"
LIST_API = f"{BASE_URL}/cbircweb/DocInfo/SelectDocByItemIdAndChild"
DETAIL_API = f"{BASE_URL}/cbircweb/DocInfo/SelectByDocId"
ITEM_ID = "4113"
MAX_ROWS = 150
PAGE_SIZE = 18
CRAWL_STATS = {"failed_pages": 0, "skipped_pages": 0, "notes": []}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"{BASE_URL}/cn/view/pages/ItemList.html?itemId={ITEM_ID}",
        }
    )
    return session


def _get_json(session: requests.Session, url: str, params: dict[str, Any]) -> dict:
    last_exc: Exception | None = None
    cdn_path = _cdn_url(url, params)
    if cdn_path:
        try:
            resp = session.get(cdn_path, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc

    for attempt in range(1):
        try:
            resp = session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(last_exc)


def _cdn_url(url: str, params: dict[str, Any]) -> str:
    api_path = url.replace(BASE_URL + "/cbircweb", "")
    if api_path == "/DocInfo/SelectByDocId":
        doc_id = params.get("docId")
        return f"{BASE_URL}/cn/static/data/DocInfo/SelectByDocId/data_docId={doc_id}.json" if doc_id else ""
    if api_path == "/DocInfo/SelectDocByItemIdAndChild":
        ordered = ",".join(f"{key}={params[key]}" for key in sorted(params))
        return f"{BASE_URL}/cn/static/data/DocInfo/SelectDocByItemIdAndChild/data_{ordered}.json"
    return ""


def _pick(mapping: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        for name, value in mapping.items():
            norm_name = re.sub(r"\s+", "", name)
            norm_key = re.sub(r"\s+", "", key)
            if norm_key in norm_name and value:
                return value
    return ""


def _row_from_mapping(mapping: dict[str, str], fallback: dict[str, str]) -> dict:
    penalty_text = _pick(
        mapping,
        ["行政处罚决定", "行政处罚内容", "处罚决定", "处罚内容", "行政处罚"],
    )
    violation_text = _pick(
        mapping,
        ["主要违法违规事实", "主要违法违规行为", "违法违规事实", "违法违规行为"],
    )
    decision_no = _pick(mapping, ["行政处罚决定书文号", "处罚文号", "决定书文号", "文号"])
    punished_entity = _pick(mapping, ["被处罚当事人", "当事人名称", "被处罚人", "当事人"])
    agency = _pick(mapping, ["作出处罚决定的机关", "作出决定机关", "处罚机关", "机关名称"])
    publish_time = _pick(mapping, ["作出处罚决定的日期", "决定日期", "日期"]) or fallback.get("publish_time", "")
    amount = ""
    amount_match = re.search(r"(?:罚款|没收)[^。；;]*?(?:万元|元)", penalty_text)
    if amount_match:
        amount = amount_match.group(0)
    return {
        "source": SOURCE,
        "title": fallback.get("title", ""),
        "publish_time": publish_time,
        "decision_no": decision_no or fallback.get("decision_no", ""),
        "punished_entity": punished_entity,
        "violation_text": violation_text,
        "penalty_text": penalty_text,
        "penalty_amount_raw": amount,
        "agency": agency,
        "url": fallback.get("url", ""),
        "crawl_time": fallback.get("crawl_time", _now()),
    }


def _parse_tables(html: str, fallback: dict[str, str]) -> list[dict]:
    soup = BeautifulSoup(html or "", "lxml")
    rows: list[dict] = []
    for table in soup.find_all("table"):
        table_rows = table.find_all("tr")
        header_cells: list[str] = []
        if table_rows:
            header_cells = [_clean(c.get_text(" ", strip=True)) for c in table_rows[0].find_all(["td", "th"])]
        if any("当事人" in h for h in header_cells) and any("行政处罚" in h for h in header_cells):
            for tr in table_rows[1:]:
                cells = [_clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
                if len(cells) != len(header_cells):
                    continue
                mapping = dict(zip(header_cells, cells))
                parsed = _row_from_mapping(mapping, fallback)
                if parsed["punished_entity"] or parsed["violation_text"] or parsed["penalty_text"]:
                    if parsed["punished_entity"]:
                        parsed["title"] = f"{fallback.get('title', '')} - {parsed['punished_entity']}"
                    rows.append(parsed)
            if rows:
                continue

        for tr in table_rows:
            cells = [_clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue

            mapping: dict[str, str] = {}
            if len(cells) >= 8:
                # NFRA public tables are often flattened as label/value pairs in one long row.
                for i in range(0, len(cells) - 1, 2):
                    mapping[cells[i]] = cells[i + 1]
            else:
                mapping[cells[0]] = " ".join(cells[1:])

            parsed = _row_from_mapping(mapping, fallback)
            if parsed["decision_no"] or parsed["punished_entity"] or parsed["violation_text"] or parsed["penalty_text"]:
                rows.append(parsed)
    return rows


def _detail_rows(session: requests.Session, doc: dict[str, Any]) -> list[dict]:
    doc_id = str(doc.get("docId", ""))
    title = _clean(doc.get("docTitle") or doc.get("docSubtitle"))
    publish_time = _clean(doc.get("publishDate") or doc.get("builddate"))
    url = f"{BASE_URL}/cn/view/pages/ItemDetail.html?docId={doc_id}&itemId={ITEM_ID}&generaltype={doc.get('generaltype', '')}"
    fallback = {
        "title": title,
        "publish_time": publish_time,
        "decision_no": _clean(doc.get("documentNo")),
        "url": url,
        "crawl_time": _now(),
    }
    try:
        data = _get_json(session, DETAIL_API, {"docId": doc_id}).get("data") or {}
        fallback["decision_no"] = _clean(data.get("documentNo")) or fallback["decision_no"]
        fallback["title"] = _clean(data.get("docTitle") or data.get("docSubtitle")) or title
        fallback["publish_time"] = _clean(data.get("publishDate") or data.get("builddate")) or publish_time
        html = data.get("docClob") or ""
        rows = _parse_tables(html, fallback)
        if rows:
            return rows
    except Exception as exc:
        CRAWL_STATS["failed_pages"] += 1
        CRAWL_STATS["notes"].append(f"NFRA detail failed docId={doc_id}: {exc}")

    CRAWL_STATS["skipped_pages"] += 1
    return [
        {
            "source": SOURCE,
            "title": title,
            "publish_time": publish_time,
            "decision_no": fallback["decision_no"],
            "punished_entity": "",
            "violation_text": "",
            "penalty_text": "",
            "penalty_amount_raw": "",
            "agency": "",
            "url": url,
            "crawl_time": fallback["crawl_time"],
        }
    ]


def crawl() -> list[dict]:
    """
    返回当前网站的原始数据列表。
    每条数据是一个 dict。
    """
    CRAWL_STATS.update({"failed_pages": 0, "skipped_pages": 0, "notes": []})
    session = _session()
    results: list[dict] = []
    page = 1
    CRAWL_STATS["notes"].append("优先读取 NFRA 公开页面使用的静态 CDN JSON 缓存，避免动态接口限流。")
    while len(results) < MAX_ROWS and page <= 6:
        try:
            payload = _get_json(
                session,
                LIST_API,
                {"itemId": ITEM_ID, "pageIndex": page, "pageSize": PAGE_SIZE},
            )
            docs = ((payload.get("data") or {}).get("rows")) or []
            if not docs:
                break
        except Exception as exc:
            CRAWL_STATS["failed_pages"] += 1
            CRAWL_STATS["notes"].append(f"NFRA list failed page={page}: {exc}")
            break

        for doc in docs:
            results.extend(_detail_rows(session, doc))
            if len(results) >= MAX_ROWS:
                break
            time.sleep(0.05)
        page += 1
    return results[:MAX_ROWS]
