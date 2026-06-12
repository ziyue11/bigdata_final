import pandas as pd
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
    # 统一日期格式
    if 'event_date' in risk_event.columns:
        risk_event['event_date'] = pd.to_datetime(risk_event['event_date'], errors='coerce')
    data['risk_event'] = risk_event
    
    # 分析统计表
    summary = pd.read_csv(DATA_ANALYSIS / "summary_stats.csv", encoding='utf-8')
    risk_type = pd.read_csv(DATA_ANALYSIS / "risk_type_stats.csv", encoding='utf-8')
    time_trend = pd.read_csv(DATA_ANALYSIS / "risk_time_trend.csv", encoding='utf-8')
    region = pd.read_csv(DATA_ANALYSIS / "region_risk_stats.csv", encoding='utf-8')
    entity = pd.read_csv(DATA_ANALYSIS / "entity_risk_rank.csv", encoding='utf-8')
    sentiment = pd.read_csv(DATA_ANALYSIS / "sentiment_trend.csv", encoding='utf-8')
    relation = pd.read_csv(DATA_ANALYSIS / "risk_relation_matrix.csv", encoding='utf-8')
    warning = pd.read_csv(DATA_ANALYSIS / "risk_warning_cases.csv", encoding='utf-8')
    
    # 时间趋势表月份格式化
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
    """
    对 risk_event 明细表进行多条件筛选
    """
    filtered = df.copy()
    
    # 日期范围筛选
    if date_range and len(date_range) == 2:
        start, end = date_range
        if pd.notna(start) and pd.notna(end):
            filtered = filtered[(filtered['event_date'] >= start) & (filtered['event_date'] <= end)]
    
    # 来源类型筛选 (source_type列: regulation, news, comment)
    if source_types and len(source_types) > 0:
        filtered = filtered[filtered['source_type'].isin(source_types)]
    
    # 风险类型筛选
    if risk_types and len(risk_types) > 0:
        filtered = filtered[filtered['risk_type'].isin(risk_types)]
    
    # 风险等级筛选
    if risk_levels and len(risk_levels) > 0:
        filtered = filtered[filtered['risk_level'].isin(risk_levels)]
    
    # 地区筛选
    if regions and len(regions) > 0:
        filtered = filtered[filtered['region'].isin(regions)]
    
    # 主体类型筛选
    if entity_types and len(entity_types) > 0:
        filtered = filtered[filtered['entity_type'].isin(entity_types)]
    
    # 关键词搜索（在entity_name、summary、violation_reason中搜索）
    if search_keyword and search_keyword.strip():
        keyword = search_keyword.strip().lower()
        mask = (
            filtered['entity_name'].fillna('').str.lower().str.contains(keyword) |
            filtered['summary'].fillna('').str.lower().str.contains(keyword) |
            filtered['violation_reason'].fillna('').str.lower().str.contains(keyword)
        )
        filtered = filtered[mask]
    
    return filtered