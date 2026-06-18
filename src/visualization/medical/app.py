import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from utils import (
    load_all_data, apply_filters,
    aggregate_time_trend, aggregate_risk_type, aggregate_region,
    aggregate_entity, aggregate_sentiment_trend, aggregate_relation_matrix
)
from charts import (
    plot_time_trend, plot_risk_type_bar, plot_region_rank,
    plot_entity_rank, plot_sentiment_trend, plot_relation_heatmap,
    plot_risk_score_distribution
)

st.set_page_config(page_title="医疗风险预警看板", layout="wide", page_icon="🏥")

# 加载全局数据（用于筛选器选项和预警案例）
if 'data' not in st.session_state:
    with st.spinner("正在加载数据..."):
        try:
            st.session_state.data = load_all_data()
            st.success("数据加载成功！")
        except Exception as e:
            st.error(f"数据加载失败: {e}")
            st.stop()

data = st.session_state.data
risk_event = data['risk_event']
warning = data['warning']

# ========================== 侧边栏筛选器 ==========================
st.sidebar.title("🔍 医疗风险预警看板")

# 日期范围
if 'event_date' in risk_event.columns and not risk_event['event_date'].isna().all():
    min_date = risk_event['event_date'].min()
    max_date = risk_event['event_date'].max()
    if pd.isna(min_date):
        min_date = datetime(2020, 1, 1)
        max_date = datetime(2026, 6, 30)
    date_range = st.sidebar.date_input(
        "时间范围", [min_date.date(), max_date.date()],
        min_value=min_date.date(), max_value=max_date.date()
    )
else:
    date_range = [None, None]

source_options = ['regulation', 'news', 'comment']
source_selected = st.sidebar.multiselect("数据来源", source_options, default=source_options)

risk_type_options = list(data['risk_type']['risk_type'].unique())
risk_type_selected = st.sidebar.multiselect("风险类型", risk_type_options, default=risk_type_options)

risk_level_options = ['high', 'medium', 'low']
risk_level_selected = st.sidebar.multiselect("风险等级", risk_level_options, default=risk_level_options)

region_options = list(data['region']['region'].unique())
region_selected = st.sidebar.multiselect("地区", region_options, default=[])

entity_type_options = list(risk_event['entity_type'].unique())
entity_type_selected = st.sidebar.multiselect("主体类型", entity_type_options, default=[])

search_keyword = st.sidebar.text_input("🔎 关键词搜索 (机构/摘要)", placeholder="输入机构名称或风险描述")

# 应用筛选
filtered_events = apply_filters(
    risk_event,
    date_range=(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])) if date_range[0] else None,
    source_types=source_selected,
    risk_types=risk_type_selected,
    risk_levels=risk_level_selected,
    regions=region_selected,
    entity_types=entity_type_selected,
    search_keyword=search_keyword
)

# 动态聚合各图表所需数据
dynamic_time_trend = aggregate_time_trend(filtered_events)
dynamic_risk_type = aggregate_risk_type(filtered_events)
dynamic_region = aggregate_region(filtered_events)
dynamic_entity = aggregate_entity(filtered_events)
dynamic_sentiment = aggregate_sentiment_trend(filtered_events)
dynamic_relation = aggregate_relation_matrix(filtered_events)

# ========================== 顶部区域 ==========================
st.title("🏥 医疗行业风险与舆情预警看板")
st.markdown("---")

# 1️⃣ 先展示典型风险预警案例（不受筛选影响）
st.subheader("🚨 典型风险预警案例")
if not warning.empty:
    st.dataframe(warning[['entity_name', 'warning_reason', 'risk_score', 'suggested_action']], use_container_width=True)
else:
    st.info("暂无典型预警案例数据")
st.markdown("---")

# 2️⃣ 再显示当前筛选结果统计
total_events = len(filtered_events)
st.subheader(f"📌 当前筛选结果: 共 {total_events} 条风险事件")
st.markdown("---")

# 3️⃣ 然后显示四个指标卡片
high_risk_events = len(filtered_events[filtered_events['risk_level'] == 'high'])
total_penalty = filtered_events['penalty_amount'].sum()
neg_ratio = len(filtered_events[filtered_events['sentiment'] == 'negative']) / total_events if total_events > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 总风险事件", f"{total_events}")
with col2:
    st.metric("⚠️ 高风险事件", f"{high_risk_events}")
with col3:
    st.metric("💰 累计处罚金额", f"{total_penalty:.1f} 万元")
