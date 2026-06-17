FINANCE_RISK_EXTRACT_PROMPT = """
你是金融合规与舆情分析专家。请阅读输入文本，抽取结构化风险指标，并只返回合法 JSON。

【输入文本】
{text_content}

【字段要求】
- entity_name: 核心机构或公司名称，无法确定填"未知机构"
- entity_type: 从[银行, 保险, 证券, 基金, 上市公司, 其他]选择
- region: 省份或地区，无法确定填"未知"
- risk_type: 从[合规风险, 信贷风险, 信息披露风险, 内部控制风险, 市场操纵风险, 消费者权益风险, 经营风险, 流动性风险, 舆情风险, 其他风险]选择
- risk_level: 从[高, 中, 低]选择
- sentiment: 从[正面, 中性, 负面]选择
- sentiment_score: [-1.0, 1.0]，负面为负数
- violation_reason: 简述核心风险点
- impact_scope: 简述影响范围
- summary: 100字以内摘要
- llm_confidence: [0.0, 1.0]
"""

MEDICAL_RISK_EXTRACT_PROMPT = """
你是医疗行业监管风险与舆情分析专家。请阅读输入文本，抽取结构化风险指标，并只返回合法 JSON。

【输入文本】
{text_content}

【字段要求】
- entity_name: 核心医院、药企、医疗机构、医美机构、平台或监管对象，无法确定填"未知主体"
- entity_type: 从[医院, 药企, 医疗器械企业, 医美机构, 互联网医疗平台, 监管机构, 其他]选择
- region: 省份或地区，无法确定填"未知"
- risk_type: 从[医疗质量风险, 药品安全风险, 医疗器械风险, 医保合规风险, 价格收费风险, 广告宣传风险, 数据隐私风险, 医患纠纷风险, 经营管理风险, 舆情风险, 其他风险]选择
- risk_level: 从[高, 中, 低]选择
- sentiment: 从[正面, 中性, 负面]选择
- sentiment_score: [-1.0, 1.0]，负面为负数
- violation_reason: 简述处罚、投诉、质量问题或监管风险点
- impact_scope: 简述影响范围，如患者权益、机构自身、区域医疗服务、行业监管
- summary: 100字以内摘要
- llm_confidence: [0.0, 1.0]
"""

PROMPTS = {
    "finance": FINANCE_RISK_EXTRACT_PROMPT,
    "medical": MEDICAL_RISK_EXTRACT_PROMPT,
}
