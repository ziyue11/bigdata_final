
# src/llm_extract/extract_risk_fields.py

import os
import json
import time
import pandas as pd
from openai import APIStatusError
from openai import OpenAI
from prompt_templates import RISK_EXTRACT_PROMPT

API_KEY = (
    os.getenv("DASHSCOPE_API_KEY")
    or os.getenv("DEEPSEEK_API_KEY")
    or os.getenv("OPENAI_API_KEY")
)
BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
MODEL_NAME = os.getenv("LLM_MODEL", "qwen-mt-flash")
MAX_QUOTA_RETRIES = int(os.getenv("LLM_MAX_QUOTA_RETRIES", "3"))
QUOTA_RETRY_DELAY_SECONDS = int(os.getenv("LLM_QUOTA_RETRY_DELAY_SECONDS", "60"))
MAX_TEXT_CHARS = int(os.getenv("LLM_MAX_TEXT_CHARS", "6000"))
OUTPUT_COLUMNS = [
    'entity_name', 'entity_type', 'region', 'risk_type', 'risk_level',
    'sentiment', 'sentiment_score', 'violation_reason', 'impact_scope',
    'summary', 'llm_confidence', 'record_id', 'source_type', 'url',
]
FAILED_COLUMNS = ['record_id', 'source_type', 'title', 'url', 'error']

client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY else None

def call_deepseek_json(text_content):
    """把单条新闻塞进 Prompt，并呼叫 DeepSeek 抽取 JSON"""
    try:
        # 将新闻正文塞入我们写好的 Prompt 模板中
        full_prompt = RISK_EXTRACT_PROMPT.format(text_content=text_content)
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        # 获取大模型返回的文本，并转换为 Python 字典
        result_json = json.loads(response.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"❌ 这一条抽失败了，原因: {e}")
        if is_quota_error(e):
            raise
        return None

def main():
    if client is None:
        print("❌ 未配置 API Key。请先设置环境变量 DASHSCOPE_API_KEY。")
        return

    output_path = 'data/processed/llm_extracted.csv'
    failed_path = 'data/processed/llm_failed_records.csv'

    print("🚀 开始读取 A 角色洗好的三类 cleaned 数据...")
    df = load_cleaned_records()
    if df.empty:
        print("❌ 没有可抽取的数据，请检查 data/processed 下三张 cleaned 表是否存在。")
        return

    done_ids = load_done_record_ids(output_path)
    if done_ids:
        print(f"🔁 检测到已有 {len(done_ids)} 条抽取结果，本次将自动跳过这些 record_id。")
    
    print(f"📊 总共有 {len(df)} 条数据待处理，正在批量呼叫 DeepSeek 抽取...")
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    for index, row in df.iterrows():
        record_id = row['record_id']
        if record_id in done_ids:
            continue

        combined_text = (
            f"数据来源: {row['source_type']}\n"
            f"标题: {row['title']}\n"
            f"正文: {truncate_text(row['text_content'])}"
        )
        
        print(f"⏳ 正在处理第 {index+1}/{len(df)} 条数据 (ID: {record_id})...")
        
        llm_data = call_with_quota_retries(combined_text)
        if llm_data == 'quota_exhausted':
            append_failed_row_to_csv(failed_path, {
                'record_id': record_id,
                'source_type': row['source_type'],
                'title': row['title'],
                'url': row['url'],
                'error': 'insufficient_quota_or_token_limit',
            })
            print("❌ 多次重试后仍然 429，已自动停止。已成功写入的记录会在下次运行时自动跳过。")
            return
        
        if llm_data:
            llm_data['record_id'] = record_id
            llm_data['source_type'] = row['source_type']
            llm_data['url'] = row['url']
            append_row_to_csv(output_path, llm_data)
            done_ids.add(record_id)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            append_failed_row_to_csv(failed_path, {
                'record_id': record_id,
                'source_type': row['source_type'],
                'title': row['title'],
                'url': row['url'],
                'error': 'LLM request or JSON parse failed',
            })
            if consecutive_failures >= max_consecutive_failures:
                print(f"❌ 已连续失败 {max_consecutive_failures} 条，自动停止。请检查模型、额度或接口参数后再重跑。")
                return
        
    print(f"✨ 恭喜你！批量抽取完成！结果已成功保存在：{output_path}")

