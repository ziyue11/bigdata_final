from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from openai import APIStatusError, OpenAI

from prompt_templates import PROMPTS

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline_paths import processed_dir  # noqa: E402


API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen-mt-flash")
MAX_QUOTA_RETRIES = int(os.getenv("LLM_MAX_QUOTA_RETRIES", "3"))
QUOTA_RETRY_DELAY_SECONDS = int(os.getenv("LLM_QUOTA_RETRY_DELAY_SECONDS", "60"))
MAX_TEXT_CHARS = int(os.getenv("LLM_MAX_TEXT_CHARS", "6000"))

OUTPUT_COLUMNS = [
    "entity_name",
    "entity_type",
    "region",
    "risk_type",
    "risk_level",
    "sentiment",
    "sentiment_score",
    "violation_reason",
    "impact_scope",
    "summary",
    "llm_confidence",
    "record_id",
    "source_type",
    "url",
]
FAILED_COLUMNS = ["record_id", "source_type", "title", "url", "error"]

client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", default="economy", help="economy or medical")
    parser.add_argument("--fallback", choices=["auto", "rule", "llm"], default="auto")
    args = parser.parse_args()

    industry = args.industry.strip().lower()
    base_dir = processed_dir(industry)
    output_path = base_dir / "llm_extracted.csv"
    failed_path = base_dir / "llm_failed_records.csv"

    df = load_cleaned_records(base_dir)
    if df.empty:
        print(f"No cleaned records found in {base_dir}")
        return

    use_rules = args.fallback == "rule" or (args.fallback == "auto" and client is None)
    if use_rules:
        extracted = [rule_extract(row, industry) for _, row in df.iterrows()]
        pd.DataFrame(extracted, columns=OUTPUT_COLUMNS).to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"Rule extraction completed for {industry}: {output_path}")
        return

    if client is None:
        print("No API key configured. Use --fallback rule or set an LLM API key.")
        return

    done_ids = load_done_record_ids(output_path)
    consecutive_failures = 0
    for index, row in df.iterrows():
        record_id = row["record_id"]
        if record_id in done_ids:
            continue
        combined_text = f"source_type: {row['source_type']}\ntitle: {row['title']}\ncontent: {truncate_text(row['text_content'])}"
        print(f"Processing {index + 1}/{len(df)} record_id={record_id}")
        llm_data = call_with_quota_retries(combined_text, industry)
        if llm_data == "quota_exhausted":
            append_failed_row_to_csv(
                failed_path,
                {"record_id": record_id, "source_type": row["source_type"], "title": row["title"], "url": row["url"], "error": "quota_exhausted"},
            )
            return
        if llm_data:
            llm_data["record_id"] = record_id
            llm_data["source_type"] = row["source_type"]
            llm_data["url"] = row["url"]
            append_row_to_csv(output_path, llm_data)
            done_ids.add(record_id)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            append_failed_row_to_csv(
                failed_path,
                {"record_id": record_id, "source_type": row["source_type"], "title": row["title"], "url": row["url"], "error": "LLM request or JSON parse failed"},
            )
            if consecutive_failures >= 5:
                return
    print(f"LLM extraction completed for {industry}: {output_path}")


def call_llm_json(text_content: str, industry: str) -> dict:
    prompt = PROMPTS.get(industry, PROMPTS["economy"]).format(text_content=text_content)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)


def load_cleaned_records(base_dir: Path) -> pd.DataFrame:
    records = []
    paths = [
        ("regulation", base_dir / "regulation_cleaned.csv", "raw_text", "entity_name"),
        ("news", base_dir / "news_cleaned.csv", "content", "mentioned_entity"),
        ("comment", base_dir / "comment_cleaned.csv", "content", "mentioned_entity"),
    ]
    for source_type, path, text_field, hint_field in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            entity_hint = row.get(hint_field, "")
            if pd.isna(entity_hint):
                entity_hint = ""
            records.append(
                {
                    "record_id": row.get("record_id", ""),
                    "source_type": source_type,
                    "title": row.get("title", ""),
                    "text_content": row.get(text_field, ""),
                    "url": row.get("url", ""),
                    "entity_hint": entity_hint,
                }
            )
    return pd.DataFrame(records)


def rule_extract(row: pd.Series, industry: str) -> dict:
    text = f"{safe_text(row.get('title'))} {safe_text(row.get('text_content'))}"
    if industry == "medical":
        return rule_extract_medical(row, text)
    return rule_extract_economy(row, text)


