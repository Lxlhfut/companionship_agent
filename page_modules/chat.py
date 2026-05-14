import streamlit as st
from langchain.memory import ConversationBufferWindowMemory
from utils.db import (
    create_conversation, get_user_conversations, get_conversation_messages,
    save_message, update_conversation_title, delete_conversation, get_conversation
)

def show():
    st.title("💬 陪伴聊天")

    if "user_id" not in st.session_state:
        st.warning("请先登录")
        return

    user_id = st.session_state.user_id
    chat_type = "companion"

    # 会话管理
    if "current_conversation_id" not in st.session_state:
        convs = get_user_conversations(user_id, chat_type, limit=1)
        if convs:
            st.session_state.current_conversation_id = convs[0]['id']
        else:
            new_id = create_conversation(user_id, chat_type, title="新对话")
            st.session_state.current_conversation_id = new_id

    conv_id = st.session_state.current_conversation_id
    cache_key = f"chat_history_{conv_id}"

    if cache_key not in st.session_state:
        db_messages = get_conversation_messages(conv_id)
        history = [{"role": msg['role'], "content": msg['content']} for msg in db_messages]
        st.session_state[cache_key] = history
        # 重建 LangChain 记忆
        memory = ConversationBufferWindowMemory(k=10, return_messages=True, memory_key="history")
        for msg in history:
            if msg['role'] == 'user':
                memory.chat_memory.add_user_message(msg['content'])
            else:
                memory.chat_memory.add_ai_message(msg['content'])
        st.session_state.chat_memory = memory

    for msg in st.session_state[cache_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    with st.sidebar:
        st.subheader("历史对话")
        if st.button("➕ 新对话", use_container_width=True):
            new_id = create_conversation(user_id, chat_type, title="新对话")
            st.session_state.current_conversation_id = new_id
            st.session_state.pop(f"chat_history_{new_id}", None)
            st.rerun()

        conversations = get_user_conversations(user_id, chat_type, limit=50)
        for conv in conversations:
            conv_id_loop = conv['id']
            title = conv['title']
            cols = st.columns([4, 1])
            with cols[0]:
                if st.button(title, key=f"conv_{conv_id_loop}", use_container_width=True):
                    st.session_state.current_conversation_id = conv_id_loop
                    st.session_state.pop(f"chat_history_{conv_id_loop}", None)
                    st.rerun()
            with cols[1]:
                if st.button("🗑️", key=f"del_{conv_id_loop}"):
                    delete_conversation(conv_id_loop)
                    if st.session_state.current_conversation_id == conv_id_loop:
                        new_id = create_conversation(user_id, chat_type, title="新对话")
                        st.session_state.current_conversation_id = new_id
                        st.session_state.pop(f"chat_history_{new_id}", None)
                    st.rerun()

    if prompt := st.chat_input("请输入..."):
        st.session_state[cache_key].append({"role": "user", "content": prompt})
        save_message(conv_id, "user", prompt)
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                if "chat_memory" not in st.session_state:
                    st.session_state.chat_memory = ConversationBufferWindowMemory(k=10, return_messages=True, memory_key="history")
                response = st.session_state.chat_agent.chat(prompt, st.session_state.chat_memory)
                st.write(response)

        st.session_state[cache_key].append({"role": "assistant", "content": response})
        save_message(conv_id, "assistant", response)
        st.session_state.chat_memory.save_context({"input": prompt}, {"output": response})

        conv_info = get_conversation(conv_id)
        if conv_info and conv_info['title'] == "新对话":
            new_title = prompt[:20] + ("..." if len(prompt) > 20 else "")
            update_conversation_title(conv_id, new_title)

        st.rerun()