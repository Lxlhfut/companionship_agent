import streamlit as st
from langchain.memory import ConversationBufferWindowMemory

def show():
    st.title("💬 陪伴聊天")
    st.markdown("有什么想聊的都可以告诉我～")

    # 初始化聊天记忆（使用 session_state 缓存，避免每次 rerun 重新创建）
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = ConversationBufferWindowMemory(
            k=10, return_messages=True, memory_key="history"
        )
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 显示历史消息（直接从缓存读取，无延迟）
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 输入框
    if prompt := st.chat_input("请输入..."):
        # 记录用户消息
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                # 调用已在 app.py 中初始化并缓存的 chat_agent
                response = st.session_state.chat_agent.chat(
                    prompt, st.session_state.chat_memory
                )
                st.write(response)
                # 记录助手回复
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                # 更新长短时记忆（缓存）
                st.session_state.chat_memory.save_context(
                    {"input": prompt}, {"output": response}
                )