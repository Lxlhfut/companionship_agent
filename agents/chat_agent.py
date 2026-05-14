import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import InternalServerError, RateLimitError, APITimeoutError
from datetime import datetime

class ChatAgent:
    def __init__(self):
        api_key = os.getenv("DPAPI_KEY")
        api_model = os.getenv("LLM_MODEL")
        if not api_key:
            raise ValueError("请设置 DPAPI_KEY 环境变量")

        # 使用 ChatOpenAI 对接 dpapi.cn
        self.llm = ChatOpenAI(
            model=api_model,
            openai_api_key=api_key,
            openai_api_base="https://dpapi.cn/v1",
            temperature=0.7,
            request_timeout=30,
            max_retries=0  # 关闭 OpenAI 自带重试，我们用 tenacity 控制
        )
        today = datetime.now().strftime("%Y年%m月%d日")
        self.system_prompt = f"""你是一位温暖、耐心的老年陪伴助手，名叫"小银"。
        今天是 {today}。
        你的服务对象是老年人，说话要慢一点、清楚一点，用词简单，充满关怀。
        你可以陪老人聊天、解答简单问题、讲笑话、回忆往事。
        如果遇到医疗建议或紧急情况，请提醒联系家人或医生。"""
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((InternalServerError, RateLimitError, APITimeoutError, ConnectionError))
    )
    def _invoke_llm(self, messages):
        """带重试的 LLM 调用"""
        return self.llm.invoke(messages)

    def chat(self, user_input, memory):
        messages = [SystemMessage(content=self.system_prompt)]
        history = memory.load_memory_variables({}).get("history", [])
        messages.extend(history)
        messages.append(HumanMessage(content=user_input))

        try:
            response = self._invoke_llm(messages)
            return response.content
        except Exception as e:
            # 所有重试都失败后，返回友好错误提示
            return f"抱歉，AI 服务器爆满暂时不可用，请稍后再试。"