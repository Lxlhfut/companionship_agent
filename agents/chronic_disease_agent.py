from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os
import streamlit as st

class ChronicDiseaseAgent:
    def __init__(self):
        api_key = os.getenv("DPAPI_KEY")
        api_model = os.getenv("LLM_MODEL")
        if not api_key:
            raise ValueError("请设置 DPAPI_KEY 环境变量")

        self.llm = ChatOpenAI(
            model=api_model,
            openai_api_key=api_key,
            openai_api_base="https://dpapi.cn/v1",
            temperature=0.7
        )

    @st.cache_data(ttl=3600, show_spinner="正在生成慢病管理计划...")
    def generate_plan_cached(_self, profile_str: str) -> str:
        """
        缓存生成计划的结果，避免相同档案重复调用 LLM。
        profile_str 应该是用户慢病档案的字符串表示（如 JSON 字符串）。
        """
        messages = [
            SystemMessage(content="你是慢病管理专家"),
            HumanMessage(content=f"""
你是一位专业的慢病管理师。请根据以下用户档案，生成一份详细的慢病管理计划，包含饮食指导、运动建议、用药提醒（如有）、监测频率和应急注意事项。

用户档案：
{profile_str}

输出要结构清晰，分点列出，语言温暖有鼓励性。
""")
        ]
        plan = _self.llm.invoke(messages).content
        return plan

    def generate_plan(self, profile):
        """
        对外接口：将 profile 转换为字符串后调用缓存版本。
        profile 可以是字典或 JSON 字符串。
        """
        import json
        if isinstance(profile, dict):
            profile_str = json.dumps(profile, ensure_ascii=False)
        else:
            profile_str = str(profile)
        return self.generate_plan_cached(profile_str)