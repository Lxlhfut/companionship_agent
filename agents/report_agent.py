import os
import pdfplumber
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


class ReportAgent:
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
        self.system_prompt = """你是一位专业的体检报告解读助手，面向老年人及其家属。
请用通俗易懂的语言解释报告中的指标含义、正常范围，并指出异常项可能的原因和健康建议。
**重要提醒**：你不是医生，解读仅供参考，如有疑问请务必咨询专业医生。"""

    def extract_text_from_pdf(self, pdf_file):
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    def interpret(self, report_text):
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"请帮我解读以下体检报告内容：\n\n{report_text[:4000]}")
        ]
        response = self.llm.invoke(messages)
        return response.content