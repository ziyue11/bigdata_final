import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.append(str(Path(__file__).parent))

from utils import load_all_data, apply_filters
from charts import (
    plot_time_trend, plot_risk_type_bar, plot_region_rank,
    plot_entity_rank, plot_sentiment_trend, plot_relation_heatmap,
    plot_risk_score_distribution
)

# 页面配置
st.set_page_config(page_title="金融风险预警看板", layout="wide", page_icon="⚠️")

# 初始化session_state
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
summary = data['summary']
risk_type = data['risk_type']
time_trend = data['time_trend']
region = data['region']
entity = data['entity']
sentiment = data['sentiment']
relation = data['relation']
warning = data['warning']

# ========================== 侧边栏筛选器 ==========================
st.sidebar.image("https://img.icons8.com/color/96/000000/risk.png", width=80)
st.sidebar.title("🔍 筛选条件")

# 日期范围
if 'event_date' in risk_event.columns and not risk_event['event_date'].isna().all():
    min_date = risk_event['event_date'].min()
    max_date = risk_event['event_date'].max()
    if pd.isna(min_date):
        min_date = datetime(2020,1,1)
        max_date = datetime(2026,6,30)
    date_range = st.sidebar.date_input(
        "时间范围", [min_date.date(), max_date.date()],
        min_value=min_date.date(), max_value=max_date.date()
    )
else:
    date_range = [None, None]

# 来源类型
source_options = ['regulation', 'news', 'comment']
source_selected = st.sidebar.multiselect("数据来源", source_options, default=source_options)

# 风险类型
risk_type_options = list(risk_type['risk_type'].unique())
risk_type_selected = st.sidebar.multiselect("风险类型", risk_type_options, default=risk_type_options)

# 风险等级
risk_level_options = ['高', '中', '低']
risk_level_selected = st.sidebar.multiselect("风险等级", risk_level_options, default=risk_level_options)

# 地区
region_options = list(region['region'].unique())
region_selected = st.sidebar.multiselect("地区", region_options, default=[])

# 主体类型
entity_type_options = list(risk_event['entity_type'].unique())
entity_type_selected = st.sidebar.multiselect("主体类型", entity_type_options, default=[])

# 关键词搜索
search_keyword = st.sidebar.text_input("🔎 关键词搜索 (机构/摘要)", placeholder="输入机构名称或违规事由")

# 应用筛选（仅对明细表生效）
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

# ========================== 顶部指标卡片 ==========================
st.title("🏦 金融机构监管风险与舆情预警看板")
st.markdown("---")

# 从summary中提取指标字典
summary_dict = dict(zip(summary['metric'], summary['value']))

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 总风险事件", f"{summary_dict.get('total_events', 0):.0f}")
with col2:
    st.metric("⚠️ 高风险事件", f"{summary_dict.get('high_risk_events', 0):.0f}")
with col3:
    penalty = summary_dict.get('total_penalty_amount', 0)
    st.metric("💰 累计处罚金额", f"{penalty:.1f} 万元")
with col4:
    neg_ratio = summary_dict.get('negative_sentiment_ratio', 0)
    st.metric("😞 负面舆情比例", f"{neg_ratio*100:.1f}%")

# 动态筛选后统计
st.markdown("---")
st.subheader(f"📌 当前筛选结果: 共 {len(filtered_events)} 条风险事件")

# ========================== 图表区域 ==========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 时间趋势", "🏷️ 风险类型", "🗺️ 地区与主体", "📰 舆情联动", "🔗 关系矩阵"
])

with tab1:
    st.plotly_chart(plot_time_trend(time_trend), use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_risk_score_distribution(filtered_events), use_container_width=True)
    with col2:
        # 额外展示高风险事件占比饼图
        high_risk_count = len(filtered_events[filtered_events['risk_level']=='高'])
        medium_risk_count = len(filtered_events[filtered_events['risk_level']=='中'])
        low_risk_count = len(filtered_events[filtered_events['risk_level']=='低'])
        pie_data = pd.DataFrame({
            '风险等级': ['高', '中', '低'],
            '事件数': [high_risk_count, medium_risk_count, low_risk_count]
        })
        st.plotly_chart(px.pie(pie_data, names='风险等级', values='事件数', title='当前筛选结果风险等级分布'), use_container_width=True)

with tab2:
    st.plotly_chart(plot_risk_type_bar(risk_type), use_container_width=True)
    # 高风险类型详情表格
    st.dataframe(risk_type[['risk_type', 'event_count', 'high_risk_count', 'avg_risk_score']].sort_values('avg_risk_score', ascending=False), use_container_width=True)

with tab3:
    col_left, col_right = st.columns(2)
    with col_left:
        top_n_region = st.slider("地区排行数量", 5, 20, 10, key="region_slider")
        st.plotly_chart(plot_region_rank(region, top_n=top_n_region), use_container_width=True)
    with col_right:
        sort_by = st.selectbox("主体排行依据", ['avg_risk_score', 'event_count', 'total_penalty_amount'], key="entity_sort")
        top_n_entity = st.slider("主体排行数量", 5, 20, 10, key="entity_slider")
        st.plotly_chart(plot_entity_rank(entity, top_n=top_n_entity, sort_by=sort_by), use_container_width=True)
    
    # 高风险主体表格
    st.subheader("🏆 高风险机构排行榜")
    st.dataframe(entity[entity['risk_level']=='高'].head(15)[['entity_name','entity_type','region','event_count','total_penalty_amount','avg_risk_score']], use_container_width=True)

with tab4:
    st.plotly_chart(plot_sentiment_trend(sentiment, time_trend), use_container_width=True)
    st.caption("注：负面事件比例 = 负面新闻数 / 当月总新闻数；情绪分越接近-1代表舆论越负面。舆情可作为风险辅助观察信号。")

with tab5:
    st.plotly_chart(plot_relation_heatmap(relation), use_container_width=True)
    st.dataframe(relation[['entity_type','risk_type','event_count','avg_risk_score']].sort_values('event_count', ascending=False), use_container_width=True)

# ========================== 风险预警案例展示 ==========================
st.markdown("---")
st.subheader("🚨 典型风险预警案例")
if not warning.empty:
    # 轮播效果或用表格展示
    st.dataframe(warning[['entity_name','warning_reason','risk_score','suggested_action']], use_container_width=True)
else:
    st.info("暂无典型预警案例数据")

# ========================== 明细事件表 ==========================
st.markdown("---")
st.subheader("📋 风险事件明细表")
st.caption("支持搜索、排序、点击链接查看原文")

# 显示筛选后的明细表关键字段
display_cols = ['event_date', 'source_type', 'entity_name', 'entity_type', 'region',
                'risk_type', 'risk_level', 'risk_score', 'sentiment', 'penalty_amount', 'summary', 'url']
available_cols = [c for c in display_cols if c in filtered_events.columns]
if available_cols:
    st.dataframe(
        filtered_events[available_cols].sort_values('event_date', ascending=False),
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("原文链接"),
            "penalty_amount": st.column_config.NumberColumn("处罚金额(万元)", format="%.2f"),
            "risk_score": st.column_config.NumberColumn("风险分", format="%.1f")
        }
    )
else:
    st.write("无明细数据")

# 导出筛选结果按钮
csv = filtered_events[available_cols].to_csv(index=False).encode('utf-8')
st.download_button("📥 导出筛选结果CSV", csv, "filtered_risk_events.csv", "text/csv")

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **数据说明**  
    - 数据来源: 监管处罚、新闻舆情、社交评论  
    - 风险评分: 基于LLM可解释规则计算  
    - 更新周期: 月频  
    - 看板版本: v1.0
    """
)