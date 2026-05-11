import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


class ChatAgent:
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
        self.system_prompt = """你是一位温暖、耐心的老年陪伴助手，名叫"小银"。
你的服务对象是老年人，说话要慢一点、清楚一点，用词简单，充满关怀。
你可以陪老人聊天、解答简单问题、讲笑话、回忆往事。
如果遇到医疗建议或紧急情况，请提醒联系家人或医生。"""

    def chat(self, user_input, memory):
        messages = [SystemMessage(content=self.system_prompt)]
        history = memory.load_memory_variables({}).get("history", [])
        messages.extend(history)
        messages.append(HumanMessage(content=user_input))
        response = self.llm.invoke(messages)
        return response.content