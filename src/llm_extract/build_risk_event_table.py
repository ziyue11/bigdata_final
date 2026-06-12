# src/llm_extract/build_risk_event_table.py

import os
import pandas as pd
import numpy as np

def calculate_heat_score(row):
    """根据数据来源计算热度分，最高 15 分。"""
    source_type = row.get('source_type', '')
    if source_type == 'comment':
        read_count = pd.to_numeric(row.get('read_count', 0), errors='coerce')
        comment_count = pd.to_numeric(row.get('comment_count', 0), errors='coerce')
        heat_raw = np.nan_to_num(read_count) + np.nan_to_num(comment_count) * 5
        return round(min(15.0, np.log1p(heat_raw) * 2), 1)
    if source_type == 'news':
        return 10.0
    if source_type == 'regulation':
        return 5.0
    return 0.0

def calculate_risk_score_v2(row, entity_counts):
    """
    严格按照组长指定的金融风险可解释规则进行评分计算:
    risk_score = 基础分 + 风险等级分 + 处罚金额分 + 负面情绪分 + 热度分 + 重复出现分
    范围严格限制在 0 - 100 分。
    """
    # 1. 基础分 (固定项)
    base_score = 15
    
    # 2. 风险等级分 (大模型识别: 高/中/低)
    level_map = {"高": 25, "中": 15, "低": 5}
    level_score = level_map.get(row.get('risk_level', '低'), 5)
    
    # 3. 处罚金额分，最高加 20 分。监管处罚使用 A 阶段解析出的万元金额。
    penalty_amount = pd.to_numeric(row.get('penalty_amount', 0), errors='coerce')
    if row.get('source_type') == 'regulation' and pd.notna(penalty_amount) and penalty_amount > 0:
        penalty_score = min(20.0, np.log1p(penalty_amount) * 3)
    else:
        penalty_score = 0.0
        
    # 4. 负面情绪分 (大模型情绪得分, 最高加 15 分)
    sentiment = row.get('sentiment', '中性')
    sentiment_score = row.get('sentiment_score', 0.0)
    if sentiment == "负面":
        emotion_score = abs(sentiment_score) * 15
    else:
        emotion_score = 0.0
        
    # 5. 热度分，新闻给固定舆情热度，评论根据阅读/评论数计算。
    heat_score = row.get('heat_score', 0.0)
        
    # 6. 重复出现分 (主体在200条里被提到次数越多，说明是惯犯，风险滚雪球)
    entity_name = row.get('entity_name', '未知机构')
    mention_count = entity_counts.get(entity_name, 1)
    if mention_count > 5:
        repeat_score = 10.0
    elif mention_count > 2:
        repeat_score = 5.0
    else:
        repeat_score = 0.0
        
    # 7. 汇总计算公式
    total_score = base_score + level_score + penalty_score + emotion_score + heat_score + repeat_score
    
    # 严格锁死在 0 到 100 之间
    return round(max(0, min(100, total_score)), 1)

def main():
    extracted_path = 'data/processed/llm_extracted.csv'
    output_path = 'data/processed/risk_event_table.csv'
    
    if not os.path.exists(extracted_path):
        print("❌ 缺少 data/processed/llm_extracted.csv，请先运行 extract_risk_fields.py！")
        return

    print("🔄 正在加载数据并统计企业重复出现频次...")
    df_llm = pd.read_csv(extracted_path)
    df_meta = load_cleaned_metadata()
    if df_meta.empty:
        print("❌ 找不到三张 cleaned 表，请先运行 A 阶段预处理脚本！")
        return
    
    # 事前统计每个主体在整个数据集里出现的总次数，用来算“重复出现分”
    entity_counts = df_llm['entity_name'].value_counts().to_dict()
    
    print("🔀 正在按 record_id 合并三类来源基础字段...")
    if 'source_type' in df_llm.columns:
        df_llm = df_llm.drop(columns=['source_type'])
    if 'url' in df_llm.columns:
        df_llm = df_llm.drop(columns=['url'])
    risk_event_table = pd.merge(df_llm, df_meta, on='record_id', how='left')
    risk_event_table['penalty_amount'] = pd.to_numeric(
        risk_event_table.get('penalty_amount', 0), errors='coerce'
    ).fillna(0)
    risk_event_table['heat_score'] = risk_event_table.apply(calculate_heat_score, axis=1)
    risk_event_table['manual_check'] = '待审核'
    
    print("🧮 正在注入官方可解释风险评分规则公式...")
    risk_event_table['risk_score'] = risk_event_table.apply(
        lambda r: calculate_risk_score_v2(r, entity_counts), axis=1
    )
    
    # 调整列顺序
    columns_order = [
        'record_id', 'event_date', 'entity_name', 'entity_type', 'region', 
        'risk_type', 'risk_level', 'risk_score', 'sentiment', 'sentiment_score', 
        'violation_reason', 'impact_scope', 'penalty_amount', 'heat_score', 'summary',
        'source_type', 'source', 'title', 'url', 'llm_confidence', 'manual_check'
    ]
    columns_order = [col for col in columns_order if col in risk_event_table.columns]
    risk_event_table = risk_event_table[columns_order]
    
    risk_event_table.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✨ 【完美对齐】核心底表 {output_path} 已基于可解释规则重新构建！")

def load_cleaned_metadata():
    """把 A 阶段三张 cleaned 表统一成事件表元数据。"""
    frames = []

    regulation_path = 'data/processed/regulation_cleaned.csv'
    if os.path.exists(regulation_path):
        df_reg = pd.read_csv(regulation_path)
        frames.append(pd.DataFrame({
            'record_id': df_reg.get('record_id'),
            'event_date': df_reg.get('event_date'),
            'source_type': 'regulation',
            'source': df_reg.get('source'),
            'title': df_reg.get('title'),
            'penalty_amount': df_reg.get('penalty_amount', 0),
            'read_count': 0,
            'comment_count': 0,
            'url': df_reg.get('url'),
        }))

    news_path = 'data/processed/news_cleaned.csv'
    if os.path.exists(news_path):
        df_news = pd.read_csv(news_path)
        frames.append(pd.DataFrame({
            'record_id': df_news.get('record_id'),
            'event_date': df_news.get('event_date'),
            'source_type': 'news',
            'source': df_news.get('source'),
            'title': df_news.get('title'),
            'penalty_amount': 0,
            'read_count': 0,
            'comment_count': 0,
            'url': df_news.get('url'),
        }))

    comment_path = 'data/processed/comment_cleaned.csv'
    if os.path.exists(comment_path):
        df_comment = pd.read_csv(comment_path)
        frames.append(pd.DataFrame({
            'record_id': df_comment.get('record_id'),
            'event_date': df_comment.get('event_date'),
            'source_type': 'comment',
            'source': df_comment.get('source'),
            'title': df_comment.get('title'),
            'penalty_amount': 0,
            'read_count': df_comment.get('read_count', 0),
            'comment_count': df_comment.get('comment_count', 0),
            'url': df_comment.get('url'),
        }))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

if __name__ == "__main__":
    main()
