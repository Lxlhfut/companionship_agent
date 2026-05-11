import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import datetime


class ReminderAgent:
    def __init__(self):
        # 如果有 LLM API，用于给出用药建议
        api_key = os.getenv("DPAPI_KEY")
        api_model = os.getenv("LLM_MODEL")
        if api_key:
            self.llm = ChatOpenAI(
                model=api_model,  # 或你的可用模型
                openai_api_key=api_key,
                openai_api_base="https://dpapi.cn/v1",
                temperature=0.7
            )
        else:
            self.llm = None

        self.system_prompt = """你是一位专业的用药顾问，帮助老年人合理用药。
请根据用户提供的多种药品信息，判断是否存在潜在的相互作用或服用时间冲突。
给出简明扼要的建议，包括：
1. 是否可以同时服用？
2. 建议的服用顺序或间隔时间（如隔开1小时等）。
3. 特别注意事项（如是否需饭后服用、忌口等）。
如果无法确定，请建议咨询医生或药师。"""

    def check_due_reminders(self, user_id, from_db_func):
        """检查当前时间应该提醒的用药（改进版）"""
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.weekday()

        # 调用数据库函数获取该时间点的提醒
        due = from_db_func(user_id, current_time, current_weekday)
        return due

    def analyze_conflicts(self, medicines):
        """分析药品间潜在冲突，返回建议"""
        if not self.llm:
            return "（未配置AI模型，无法提供用药建议。请咨询医生或药师。）"

        med_list = "\n".join([f"- {m[1]} {m[2]}" for m in medicines])
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"用户需要在同一时间服用以下药品：\n{med_list}\n请分析是否存在冲突，并给出服用建议。")
        ]
        response = self.llm.invoke(messages)
        return response.content