def rule_extract_medical(row: pd.Series, text: str) -> dict:
    risk_type = "other_risk"
    if any(word in text for word in ["药品", "疫苗", "假药", "劣药"]):
        risk_type = "drug_safety_risk"
    elif any(word in text for word in ["器械", "耗材", "设备"]):
        risk_type = "medical_device_risk"
    elif any(word in text for word in ["医保", "骗保", "报销"]):
        risk_type = "insurance_compliance_risk"
    elif any(word in text for word in ["价格", "收费", "乱收费"]):
        risk_type = "pricing_risk"
    elif any(word in text for word in ["广告", "宣传", "虚假"]):
        risk_type = "advertising_risk"
    elif any(word in text for word in ["投诉", "纠纷", "维权"]):
        risk_type = "dispute_risk"
    elif any(word in text for word in ["处罚", "监管", "违法", "违规"]):
        risk_type = "quality_compliance_risk"
    elif row.get("source_type") == "comment":
        risk_type = "public_opinion_risk"

    entity_type = "other"
    if "医院" in text:
        entity_type = "hospital"
    elif any(word in text for word in ["药业", "制药", "药企", "药房"]):
        entity_type = "pharma"
    elif "器械" in text:
        entity_type = "device_company"
    elif any(word in text for word in ["医美", "美容"]):
        entity_type = "medical_beauty"
    elif any(word in text for word in ["平台", "互联网医院"]):
        entity_type = "health_platform"

    negative_words = ["处罚", "违法", "违规", "投诉", "纠纷", "召回", "罚款", "骗保", "事故", "虚假"]
    sentiment = "negative" if any(word in text for word in negative_words) else "neutral"
    sentiment_score = -0.65 if sentiment == "negative" else 0.0
    risk_level = "high" if any(word in text for word in ["事故", "骗保", "假药", "重大", "吊销"]) else ("medium" if sentiment == "negative" else "low")
    return base_output(row, entity_type, risk_type, risk_level, sentiment, sentiment_score, "medical risk event derived from regulation or health news")


def rule_extract_economy(row: pd.Series, text: str) -> dict:
    risk_type = "compliance_risk" if any(word in text for word in ["处罚", "违法", "违规"]) else "public_opinion_risk"
    entity_type = "bank" if "银行" in text else ("insurance" if "保险" in text else ("securities" if "证券" in text else "other"))
    sentiment = "negative" if any(word in text for word in ["处罚", "投诉", "风险", "违规", "违法"]) else "neutral"
    sentiment_score = -0.6 if sentiment == "negative" else 0.0
    risk_level = "medium" if sentiment == "negative" else "low"
    return base_output(row, entity_type, risk_type, risk_level, sentiment, sentiment_score, "economy risk event derived from regulation or public text")


def base_output(row: pd.Series, entity_type: str, risk_type: str, risk_level: str, sentiment: str, sentiment_score: float, reason: str) -> dict:
    title = safe_text(row.get("title"))
    entity_hint = safe_text(row.get("entity_hint"))
    entity = entity_hint or guess_entity(title) or "unknown_entity"
    return {
        "entity_name": entity,
        "entity_type": entity_type,
        "region": guess_region(title),
        "risk_type": risk_type,
        "risk_level": risk_level,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "violation_reason": reason,
        "impact_scope": "institution, users/patients, sector supervision",
        "summary": title[:100],
        "llm_confidence": 0.55,
        "record_id": row.get("record_id", ""),
        "source_type": row.get("source_type", ""),
        "url": row.get("url", ""),
    }


def safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def guess_entity(text: str) -> str:
    match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]{2,40}(?:医院|卫生院|制药|药业|医药|医疗器械|公司|平台|药房))", text)
    return match.group(1) if match else ""


def guess_region(text: str) -> str:
    regions = "北京 上海 天津 重庆 广东 浙江 江苏 山东 河南 河北 四川 湖北 湖南 福建 安徽 江西 辽宁 吉林 黑龙江 陕西 山西 云南 贵州 广西 海南 甘肃 青海 宁夏 新疆 西藏 内蒙古 香港 澳门".split()
    for region in regions:
        if region in text:
            return region
    return "unknown"


def truncate_text(text) -> str:
    text = safe_text(text)
    if len(text) <= MAX_TEXT_CHARS:
        return text
    head_len = MAX_TEXT_CHARS // 2
    tail_len = MAX_TEXT_CHARS - head_len
    return text[:head_len] + "\n...truncated...\n" + text[-tail_len:]


def is_quota_error(error: Exception) -> bool:
    if isinstance(error, APIStatusError) and error.status_code == 429:
        return True
    text = str(error).lower()
    return "insufficient_quota" in text or "exceeded your current quota" in text


def call_with_quota_retries(text_content: str, industry: str):
    for attempt in range(MAX_QUOTA_RETRIES + 1):
        try:
            return call_llm_json(text_content, industry)
        except Exception as exc:
            if not is_quota_error(exc):
                print(f"LLM extraction failed: {exc}")
                return None
            if attempt >= MAX_QUOTA_RETRIES:
                return "quota_exhausted"
            time.sleep(QUOTA_RETRY_DELAY_SECONDS * (attempt + 1))


def load_done_record_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    try:
        df_done = pd.read_csv(output_path)
    except pd.errors.EmptyDataError:
        return set()
    if "record_id" not in df_done.columns:
        return set()
    return set(df_done["record_id"].dropna().astype(str))


def append_row_to_csv(output_path: Path, row: dict) -> None:
    normalized = {column: row.get(column, "") for column in OUTPUT_COLUMNS}
    df_row = pd.DataFrame([normalized], columns=OUTPUT_COLUMNS)
    write_header = not output_path.exists() or output_path.stat().st_size == 0
    df_row.to_csv(output_path, mode="a", index=False, header=write_header, encoding="utf-8-sig")


def append_failed_row_to_csv(output_path: Path, row: dict) -> None:
    normalized = {column: row.get(column, "") for column in FAILED_COLUMNS}
    df_row = pd.DataFrame([normalized], columns=FAILED_COLUMNS)
    write_header = not output_path.exists() or output_path.stat().st_size == 0
    df_row.to_csv(output_path, mode="a", index=False, header=write_header, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
