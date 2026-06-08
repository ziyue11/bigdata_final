import csv
import html
import re
from datetime import datetime
from pathlib import Path


INVALID_TEXT_MARKERS = (
    "免责声明",
    "版权所有",
    "导航",
    "返回首页",
    "关闭窗口",
    "打印",
)

ENTITY_SUFFIXES = (
    "股份有限公司",
    "有限责任公司",
    "证券有限公司",
    "基金管理有限公司",
    "资产管理有限公司",
    "保险有限公司",
    "信托有限公司",
    "期货有限公司",
    "农商银行",
    "商业银行",
    "银行",
    "证券",
    "保险",
    "集团",
    "股份",
    "公司",
    "基金",
    "信托",
    "期货",
)

REGIONS = (
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门", "深圳", "厦门",
    "青岛", "宁波", "大连",
)


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_text(value):
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n+ *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def normalize_date(publish_time, crawl_time=""):
    raw = str(publish_time or "").strip()
    if not raw:
        return ""
    raw = raw.replace("/", "-")
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日",
        "%m-%d %H:%M",
        "%m-%d",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if "%Y" not in fmt:
                dt = dt.replace(year=_year_from_crawl_time(crawl_time))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(\d{4})[-年.](\d{1,2})[-月.](\d{1,2})", raw)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{1,2})[-月.](\d{1,2})", raw)
    if match:
        month, day = match.groups()
        return f"{_year_from_crawl_time(crawl_time):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def _year_from_crawl_time(crawl_time):
    match = re.search(r"(\d{4})", str(crawl_time or ""))
    return int(match.group(1)) if match else datetime.now().year


def parse_number(value):
    text = str(value or "").strip().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return int(float(match.group(0))) if match else 0


def parse_penalty_amount(*values):
    for value in values:
        amount = _parse_penalty_amount_from_text(value)
        if amount > 0:
            return amount
    return 0


def _parse_penalty_amount_from_text(value):
    text = clean_text(value)
    compact = re.sub(r"\s+", "", text).replace(",", "")
    amounts = []
    seen_spans = set()
    for match in re.finditer(r"(?:罚款|处以|并处|罚金)[^。；;，,]{0,30}?(\d+(?:\.\d+)?)(亿元|万元|元)", compact):
        amount_span = match.span(1)
        if amount_span in seen_spans:
            continue
        seen_spans.add(amount_span)
        amounts.append(_to_wan(match.group(1), match.group(2)))
    for match in re.finditer(r"(\d+(?:\.\d+)?)(亿元|万元|元)[^。；;，,]{0,12}?罚款", compact):
        amount_span = match.span(1)
        if amount_span in seen_spans:
            continue
        seen_spans.add(amount_span)
        amounts.append(_to_wan(match.group(1), match.group(2)))
    return round(sum(amounts), 4) if amounts else 0


def _to_wan(number, unit):
    value = float(number)
    if unit == "亿元":
        return value * 10000
    if unit == "元":
        return value / 10000
    return value


def extract_entity(*values):
    text = clean_text(" ".join(str(v or "") for v in values))
    suffix = "|".join(map(re.escape, ENTITY_SUFFIXES))
    pattern = re.compile(rf"[\u4e00-\u9fa5A-Za-z0-9（）()·]{2,40}(?:{suffix})")
    matches = []
    for match in pattern.finditer(text):
        entity = match.group(0).strip(" ，。、；:：()（）[]【】")
        if len(entity) <= 40 and not entity.startswith(("关于", "根据", "上述", "相关")):
            matches.append(entity)
    return matches[0] if matches else ""


def extract_region(*values):
    text = clean_text(" ".join(str(v or "") for v in values))
    for region in REGIONS:
        if region in text:
            return region
    return ""


def is_invalid_record(title, text, url):
    title = clean_text(title)
    text = clean_text(text)
    if not clean_text(url):
        return True
    if not title and not text:
        return True
    compact = re.sub(r"\s+", "", text)
    if compact and len(compact) <= 30 and any(marker in compact for marker in INVALID_TEXT_MARKERS):
        return True
    return False


def non_empty_rate(rows, field):
    if not rows:
        return 0.0
    count = sum(1 for row in rows if str(row.get(field, "")).strip())
    return count / len(rows)


def make_record_id(prefix, index):
    return f"{prefix}_{index:06d}"
