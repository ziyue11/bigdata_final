from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src"))
from pipeline_paths import analysis_dir, processed_dir  # noqa: E402


def load_all_data(industry: str = "finance") -> Dict[str, pd.DataFrame]:
    data = {}
    data_processed = processed_dir(industry)
    data_analysis = analysis_dir(industry)

    risk_event = pd.read_csv(data_processed / "risk_event_table.csv", encoding="utf-8")
    if "event_date" in risk_event.columns:
        risk_event["event_date"] = pd.to_datetime(risk_event["event_date"], errors="coerce")
    if "record_id" not in risk_event.columns:
        risk_event["record_id"] = risk_event.index
    data["risk_event"] = risk_event

    summary = pd.read_csv(data_analysis / "summary_stats.csv", encoding="utf-8")
    risk_type = pd.read_csv(data_analysis / "risk_type_stats.csv", encoding="utf-8")
    time_trend = pd.read_csv(data_analysis / "risk_time_trend.csv", encoding="utf-8")
    region = pd.read_csv(data_analysis / "region_risk_stats.csv", encoding="utf-8")
    entity = pd.read_csv(data_analysis / "entity_risk_rank.csv", encoding="utf-8")
    sentiment = pd.read_csv(data_analysis / "sentiment_trend.csv", encoding="utf-8")
    relation = pd.read_csv(data_analysis / "risk_relation_matrix.csv", encoding="utf-8")
    warning = pd.read_csv(data_analysis / "risk_warning_cases.csv", encoding="utf-8")

    if "month" in time_trend.columns:
        time_trend["month"] = pd.to_datetime(time_trend["month"], format="%Y-%m", errors="coerce")
    if "month" in sentiment.columns:
        sentiment["month"] = pd.to_datetime(sentiment["month"], format="%Y-%m", errors="coerce")

    data["summary"] = summary
    data["risk_type"] = risk_type
    data["time_trend"] = time_trend
    data["region"] = region
    data["entity"] = entity
    data["sentiment"] = sentiment
    data["relation"] = relation
    data["warning"] = warning
    return data


def apply_filters(
    df: pd.DataFrame,
    date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]] = None,
    source_types: list | None = None,
    risk_types: list | None = None,
    risk_levels: list | None = None,
    regions: list | None = None,
    entity_types: list | None = None,
    search_keyword: str = "",
) -> pd.DataFrame:
    filtered = df.copy()

    if date_range and len(date_range) == 2:
        start, end = date_range
        if pd.notna(start) and pd.notna(end):
            filtered = filtered[(filtered["event_date"] >= start) & (filtered["event_date"] <= end)]

    if source_types:
        filtered = filtered[filtered["source_type"].isin(source_types)]
    if risk_types:
        filtered = filtered[filtered["risk_type"].isin(risk_types)]
    if risk_levels:
        filtered = filtered[filtered["risk_level"].isin(risk_levels)]
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if entity_types:
        filtered = filtered[filtered["entity_type"].isin(entity_types)]

    if search_keyword and search_keyword.strip():
        keyword = search_keyword.strip().lower()
        mask = (
            filtered["entity_name"].fillna("").astype(str).str.lower().str.contains(keyword)
            | filtered["summary"].fillna("").astype(str).str.lower().str.contains(keyword)
            | filtered["violation_reason"].fillna("").astype(str).str.lower().str.contains(keyword)
        )
        filtered = filtered[mask]

    return filtered


