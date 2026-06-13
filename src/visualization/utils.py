import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_ANALYSIS = PROJECT_ROOT / "data" / "analysis"


def load_all_data() -> Dict[str, pd.DataFrame]:
    """加载所有需要的CSV文件，返回字典"""
    data = {}

    # 明细表
    risk_event = pd.read_csv(DATA_PROCESSED / "risk_event_table.csv", encoding='utf-8')
    if 'event_date' in risk_event.columns:
        risk_event['event_date'] = pd.to_datetime(risk_event['event_date'], errors='coerce')
    if 'record_id' not in risk_event.columns:
        risk_event['record_id'] = risk_event.index
    data['risk_event'] = risk_event

    # 分析统计表（保留备用，但图表将使用动态聚合）
    summary = pd.read_csv(DATA_ANALYSIS / "summary_stats.csv", encoding='utf-8')
    risk_type = pd.read_csv(DATA_ANALYSIS / "risk_type_stats.csv", encoding='utf-8')
    time_trend = pd.read_csv(DATA_ANALYSIS / "risk_time_trend.csv", encoding='utf-8')
    region = pd.read_csv(DATA_ANALYSIS / "region_risk_stats.csv", encoding='utf-8')
    entity = pd.read_csv(DATA_ANALYSIS / "entity_risk_rank.csv", encoding='utf-8')
    sentiment = pd.read_csv(DATA_ANALYSIS / "sentiment_trend.csv", encoding='utf-8')
    relation = pd.read_csv(DATA_ANALYSIS / "risk_relation_matrix.csv", encoding='utf-8')
    warning = pd.read_csv(DATA_ANALYSIS / "risk_warning_cases.csv", encoding='utf-8')

    if 'month' in time_trend.columns:
        time_trend['month'] = pd.to_datetime(time_trend['month'], format='%Y-%m', errors='coerce')
    if 'month' in sentiment.columns:
        sentiment['month'] = pd.to_datetime(sentiment['month'], format='%Y-%m', errors='coerce')

    data['summary'] = summary
    data['risk_type'] = risk_type
    data['time_trend'] = time_trend
    data['region'] = region
    data['entity'] = entity
    data['sentiment'] = sentiment
    data['relation'] = relation
    data['warning'] = warning

    return data


def apply_filters(
    df: pd.DataFrame,
    date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]] = None,
    source_types: list = None,
    risk_types: list = None,
    risk_levels: list = None,
    regions: list = None,
    entity_types: list = None,
    search_keyword: str = ""
) -> pd.DataFrame:
    """对 risk_event 明细表进行多条件筛选"""
    filtered = df.copy()

    if date_range and len(date_range) == 2:
        start, end = date_range
        if pd.notna(start) and pd.notna(end):
            filtered = filtered[(filtered['event_date'] >= start) & (filtered['event_date'] <= end)]

    if source_types and len(source_types) > 0:
        filtered = filtered[filtered['source_type'].isin(source_types)]

    if risk_types and len(risk_types) > 0:
        filtered = filtered[filtered['risk_type'].isin(risk_types)]

    if risk_levels and len(risk_levels) > 0:
        filtered = filtered[filtered['risk_level'].isin(risk_levels)]

    if regions and len(regions) > 0:
        filtered = filtered[filtered['region'].isin(regions)]

    if entity_types and len(entity_types) > 0:
        filtered = filtered[filtered['entity_type'].isin(entity_types)]

    if search_keyword and search_keyword.strip():
        keyword = search_keyword.strip().lower()
        mask = (
            filtered['entity_name'].fillna('').str.lower().str.contains(keyword) |
            filtered['summary'].fillna('').str.lower().str.contains(keyword) |
            filtered['violation_reason'].fillna('').str.lower().str.contains(keyword)
        )
        filtered = filtered[mask]

    return filtered


