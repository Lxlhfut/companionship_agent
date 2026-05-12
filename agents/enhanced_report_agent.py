import json
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from utils.db import get_user_reports

class EnhancedReportAgent:
    def __init__(self):
        api_key = os.getenv("DPAPI_KEY")
        api_model = os.getenv("LLM_MODEL")
        if not api_key:
            raise ValueError("请设置 DPAPI_KEY 环境变量")

        # 使用 ChatOpenAI 对接 dpapi.cn
        self.llm = ChatOpenAI(
            model=api_model,  # 你购买的模型
            openai_api_key=api_key,
            openai_api_base="https://dpapi.cn/v1",  # 注意末尾有 /v1
            temperature=0.7
        )

    def extract_indicators(self, report_text):
        prompt = f"""从以下体检报告中提取所有健康指标，返回一个JSON对象，键为指标名称，值为数值+单位。只返回JSON，不包含其他文字。
报告内容：{report_text[:3000]}"""
        messages = [SystemMessage(content="你是一个医疗数据解析器"), HumanMessage(content=prompt)]
        result = self.llm.invoke(messages).content
        try:
            return json.loads(result)
        except:
            return {}

    def analyze_trends(self, user_id=None, reports=None):
        """
        分析趋势，优先使用传入的 reports 数据，否则从数据库加载。
        reports 应为 get_user_reports 返回的列表格式：[(id, date, indicators_json), ...]
        """
        if reports is None:
            if user_id is None:
                raise ValueError("必须提供 user_id 或 reports 参数")
            from utils.db import get_user_reports
            reports = get_user_reports(user_id)

        if len(reports) < 2:
            return None, "至少需要两份体检报告才能进行趋势分析。请多上传几份历史报告。"

        # 后续处理逻辑不变...
        history = []
        for r in reports:
            rid, date, ind_json = r
            try:
                ind = json.loads(ind_json) if ind_json else {}
            except:
                ind = {}
            history.append({"date": date, "indicators": ind})
        history_text = json.dumps(history, ensure_ascii=False, indent=2)
        prompt = f"""
你是一位资深健康分析师。以下是用户的多份体检报告指标历史数据：
{history_text}
请分析：
1. 各关键指标的变化趋势（如血糖、血压、血脂等）。
2. 潜在健康风险预测，指出哪些指标值得警惕。
3. 提供具体的改善建议和下次体检重点。
输出使用中文，条理清晰。
"""
        messages = [SystemMessage(content="你是健康分析师"), HumanMessage(content=prompt)]
        analysis = self.llm.invoke(messages).content
        return history, analysis