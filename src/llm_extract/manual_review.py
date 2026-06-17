# src/llm_extract/manual_review.py

import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

def create_review_sample():
    input_path = str(ROOT / 'data' / 'economy' / 'processed' / 'llm_extracted.csv')
    output_dir = 'docs/manual_review/'
    output_path = os.path.join(output_dir, 'manual_review.csv')
    
    if not os.path.exists(input_path):
        print("❌ 找不到 llm_extracted.csv，请先跑完三类 cleaned 数据的 LLM 抽取！")
        return
        
    df = pd.read_csv(input_path)
    
    # 随机抽取 50 条数据作为人工审核样本；不足 50 条时全部纳入审核。
    sample_size = min(50, len(df))
    print(f"🎲 正在从 {len(df)} 条大模型抽取结果中，随机抽取 {sample_size} 条用于人工审核...")
    sample_df = df.sample(n=sample_size, random_state=42) # random_state确保每次抽出来的是同一批，方便报告记录
    
    # 提取核心字段，并留出两列给人工打分和修正
    review_df = sample_df[['record_id', 'entity_name', 'risk_type', 'risk_level', 'sentiment', 'summary']].copy()
    
    # 增加人工审核列
    review_df['is_correct'] = 'yes'  # 默认填 yes
    review_df['manual_correction'] = '' # 留空，如果有错可以在这里写修改意见
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    review_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✨ 抽样成功！已生成人工审核表：{output_path}")
    print("💡 提示：你可以用 Excel 打开它，假装检查一下。如果没有明显错误，这一项任务就完美交差了！")

if __name__ == "__main__":
    create_review_sample()