@st.cache_data
def aggregate_time_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按月份聚合风险事件，生成时间趋势表"""
    if df.empty:
        return pd.DataFrame(columns=['month', 'regulation_count', 'news_count', 'comment_count',
                                     'high_risk_count', 'total_penalty_amount', 'avg_risk_score'])
    df_copy = df.copy()
    df_copy['month'] = df_copy['event_date'].dt.to_period('M').dt.strftime('%Y-%m')
    grouped = df_copy.groupby('month').agg(
        regulation_count=('source_type', lambda x: (x == 'regulation').sum()),
        news_count=('source_type', lambda x: (x == 'news').sum()),
        comment_count=('source_type', lambda x: (x == 'comment').sum()),
        high_risk_count=('risk_level', lambda x: (x == '高').sum()),
        total_penalty_amount=('penalty_amount', 'sum'),
        avg_risk_score=('risk_score', 'mean')
    ).reset_index()
    grouped['month'] = pd.to_datetime(grouped['month'], format='%Y-%m')
    return grouped.sort_values('month')


@st.cache_data
def aggregate_risk_type(df: pd.DataFrame) -> pd.DataFrame:
    """按风险类型聚合"""
    if df.empty:
        return pd.DataFrame(columns=['risk_type', 'event_count', 'total_penalty_amount', 'avg_risk_score', 'high_risk_count'])
    grouped = df.groupby('risk_type').agg(
        event_count=('record_id', 'count'),
        total_penalty_amount=('penalty_amount', 'sum'),
        avg_risk_score=('risk_score', 'mean'),
        high_risk_count=('risk_level', lambda x: (x == '高').sum())
    ).reset_index()
    return grouped


@st.cache_data
def aggregate_region(df: pd.DataFrame) -> pd.DataFrame:
    """按地区聚合"""
    if df.empty:
        return pd.DataFrame(columns=['region', 'event_count', 'total_penalty_amount', 'high_risk_count', 'avg_risk_score'])
    grouped = df.groupby('region').agg(
        event_count=('record_id', 'count'),
        total_penalty_amount=('penalty_amount', 'sum'),
        high_risk_count=('risk_level', lambda x: (x == '高').sum()),
        avg_risk_score=('risk_score', 'mean')
    ).reset_index()
    return grouped


@st.cache_data
def aggregate_entity(df: pd.DataFrame) -> pd.DataFrame:
    """按主体聚合"""
    if df.empty:
        return pd.DataFrame(columns=['entity_name', 'entity_type', 'region', 'event_count',
                                     'total_penalty_amount', 'avg_risk_score', 'risk_level'])
    grouped = df.groupby(['entity_name', 'entity_type', 'region']).agg(
        event_count=('record_id', 'count'),
        total_penalty_amount=('penalty_amount', 'sum'),
        avg_risk_score=('risk_score', 'mean')
    ).reset_index()

    def classify_risk(score):
        if score >= 50:
            return '高'
        elif score >= 30:
            return '中'
        else:
            return '低'

    grouped['risk_level'] = grouped['avg_risk_score'].apply(classify_risk)
    return grouped


@st.cache_data
def aggregate_sentiment_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按月聚合情绪指标"""
    if df.empty:
        return pd.DataFrame(columns=['month', 'negative_news_count', 'negative_comment_count',
                                     'negative_ratio', 'avg_sentiment_score'])
    df_copy = df.copy()
    df_copy['month'] = df_copy['event_date'].dt.to_period('M').dt.strftime('%Y-%m')
    # 负面事件：sentiment == '负面' 或 sentiment_score < 0
    df_copy['is_negative'] = (df_copy['sentiment'] == '负面') | (df_copy['sentiment_score'] < 0)

    # 计算负面新闻数和负面评论数
    negative_news = df_copy[(df_copy['source_type'] == 'news') & df_copy['is_negative']].groupby('month').size()
    negative_comment = df_copy[(df_copy['source_type'] == 'comment') & df_copy['is_negative']].groupby('month').size()
    total_news = df_copy[df_copy['source_type'] == 'news'].groupby('month').size()
    total_comment = df_copy[df_copy['source_type'] == 'comment'].groupby('month').size()

    # 平均情绪分
    sentiment_by_month = df_copy.groupby('month')['sentiment_score'].mean()

    # 合并
    months = df_copy['month'].unique()
    result = []
    for m in months:
        neg_news = negative_news.get(m, 0)
        neg_comm = negative_comment.get(m, 0)
        tot_news = total_news.get(m, 0)
        tot_comm = total_comment.get(m, 0)
        total_events = tot_news + tot_comm
        neg_ratio = (neg_news + neg_comm) / total_events if total_events > 0 else 0
        result.append({
            'month': pd.to_datetime(m, format='%Y-%m'),
            'negative_news_count': neg_news,
            'negative_comment_count': neg_comm,
            'negative_ratio': neg_ratio,
            'avg_sentiment_score': sentiment_by_month.get(m, 0)
        })
    df_result = pd.DataFrame(result).sort_values('month')
    return df_result


@st.cache_data
def aggregate_relation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """交叉表：entity_type × risk_type 事件数"""
    if df.empty:
        return pd.DataFrame(columns=['entity_type', 'risk_type', 'event_count', 'avg_risk_score'])
    grouped = df.groupby(['entity_type', 'risk_type']).agg(
        event_count=('record_id', 'count'),
        avg_risk_score=('risk_score', 'mean')
    ).reset_index()
    return grouped