from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline_paths import analysis_dir, processed_dir  # noqa: E402


def is_high_risk(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().eq("high")


def is_negative(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().eq("negative")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", default="finance", help="finance or medical")
    args = parser.parse_args()

    input_path = processed_dir(args.industry) / "risk_event_table.csv"
    output_dir = analysis_dir(args.industry)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Missing {input_path}; run build_risk_event_table.py first.")
        return

    df = pd.read_csv(input_path, keep_default_na=False)
    df["event_date"] = pd.to_datetime(df.get("event_date"), errors="coerce")
    df["month"] = df["event_date"].dt.to_period("M").astype(str).replace("NaT", "unknown")
    df["penalty_amount"] = pd.to_numeric(df.get("penalty_amount", 0), errors="coerce").fillna(0)
    df["risk_score"] = pd.to_numeric(df.get("risk_score", 0), errors="coerce").fillna(0)
    df["sentiment_score"] = pd.to_numeric(df.get("sentiment_score", 0), errors="coerce").fillna(0)
    df["entity_name"] = df.get("entity_name", "").fillna("").astype(str).str.strip()
    df["entity_type"] = df.get("entity_type", "").fillna("").astype(str).str.strip().replace("", "other")
    df["region"] = df.get("region", "").fillna("").astype(str).str.strip().replace("", "unknown")
    df["risk_level"] = df.get("risk_level", "").fillna("").astype(str).str.strip().str.lower()
    df["sentiment"] = df.get("sentiment", "").fillna("").astype(str).str.strip().str.lower()

    total_events = float(len(df))
    negative_mask = is_negative(df["sentiment"])
    high_risk_mask = is_high_risk(df["risk_level"])

    summary_data = {
        "metric": [
            "total_events",
            "regulation_events",
            "news_events",
            "comment_events",
            "high_risk_events",
            "total_penalty_amount",
            "negative_sentiment_ratio",
        ],
        "value": [
            total_events,
            float((df["source_type"] == "regulation").sum()),
            float((df["source_type"] == "news").sum()),
            float((df["source_type"] == "comment").sum()),
            float(high_risk_mask.sum()),
            float(df["penalty_amount"].sum()),
            round(float(negative_mask.mean()) if total_events > 0 else 0.0, 4),
        ],
    }
    pd.DataFrame(summary_data).to_csv(output_dir / "summary_stats.csv", index=False, encoding="utf-8-sig")

    type_stats = (
        df.groupby("risk_type", dropna=False)
        .agg(
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
            high_risk_count=("risk_level", lambda values: values.fillna("").astype(str).str.lower().eq("high").sum()),
        )
        .reset_index()
    )
    type_stats.to_csv(output_dir / "risk_type_stats.csv", index=False, encoding="utf-8-sig")

    time_trend = (
        df.groupby("month", dropna=False)
        .agg(
            regulation_count=("source_type", lambda values: (values == "regulation").sum()),
            news_count=("source_type", lambda values: (values == "news").sum()),
            comment_count=("source_type", lambda values: (values == "comment").sum()),
            high_risk_count=("risk_level", lambda values: values.fillna("").astype(str).str.lower().eq("high").sum()),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
        .sort_values("month")
    )
    time_trend.to_csv(output_dir / "risk_time_trend.csv", index=False, encoding="utf-8-sig")

    region_stats = (
        df.groupby("region", dropna=False)
        .agg(
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            high_risk_count=("risk_level", lambda values: values.fillna("").astype(str).str.lower().eq("high").sum()),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
        .sort_values(["event_count", "avg_risk_score"], ascending=[False, False])
    )
    region_stats.to_csv(output_dir / "region_risk_stats.csv", index=False, encoding="utf-8-sig")

    entity_df = df[~df["entity_name"].isin(["", "unknown_entity"])].copy()
    entity_stats = (
        entity_df.groupby("entity_name", dropna=False)
        .agg(
            entity_type=("entity_type", "first"),
            region=("region", "first"),
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
        .sort_values(["avg_risk_score", "event_count"], ascending=[False, False])
    )
    entity_stats["risk_level"] = entity_stats["avg_risk_score"].apply(
        lambda value: "high" if value > 60 else ("medium" if value > 30 else "low")
    )
    entity_stats.to_csv(output_dir / "entity_risk_rank.csv", index=False, encoding="utf-8-sig")

    sent_trend = (
        df.groupby("month", dropna=False)
        .agg(
            negative_news_count=("record_id", lambda idx: ((df.loc[idx.index, "source_type"] == "news") & negative_mask.loc[idx.index]).sum()),
            negative_comment_count=("record_id", lambda idx: ((df.loc[idx.index, "source_type"] == "comment") & negative_mask.loc[idx.index]).sum()),
            avg_sentiment_score=("sentiment_score", "mean"),
            total_in_month=("record_id", "count"),
        )
        .reset_index()
        .sort_values("month")
    )
    sent_trend["negative_ratio"] = (
        (sent_trend["negative_news_count"] + sent_trend["negative_comment_count"]) / sent_trend["total_in_month"]
    ).round(4)
    sent_trend = sent_trend[["month", "negative_news_count", "negative_comment_count", "negative_ratio", "avg_sentiment_score"]]
    sent_trend.to_csv(output_dir / "sentiment_trend.csv", index=False, encoding="utf-8-sig")

    relation = (
        df.groupby(["entity_type", "risk_type"], dropna=False)
        .agg(event_count=("record_id", "count"), avg_risk_score=("risk_score", "mean"))
        .reset_index()
    )
    relation.to_csv(output_dir / "risk_relation_matrix.csv", index=False, encoding="utf-8-sig")

    high_df = df[(df["risk_score"] > 40) & (~df["entity_name"].isin(["", "unknown_entity"]))].sort_values(
        by="risk_score", ascending=False
    ).head(10)
    cases_df = pd.DataFrame(
        {
            "entity_name": high_df["entity_name"].tolist(),
            "warning_reason": high_df["violation_reason"].tolist(),
            "evidence_sources": high_df["source_type"].tolist(),
            "risk_score": high_df["risk_score"].tolist(),
            "suggested_action": ["add to manual review queue and verify against source URL"] * len(high_df),
        }
    )
    cases_df.to_csv(output_dir / "risk_warning_cases.csv", index=False, encoding="utf-8-sig")
    print(f"Analysis completed: {output_dir}")


if __name__ == "__main__":
    main()
