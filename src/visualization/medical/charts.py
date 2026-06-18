import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

COLOR_PALETTE = px.colors.qualitative.Plotly


def plot_time_trend(df: pd.DataFrame) -> go.Figure:
    """风险时间趋势图（双轴：事件数 + 罚金）"""
    if df.empty or len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="暂无时间趋势数据", x=0.5, y=0.5, showarrow=False)
        return fig

    if len(df) == 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['month'], y=df['regulation_count'], name='监管处罚事件',
            mode='markers', marker=dict(size=12, color='#1f77b4')
        ))
        fig.add_annotation(
            text="⚠️ 当前仅有一期数据，无法展示趋势。请补充更多月份数据。",
            x=0.5, y=0.8, showarrow=False, font=dict(color='red')
        )
        fig.update_layout(title='风险时间趋势（数据不足）', height=450)
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(x=df['month'], y=df['regulation_count'], name='监管处罚事件',
                   mode='lines+markers', line=dict(color='#1f77b4')),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df['month'], y=df['news_count'], name='新闻舆情事件',
                   mode='lines+markers', line=dict(color='#ff7f0e')),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df['month'], y=df['comment_count'], name='社交评论热度',
                   mode='lines+markers', line=dict(color='#2ca02c')),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(x=df['month'], y=df['total_penalty_amount'], name='总处罚金额(万元)',
               marker_color='rgba(220,20,60,0.5)', yaxis='y2'),
        secondary_y=True,
    )

    fig.update_layout(
        title='风险事件时间趋势与处罚金额变化',
        xaxis_title='月份',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=450
    )
    fig.update_yaxes(title_text="事件数量", secondary_y=False)
    fig.update_yaxes(title_text="处罚金额 (万元)", secondary_y=True)
    return fig


def plot_risk_type_bar(df: pd.DataFrame) -> go.Figure:
    """风险类型分布柱状图"""
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values('event_count', ascending=False)
    fig = px.bar(
        df_sorted, x='risk_type', y='event_count',
        color='avg_risk_score', color_continuous_scale='Reds',
        text='event_count',
        title='各风险类型事件数量与平均风险分',
        labels={'risk_type': '风险类型', 'event_count': '事件数量', 'avg_risk_score': '平均风险分'}
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_tickangle=-30, height=450)
    return fig


def plot_region_rank(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """地区风险排行横向柱状图"""
    if df.empty:
        return go.Figure()
    df_top = df.nlargest(top_n, 'event_count').sort_values('event_count', ascending=True)
    fig = px.bar(
        df_top, x='event_count', y='region',
        color='avg_risk_score', color_continuous_scale='OrRd',
        text='event_count',
        title=f'地区风险事件排行 (Top {top_n})',
        labels={'region': '地区', 'event_count': '事件数量', 'avg_risk_score': '平均风险分'}
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
    return fig


def plot_entity_rank(df: pd.DataFrame, top_n: int = 10, sort_by: str = 'avg_risk_score') -> go.Figure:
    """高风险主体排行条形图"""
    if df.empty:
        return go.Figure()
    valid_cols = [c for c in [sort_by, 'entity_name'] if c in df.columns]
    if not valid_cols:
        return go.Figure()
    df_top = df.nlargest(top_n, sort_by).sort_values(sort_by, ascending=True)
    fig = px.bar(
        df_top, x=sort_by, y='entity_name',
        color='risk_level', color_discrete_map={'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'},
        text=sort_by,
        title=f'高风险机构排行 (按{sort_by})',
        labels={'entity_name': '机构名称', sort_by: sort_by}
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=500)
    return fig


def plot_sentiment_trend(df_sentiment: pd.DataFrame, df_risk_time: pd.DataFrame = None) -> go.Figure:
    """舆情趋势双轴图：负面事件比例 vs 平均情绪分"""
    if df_sentiment.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无舆情数据", x=0.5, y=0.5, showarrow=False)
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(x=df_sentiment['month'], y=df_sentiment['negative_ratio'],
                   name='负面事件比例', mode='lines+markers',
                   line=dict(color='crimson', width=2)),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=df_sentiment['month'], y=df_sentiment['avg_sentiment_score'],
                   name='平均情绪分', mode='lines+markers',
                   line=dict(color='steelblue', width=2, dash='dash')),
        secondary_y=True,
    )

    fig.update_layout(
        title='舆情情绪趋势：负面事件比例 vs 情绪评分',
        xaxis_title='月份',
        hovermode='x unified',
        height=400
    )
    fig.update_yaxes(title_text="负面事件比例", secondary_y=False, range=[0, 1])
    fig.update_yaxes(title_text="情绪分 (负值越趋近-1越负面)", secondary_y=True)
    return fig


def plot_relation_heatmap(df: pd.DataFrame) -> go.Figure:
    """主体类型-风险类型热力图（用事件数量填充）"""
    if df.empty:
        return go.Figure()
    pivot = df.pivot(index='entity_type', columns='risk_type', values='event_count').fillna(0)
    fig = px.imshow(
        pivot, text_auto=True, aspect='auto',
        color_continuous_scale='RdBu_r',
        title='主体类型 vs 风险类型 热力图 (事件数量)',
        labels=dict(x='风险类型', y='主体类型', color='事件数量')
    )
    fig.update_layout(height=500, xaxis_tickangle=-45)
    return fig


def plot_risk_score_distribution(df: pd.DataFrame) -> go.Figure:
    """风险评分分布直方图"""
    if df.empty or 'risk_score' not in df.columns:
        return go.Figure()
    fig = px.histogram(df, x='risk_score', nbins=30, color='risk_level',
                       color_discrete_map={'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'},
                       title='风险评分分布 (0-100)',
                       labels={'risk_score': '风险评分', 'count': '事件数量'})
    fig.update_layout(bargap=0.05, height=400)
    return fig