def _is_high_risk(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().isin(["high", "高"])


def _is_negative(series: pd.Series, score_series: pd.Series | None = None) -> pd.Series:
    text_mask = series.fillna("").astype(str).str.strip().str.lower().isin(["negative", "负面"])
    if score_series is None:
        return text_mask
    score_mask = pd.to_numeric(score_series, errors="coerce").fillna(0) < 0
    return text_mask | score_mask


@st.cache_data
def aggregate_time_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["month", "regulation_count", "news_count", "comment_count", "high_risk_count", "total_penalty_amount", "avg_risk_score"]
        )
    df_copy = df.copy()
    df_copy["month"] = df_copy["event_date"].dt.to_period("M").dt.strftime("%Y-%m")
    grouped = (
        df_copy.groupby("month")
        .agg(
            regulation_count=("source_type", lambda x: (x == "regulation").sum()),
            news_count=("source_type", lambda x: (x == "news").sum()),
            comment_count=("source_type", lambda x: (x == "comment").sum()),
            high_risk_count=("risk_level", lambda x: _is_high_risk(x).sum()),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
    )
    grouped["month"] = pd.to_datetime(grouped["month"], format="%Y-%m")
    return grouped.sort_values("month")


@st.cache_data
def aggregate_risk_type(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["risk_type", "event_count", "total_penalty_amount", "avg_risk_score", "high_risk_count"])
    return (
        df.groupby("risk_type")
        .agg(
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
            high_risk_count=("risk_level", lambda x: _is_high_risk(x).sum()),
        )
        .reset_index()
    )


@st.cache_data
def aggregate_region(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["region", "event_count", "total_penalty_amount", "high_risk_count", "avg_risk_score"])
    return (
        df.groupby("region")
        .agg(
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            high_risk_count=("risk_level", lambda x: _is_high_risk(x).sum()),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
    )


@st.cache_data
def aggregate_entity(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["entity_name", "entity_type", "region", "event_count", "total_penalty_amount", "avg_risk_score", "risk_level"])
    grouped = (
        df.groupby(["entity_name", "entity_type", "region"])
        .agg(
            event_count=("record_id", "count"),
            total_penalty_amount=("penalty_amount", "sum"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
    )

    def classify_risk(score: float) -> str:
        if score >= 50:
            return "高"
        if score >= 30:
            return "中"
        return "低"

    grouped["risk_level"] = grouped["avg_risk_score"].apply(classify_risk)
    return grouped


@st.cache_data
def aggregate_sentiment_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "negative_news_count", "negative_comment_count", "negative_ratio", "avg_sentiment_score"])
    df_copy = df.copy()
    df_copy["month"] = df_copy["event_date"].dt.to_period("M").dt.strftime("%Y-%m")
    df_copy["is_negative"] = _is_negative(df_copy["sentiment"], df_copy["sentiment_score"])

    negative_news = df_copy[(df_copy["source_type"] == "news") & df_copy["is_negative"]].groupby("month").size()
    negative_comment = df_copy[(df_copy["source_type"] == "comment") & df_copy["is_negative"]].groupby("month").size()
    total_news = df_copy[df_copy["source_type"] == "news"].groupby("month").size()
    total_comment = df_copy[df_copy["source_type"] == "comment"].groupby("month").size()
    sentiment_by_month = df_copy.groupby("month")["sentiment_score"].mean()

    result = []
    for month in df_copy["month"].unique():
        neg_news = negative_news.get(month, 0)
        neg_comment = negative_comment.get(month, 0)
        tot_news = total_news.get(month, 0)
        tot_comment = total_comment.get(month, 0)
        total_events = tot_news + tot_comment
        result.append(
            {
                "month": pd.to_datetime(month, format="%Y-%m"),
                "negative_news_count": neg_news,
                "negative_comment_count": neg_comment,
                "negative_ratio": (neg_news + neg_comment) / total_events if total_events > 0 else 0,
                "avg_sentiment_score": sentiment_by_month.get(month, 0),
            }
        )
    return pd.DataFrame(result).sort_values("month")


@st.cache_data
def aggregate_relation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["entity_type", "risk_type", "event_count", "avg_risk_score"])
    return (
        df.groupby(["entity_type", "risk_type"])
        .agg(event_count=("record_id", "count"), avg_risk_score=("risk_score", "mean"))
        .reset_index()
    )
