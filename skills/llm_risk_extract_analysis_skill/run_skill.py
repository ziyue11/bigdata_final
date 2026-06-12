# skills/llm_risk_extract_analysis_skill/run_skill.py

import os

def main():
    print("==================================================================")
    print("🤖 触发大模型风险抽取与多维分析原子能力 (llm_risk_extract_analysis_skill)")
    print("==================================================================")
    
    # 锚定项目根目录 (由于在二级子目录下，需要往上跳两级)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    os.chdir(project_root)
    
    # 1. 运行三源 LLM 风险字段抽取
    print("\n[Step 1/4] 正在读取三类 cleaned 数据并调用 LLM 抽取风险字段 ...")
    exit_code_0 = os.system("python src/llm_extract/extract_risk_fields.py")
    if exit_code_0 != 0:
        print("❌ Step 1 运行失败！")
        return

    # 2. 运行核心评分与大表构建
    print("\n[Step 2/4] 正在调用打分引擎构建核心大表 risk_event_table.csv ...")
    exit_code_1 = os.system("python src/llm_extract/build_risk_event_table.py")
    if exit_code_1 != 0:
        print("❌ Step 2 运行失败！")
        return
    
    # 3. 运行全自动大满贯分析
    print("\n[Step 3/4] 正在调用统计组件切分 8 张看板分析底表 ...")
    exit_code_2 = os.system("python src/analysis/run_analysis.py")
    if exit_code_2 != 0:
        print("❌ Step 3 运行失败！")
        return
    
    # 4. 运行人工抽样审核生成
    print("\n[Step 4/4] 正在自动导出 50 条人工抽样对比审计表 ...")
    exit_code_3 = os.system("python src/llm_extract/manual_review.py")
    if exit_code_3 != 0:
        print("❌ Step 4 运行失败！")
        return
    
    print("\n🎯 [SKILL COMPLETE] 全套大模型分析与统计底表已完美交付至 data/ 目录！")

if __name__ == "__main__":
    main()
