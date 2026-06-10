# 🛠️ LLM 风险特征抽取与多维打分分析原子组件

## 1. 组件概述
本组件属于本金融风控看板系统的核心 AI 原子能力。主要负责接收 A 角色清洗后的结构化底表，通过提示词工程驱动大模型批量抽取出隐藏的风险实体、违规诱因、情绪得分，并基于可解释评分模型完成对金融风险事件的量化评级，最终自动化切分出 8 张面向 Streamlit 看板的统计视图。

## 2. 核心输入输出
* **输入文件：** `data/processed/llm_extracted.csv` / `news_cleaned.csv`
* **输出文件：** `data/processed/risk_event_table.csv`、`data/analysis/*.csv` (共 8 张)

## 3. 调用与触发方式
```bash
python skills/llm_risk_extract_analysis_skill/run_skill.py