import streamlit as st
from langchain.memory import ConversationBufferWindowMemory

def show():
    st.title("💬 陪伴聊天")
    st.markdown("有什么想聊的都可以告诉我～")

    # 初始化聊天记忆
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = ConversationBufferWindowMemory(
            k=10, return_messages=True, memory_key="history"
        )
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 显示历史消息
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 输入框
    if prompt := st.chat_input("请输入..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = st.session_state.chat_agent.chat(
                    prompt, st.session_state.chat_memory
                )
                st.write(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                # 更新记忆
                st.session_state.chat_memory.save_context(
                    {"input": prompt}, {"output": response}
                )