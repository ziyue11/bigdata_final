
# src/llm_extract/extract_risk_fields.py

import os
import json
import pandas as pd
from openai import OpenAI
from prompt_templates import RISK_EXTRACT_PROMPT

# 1. 配置DeepSeek 钥匙

API_KEY = "sk-1efb5b5709cd485196cdd5c8773beb2d" 

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com" # DeepSeek 的官方服务器地址
)

def call_deepseek_json(text_content):
    """把单条新闻塞进 Prompt，并呼叫 DeepSeek 抽取 JSON"""
    try:
        # 将新闻正文塞入我们写好的 Prompt 模板中
        full_prompt = RISK_EXTRACT_PROMPT.format(text_content=text_content)
        
        response = client.chat.completions.create(
            model="deepseek-chat", # 使用 DeepSeek V3/R1 模型
            messages=[
                {"role": "user", "content": full_prompt}
            ],
            response_format={
                'type': 'json_object' # 强制要求模型必须返回标准的 JSON 格式
            },
            temperature=0.2 # 降低随机性，让大模型更严谨
        )
        
        # 获取大模型返回的文本，并转换为 Python 字典
        result_json = json.loads(response.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"❌ 这一条抽失败了，原因: {e}")
        return None

def main():
    # 2. 读取 A 角色洗好的新闻数据
    input_path = 'data/processed/news_cleaned.csv'
    output_path = 'data/processed/llm_extracted.csv'
    
    if not os.path.exists(input_path):
        print(f"❌ 找不到输入文件：{input_path}，请先让 A 角色把数据放进去！")
        return
        
    print("🚀 开始读取 A 角色洗好的数据...")
    df = pd.read_csv(input_path)
    
    # 为了防止你充值的钱一次性扣太多，我们可以先拿前 5 条测试，没问题了再跑全部
    # 💡 真正跑全部数据时，把下面这一行的冒号前面的内容删掉，变成：all_results = []
    all_results = []
    
    print(f"📊 总共有 {len(df)} 条数据待处理，正在批量呼叫 DeepSeek 抽取...")
    
    for index, row in df.iterrows():
        # 提取新闻的标题加正文，喂给大模型
        combined_text = f"标题: {row['title']}\n正文: {row['content']}"
        record_id = row['record_id']
        
        print(f"⏳ 正在处理第 {index+1}/{len(df)} 条数据 (ID: {record_id})...")
        
        llm_data = call_deepseek_json(combined_text)
        
        if llm_data:
            # 把原始的 record_id 和 url 拼进去，方便后面跟 A 角色的表做关联
            llm_data['record_id'] = record_id
            llm_data['url'] = row['url']
            all_results.append(llm_data)
        
    # 3. 把大模型抽出来的所有 JSON 列表组合成一个新的表格并保存
    df_extracted = pd.DataFrame(all_results)
    df_extracted.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✨ 恭喜你！批量抽取完成！结果已成功保存在：{output_path}")

if __name__ == "__main__":
    main()