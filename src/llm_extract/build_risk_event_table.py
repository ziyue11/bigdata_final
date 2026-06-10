# src/llm_extract/build_risk_event_table.py

import os
import pandas as pd
import numpy as np

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
    
    # 3. 处罚金额分 (根据实际业务模拟或提取，假设最高加 20 分)
    # 监管处罚通常涉及金额，新闻舆情金额为 0
    if row.get('source_type') == '监管处罚':
        penalty_score = 15.0  # 默认处罚基准分
    else:
        penalty_score = 0.0
        
    # 4. 负面情绪分 (大模型情绪得分, 最高加 15 分)
    sentiment = row.get('sentiment', '中性')
    sentiment_score = row.get('sentiment_score', 0.0)
    if sentiment == "负面":
        emotion_score = abs(sentiment_score) * 15
    else:
        emotion_score = 0.0
        
    # 5. 热度分 (新闻和评论的关注度，最高加 15 分)
    # 社交媒体/舆情的新闻有更高的衍生评论和扩散热度
    if row.get('source_type') == '新闻舆情':
        heat_score = 12.0
    else:
        heat_score = 5.0  # 官网处罚公告传播热度较低
        
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
    news_cleaned_path = 'data/processed/news_cleaned.csv'
    output_path = 'data/processed/risk_event_table.csv'
    
    if not os.path.exists(extracted_path) or not os.path.exists(news_cleaned_path):
        print("❌ 缺少基础 CSV 文件，请确保上游步骤已跑完！")
        return

    print("🔄 正在加载数据并统计企业重复出现频次...")
    df_llm = pd.read_csv(extracted_path)
    df_news = pd.read_csv(news_cleaned_path)
    
    # 事前统计每个主体在整个数据集里出现的总次数，用来算“重复出现分”
    entity_counts = df_llm['entity_name'].value_counts().to_dict()
    
    print("🔀 正在横向合并基础字段...")
    df_news_sub = df_news[['record_id', 'event_date', 'source_type', 'source', 'title']]
    risk_event_table = pd.merge(df_llm, df_news_sub, on='record_id', how='left')
    
    print("🧮 正在注入官方可解释风险评分规则公式...")
    risk_event_table['risk_score'] = risk_event_table.apply(
        lambda r: calculate_risk_score_v2(r, entity_counts), axis=1
    )
    
    # 调整列顺序
    columns_order = [
        'record_id', 'event_date', 'entity_name', 'entity_type', 'region', 
        'risk_type', 'risk_level', 'risk_score', 'sentiment', 'sentiment_score', 
        'violation_reason', 'impact_scope', 'summary', 'source_type', 'source', 'title', 'url'
    ]
    columns_order = [col for col in columns_order if col in risk_event_table.columns]
    risk_event_table = risk_event_table[columns_order]
    
    risk_event_table.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✨ 【完美对齐】核心底表 {output_path} 已基于可解释规则重新构建！")

if __name__ == "__main__":
    main()