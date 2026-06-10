# src/llm_extract/prompt_templates.py

# 这是你给大模型规定的标准抽取模板，能确保大模型乖乖听话输出 JSON 格式
RISK_EXTRACT_PROMPT = """
你是一个精通金融合规审计与舆情分析的专家。请阅读以下输入的文本片段，并从中抽取结构化的风险指标。

【输入文本】
{text_content}

【抽取规则】
1. entity_name: 识别受罚或被提及的核心金融机构或上市公司全称。
2. entity_type: 必须在 [银行, 保险, 证券, 基金, 上市公司, 其他] 中选择一个，若无法确定填"其他"。
3. region: 识别该机构或事件发生的省份/地区（如：浙江、广东、北京），若文本未提及填"未知"。
4. risk_type: 必须严格在以下列表中选择一个，不得自行创造：
   [合规风险, 信贷风险, 信息披露风险, 内部控制风险, 市场操纵风险, 消费者权益风险, 经营风险, 流动性风险, 舆情风险, 其他风险]
5. risk_level: 必须在 [高, 中, 低] 中选择一个。
6. sentiment: 必须在 [正面, 中性, 负面] 中选择一个。
7. sentiment_score: 给出情绪倾向得分，范围在 [-1.0, 1.0] 之间，-1.0代表极度负面，1.0代表极度正面。
8. violation_reason: 用一句简短的话概括其违规原因或核心风险点。
9. impact_scope: 评估影响范围（如：机构自身, 整个行业, 客户权益）。
10. summary: 100字以内的事件摘要。
11. llm_confidence: 你的置信度分数，范围在 [0.0, 1.0] 之间。

【输出格式】
必须且只能返回一个合法的 JSON 字符串，不要包含任何 Markdown 标记（如 ```json ）。
JSON 格式示例：
{{
  "entity_name": "某某银行",
  "entity_type": "银行",
  "region": "浙江",
  "risk_type": "合规风险",
  "risk_level": "中",
  "sentiment": "负面",
  "sentiment_score": -0.72,
  "violation_reason": "贷款管理不审慎，相关业务存在违规操作",
  "impact_scope": "机构自身、客户权益",
  "summary": "该机构因贷款管理问题受到监管处罚",
  "llm_confidence": 0.86
}}
"""