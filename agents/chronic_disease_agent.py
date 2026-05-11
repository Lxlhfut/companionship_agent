from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import os

class ChronicDiseaseAgent:
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

    def generate_plan(self, profile):
        """根据慢病档案生成个性化管理计划"""
        prompt = f"""
        你是一位专业的慢病管理师。请根据以下用户档案，生成一份详细的慢病管理计划，包含饮食指导、运动建议、用药提醒（如有）、监测频率和应急注意事项。
        用户档案：
        {profile}
        输出要结构清晰，分点列出，语言温暖有鼓励性。
        """
        messages = [SystemMessage(content="你是慢病管理专家"), HumanMessage(content=prompt)]
        plan = self.llm.invoke(messages).content
        return plan