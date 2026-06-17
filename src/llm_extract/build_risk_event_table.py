from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline_paths import processed_dir  # noqa: E402


def calculate_heat_score(row: pd.Series) -> float:
    source_type = str(row.get("source_type", "")).strip()
    if source_type == "comment":
        read_count = pd.to_numeric(row.get("read_count", 0), errors="coerce")
        comment_count = pd.to_numeric(row.get("comment_count", 0), errors="coerce")
        heat_raw = np.nan_to_num(read_count) + np.nan_to_num(comment_count) * 5
        return round(min(15.0, np.log1p(heat_raw) * 2), 1)
    if source_type == "news":
        return 10.0
    if source_type == "regulation":
        return 5.0
    return 0.0


def normalize_risk_level(value: object) -> str:
    text = str(value).strip().lower()
    mapping = {
        "high": "high",
        "medium": "medium",
        "low": "low",
        "高": "high",
        "中": "medium",
        "低": "low",
    }
    return mapping.get(text, "low")


def calculate_risk_score(row: pd.Series, entity_counts: dict[str, int]) -> float:
    level_score = {"high": 25.0, "medium": 15.0, "low": 5.0}.get(normalize_risk_level(row.get("risk_level")), 5.0)
    penalty_amount = pd.to_numeric(row.get("penalty_amount", 0), errors="coerce")
    penalty_score = min(20.0, np.log1p(penalty_amount) * 3) if pd.notna(penalty_amount) and penalty_amount > 0 else 0.0

    sentiment = str(row.get("sentiment", "")).strip().lower()
    sentiment_score = pd.to_numeric(row.get("sentiment_score", 0), errors="coerce")
    emotion_score = min(15.0, abs(np.nan_to_num(sentiment_score)) * 15) if sentiment == "negative" else 0.0

    heat_score = pd.to_numeric(row.get("heat_score", 0), errors="coerce")
    entity_name = str(row.get("entity_name", "")).strip()
    mention_count = entity_counts.get(entity_name, 1)
    repeat_score = 10.0 if mention_count > 5 else (5.0 if mention_count > 2 else 0.0)
    source_score = 15.0 if str(row.get("source_type", "")).strip() == "regulation" else 10.0
    total_score = source_score + level_score + penalty_score + emotion_score + np.nan_to_num(heat_score) + repeat_score
    return round(max(0.0, min(100.0, total_score)), 1)


def load_cleaned_metadata(base_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    regulation_path = base_dir / "regulation_cleaned.csv"
    if regulation_path.exists():
        df_reg = pd.read_csv(regulation_path)
        frames.append(
            pd.DataFrame(
                {
                    "record_id": df_reg.get("record_id"),
                    "event_date": df_reg.get("event_date"),
                    "source_type": "regulation",
                    "source": df_reg.get("source"),
                    "title": df_reg.get("title"),
                    "penalty_amount": df_reg.get("penalty_amount", 0),
                    "read_count": 0,
                    "comment_count": 0,
                    "url": df_reg.get("url"),
                }
            )
        )

    news_path = base_dir / "news_cleaned.csv"
    if news_path.exists():
        df_news = pd.read_csv(news_path)
        frames.append(
            pd.DataFrame(
                {
                    "record_id": df_news.get("record_id"),
                    "event_date": df_news.get("event_date"),
                    "source_type": "news",
                    "source": df_news.get("source"),
                    "title": df_news.get("title"),
                    "penalty_amount": 0,
                    "read_count": 0,
                    "comment_count": 0,
                    "url": df_news.get("url"),
                }
            )
        )

    comment_path = base_dir / "comment_cleaned.csv"
    if comment_path.exists():
        df_comment = pd.read_csv(comment_path)
        frames.append(
            pd.DataFrame(
                {
                    "record_id": df_comment.get("record_id"),
                    "event_date": df_comment.get("event_date"),
                    "source_type": "comment",
                    "source": df_comment.get("source"),
                    "title": df_comment.get("title"),
                    "penalty_amount": 0,
                    "read_count": df_comment.get("read_count", 0),
                    "comment_count": df_comment.get("comment_count", 0),
                    "url": df_comment.get("url"),
                }
            )
        )

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", default="economy", help="economy or medical")
    args = parser.parse_args()

    base_dir = processed_dir(args.industry)
    extracted_path = base_dir / "llm_extracted.csv"
    output_path = base_dir / "risk_event_table.csv"

    if not extracted_path.exists():
        print(f"Missing {extracted_path}; run extract_risk_fields.py first.")
        return

    df_llm = pd.read_csv(extracted_path, keep_default_na=False)
    df_meta = load_cleaned_metadata(base_dir)
    if df_meta.empty:
        print(f"No cleaned metadata found in {base_dir}")
        return

    entity_counts = (
        df_llm["entity_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "unknown_entity")
        .value_counts()
        .to_dict()
    )
    df_llm = df_llm.drop(columns=[column for column in ["source_type", "url"] if column in df_llm.columns])
    risk_event_table = pd.merge(df_llm, df_meta, on="record_id", how="left")

    risk_event_table["entity_name"] = (
        risk_event_table.get("entity_name", "")
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "unknown_entity")
    )
    risk_event_table["entity_type"] = risk_event_table.get("entity_type", "").fillna("").astype(str).str.strip().replace("", "other")
    risk_event_table["region"] = risk_event_table.get("region", "").fillna("").astype(str).str.strip().replace("", "unknown")
    risk_event_table["risk_level"] = risk_event_table.get("risk_level", "low").apply(normalize_risk_level)
    risk_event_table["sentiment"] = risk_event_table.get("sentiment", "neutral").fillna("neutral").astype(str).str.strip().str.lower()
    risk_event_table["penalty_amount"] = pd.to_numeric(risk_event_table.get("penalty_amount", 0), errors="coerce").fillna(0)
    risk_event_table["sentiment_score"] = pd.to_numeric(risk_event_table.get("sentiment_score", 0), errors="coerce").fillna(0)
    risk_event_table["heat_score"] = risk_event_table.apply(calculate_heat_score, axis=1)
    risk_event_table["manual_check"] = "pending_review"
    risk_event_table["risk_score"] = risk_event_table.apply(lambda row: calculate_risk_score(row, entity_counts), axis=1)

    columns_order = [
        "record_id",
        "event_date",
        "entity_name",
        "entity_type",
        "region",
        "risk_type",
        "risk_level",
        "risk_score",
        "sentiment",
        "sentiment_score",
        "violation_reason",
        "impact_scope",
        "penalty_amount",
        "heat_score",
        "summary",
        "source_type",
        "source",
        "title",
        "url",
        "llm_confidence",
        "manual_check",
    ]
    risk_event_table = risk_event_table[[column for column in columns_order if column in risk_event_table.columns]]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    risk_event_table.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Risk event table written: {output_path} ({len(risk_event_table)} rows)")


if __name__ == "__main__":
    main()