def load_cleaned_records():
    """读取 regulation/news/comment 三张 cleaned 表，并统一成 LLM 输入 schema。"""
    records = []

    regulation_path = 'data/processed/regulation_cleaned.csv'
    if os.path.exists(regulation_path):
        df_reg = pd.read_csv(regulation_path)
        for _, row in df_reg.iterrows():
            records.append({
                'record_id': row.get('record_id', ''),
                'source_type': 'regulation',
                'title': row.get('title', ''),
                'text_content': row.get('raw_text', ''),
                'url': row.get('url', ''),
            })

    news_path = 'data/processed/news_cleaned.csv'
    if os.path.exists(news_path):
        df_news = pd.read_csv(news_path)
        for _, row in df_news.iterrows():
            records.append({
                'record_id': row.get('record_id', ''),
                'source_type': 'news',
                'title': row.get('title', ''),
                'text_content': row.get('content', ''),
                'url': row.get('url', ''),
            })

    comment_path = 'data/processed/comment_cleaned.csv'
    if os.path.exists(comment_path):
        df_comment = pd.read_csv(comment_path)
        for _, row in df_comment.iterrows():
            records.append({
                'record_id': row.get('record_id', ''),
                'source_type': 'comment',
                'title': row.get('title', ''),
                'text_content': row.get('content', ''),
                'url': row.get('url', ''),
            })

    return pd.DataFrame(records)

def truncate_text(text):
    text = '' if pd.isna(text) else str(text)
    if len(text) <= MAX_TEXT_CHARS:
        return text
    head_len = MAX_TEXT_CHARS // 2
    tail_len = MAX_TEXT_CHARS - head_len
    return text[:head_len] + "\n……中间内容已截断……\n" + text[-tail_len:]

def is_quota_error(error):
    if isinstance(error, APIStatusError) and error.status_code == 429:
        return True
    text = str(error).lower()
    return 'insufficient_quota' in text or 'exceeded your current quota' in text

def call_with_quota_retries(text_content):
    for attempt in range(MAX_QUOTA_RETRIES + 1):
        try:
            return call_deepseek_json(text_content)
        except Exception as e:
            if not is_quota_error(e):
                raise
            if attempt >= MAX_QUOTA_RETRIES:
                return 'quota_exhausted'
            wait_seconds = QUOTA_RETRY_DELAY_SECONDS * (attempt + 1)
            print(f"⏸️ 触发 429/token-limit，等待 {wait_seconds} 秒后重试同一条...")
            time.sleep(wait_seconds)

def load_done_record_ids(output_path):
    if not os.path.exists(output_path):
        return set()
    try:
        df_done = pd.read_csv(output_path)
    except pd.errors.EmptyDataError:
        return set()
    if 'record_id' not in df_done.columns:
        return set()
    return set(df_done['record_id'].dropna().astype(str))

def append_row_to_csv(output_path, row):
    normalized = {col: row.get(col, '') for col in OUTPUT_COLUMNS}
    df_row = pd.DataFrame([normalized], columns=OUTPUT_COLUMNS)
    write_header = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
    df_row.to_csv(
        output_path,
        mode='a',
        index=False,
        header=write_header,
        encoding='utf-8-sig',
    )

def append_failed_row_to_csv(output_path, row):
    normalized = {col: row.get(col, '') for col in FAILED_COLUMNS}
    df_row = pd.DataFrame([normalized], columns=FAILED_COLUMNS)
    write_header = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
    df_row.to_csv(
        output_path,
        mode='a',
        index=False,
        header=write_header,
        encoding='utf-8-sig',
    )

if __name__ == "__main__":
    main()
