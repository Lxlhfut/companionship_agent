from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import InternalServerError, RateLimitError, APITimeoutError


class FamilyAvatarAgent:
    def __init__(self):
        api_key = os.getenv("DPAPI_KEY")
        api_model = os.getenv("LLM_MODEL")
        if not api_key:
            raise ValueError("请设置 DPAPI_KEY 环境变量")

        self.llm = ChatOpenAI(
            model=api_model,
            openai_api_key=api_key,
            openai_api_base="https://dpapi.cn/v1",
            temperature=0.7,
            request_timeout=30,
            max_retries=0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((InternalServerError, RateLimitError, APITimeoutError, ConnectionError))
    )
    def _invoke_llm(self, messages):
        return self.llm.invoke(messages)

    def get_avatar_response(self, avatar_data, user_name, user_input, chat_history):
        """使用家人分身的个性化设置进行回复"""
        avatar_name = avatar_data[2]  # 注意：avatar_data 是 tuple，索引 2 是 avatar_name
        personality = avatar_data[4] or "亲切温暖的家人"
        speech_samples = avatar_data[5] or ""

        system_prompt = f"""你正扮演一位真实的家人，名字叫{avatar_name}。你需要模仿他/她的性格和说话风格。
        性格描述：{personality}
        说话风格样例：{speech_samples}
        当前与你对话的是你关心的家人：{user_name}。请用真实的、口语化的、充满感情的方式回复，就像你真的在陪他/她聊天。
        可以加入一些回忆、关心问候或日常小事。"""

        messages = [SystemMessage(content=system_prompt)]
        # 加上历史（仅保留最近几条）
        for msg in chat_history[-6:]:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            else:
                messages.append(AIMessage(content=msg['content']))
        messages.append(HumanMessage(content=user_input))

        try:
            response = self._invoke_llm(messages)
            return response.content
        except Exception as e:
            return f"抱歉，AI 服务器爆满暂时无法回复（错误类型：{type(e).__name__}），请稍后再试。"