with col4:
    st.metric("😞 负面舆情比例", f"{neg_ratio * 100:.1f}%")

st.markdown("---")

# ========================== 图表区域 ==========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 时间趋势", "🏷️ 风险类型", "🗺️ 地区与主体", "📰 舆情联动", "🔗 关系矩阵"
])

with tab1:
    st.plotly_chart(plot_time_trend(dynamic_time_trend), use_container_width=True)
    col_left, col_right = st.columns(2)
    with col_left:
        st.plotly_chart(plot_risk_score_distribution(filtered_events), use_container_width=True)
    with col_right:
        high_cnt = len(filtered_events[filtered_events['risk_level'] == 'high'])
        medium_cnt = len(filtered_events[filtered_events['risk_level'] == 'medium'])
        low_cnt = len(filtered_events[filtered_events['risk_level'] == 'low'])
        pie_data = pd.DataFrame({
            '风险等级': ['高', '中', '低'],
            '事件数': [high_cnt, medium_cnt, low_cnt]
        })
        st.plotly_chart(px.pie(pie_data, names='风险等级', values='事件数', title='当前筛选结果风险等级分布'), use_container_width=True)

with tab2:
    st.plotly_chart(plot_risk_type_bar(dynamic_risk_type), use_container_width=True)
    st.dataframe(dynamic_risk_type[['risk_type', 'event_count', 'high_risk_count', 'avg_risk_score']].sort_values('avg_risk_score', ascending=False), use_container_width=True)

with tab3:
    col_left, col_right = st.columns(2)
    with col_left:
        top_n_region = st.slider("地区排行数量", 5, 20, 10, key="region_slider")
        st.plotly_chart(plot_region_rank(dynamic_region, top_n=top_n_region), use_container_width=True)
    with col_right:
        sort_by = st.selectbox("主体排行依据", ['avg_risk_score', 'event_count', 'total_penalty_amount'], key="entity_sort")
        top_n_entity = st.slider("主体排行数量", 5, 20, 10, key="entity_slider")
        st.plotly_chart(plot_entity_rank(dynamic_entity, top_n=top_n_entity, sort_by=sort_by), use_container_width=True)
    st.subheader("🏆 高风险机构排行榜")
    high_risk_entities = dynamic_entity[dynamic_entity['risk_level'] == 'high'].head(15)
    if not high_risk_entities.empty:
        st.dataframe(high_risk_entities[['entity_name', 'entity_type', 'region', 'event_count', 'total_penalty_amount', 'avg_risk_score']], use_container_width=True)
    else:
        st.info("当前筛选条件下无高风险机构")

with tab4:
    st.plotly_chart(plot_sentiment_trend(dynamic_sentiment, dynamic_time_trend), use_container_width=True)
    st.caption("注：负面事件比例 = 负面新闻数 / 当月总新闻数；情绪分越接近-1代表舆论越负面。舆情可作为风险辅助观察信号。")

with tab5:
    st.plotly_chart(plot_relation_heatmap(dynamic_relation), use_container_width=True)
    st.dataframe(dynamic_relation[['entity_type', 'risk_type', 'event_count', 'avg_risk_score']].sort_values('event_count', ascending=False), use_container_width=True)

# ========================== 明细事件表 ==========================
st.markdown("---")
st.subheader("📋 风险事件明细表")
st.caption("支持搜索、排序、点击链接查看原文")

display_cols = ['event_date', 'source_type', 'entity_name', 'entity_type', 'region',
                'risk_type', 'risk_level', 'risk_score', 'sentiment', 'penalty_amount', 'summary', 'url']
available_cols = [c for c in display_cols if c in filtered_events.columns]
if available_cols and not filtered_events.empty:
    st.dataframe(
        filtered_events[available_cols].sort_values('event_date', ascending=False),
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("原文链接"),
            "penalty_amount": st.column_config.NumberColumn("处罚金额(万元)", format="%.2f"),
            "risk_score": st.column_config.NumberColumn("风险分", format="%.1f")
        }
    )
    csv = filtered_events[available_cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 导出筛选结果CSV", csv, "filtered_risk_events.csv", "text/csv")
else:
    st.write("无明细数据")

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **数据说明**  
    - 数据来源: 监管处罚、新闻舆情、社交评论  
    - 风险评分: 基于LLM可解释规则计算  
    - 更新周期: 月频  
    - 看板版本: v2.0 (医疗行业适配)
    """
)