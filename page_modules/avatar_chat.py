import streamlit as st
from utils.db import (
    get_family_avatars_for_elder, get_avatar,
    create_conversation, get_user_conversations, get_conversation_messages,
    save_message, update_conversation_title, delete_conversation, get_conversation
)
from agents.family_avatar_agent import FamilyAvatarAgent

def show():
    st.title("💬 家人AI分身")

    if "user_id" not in st.session_state:
        st.warning("请先登录")
        return

    user_id = st.session_state.user_id
    if st.session_state.get("user_subscription", 'free') != 'premium':
        st.warning("高级会员功能")
        return

    cache_key_avatars = f"avatars_{user_id}"
    if cache_key_avatars not in st.session_state:
        st.session_state[cache_key_avatars] = get_family_avatars_for_elder(user_id)

    avatars = st.session_state[cache_key_avatars]
    if not avatars:
        st.info("还没有家人为你创建AI分身。\n\n请让你的子女登录后，在「家人绑定 - 我照料的老人」旁点击「创建分身」。")
        return

    avatar_names = [a['avatar_name'] for a in avatars]
    selected_name = st.selectbox("选择你想聊天的家人", avatar_names)
    selected_avatar = avatars[avatar_names.index(selected_name)]
    avatar_id = selected_avatar['id']
    avatar_data = get_avatar(avatar_id)

    chat_type = "avatar"
    session_key = f"current_conversation_{avatar_id}"
    if session_key not in st.session_state:
        convs = get_user_conversations(user_id, chat_type, avatar_id=avatar_id, limit=1)
        if convs:
            st.session_state[session_key] = convs[0]['id']
        else:
            new_id = create_conversation(user_id, chat_type, avatar_id=avatar_id, title="新对话")
            st.session_state[session_key] = new_id

    conv_id = st.session_state[session_key]
    history_key = f"avatar_history_{conv_id}"
    if history_key not in st.session_state:
        db_messages = get_conversation_messages(conv_id)
        st.session_state[history_key] = [{"role": msg['role'], "content": msg['content']} for msg in db_messages]

    for msg in st.session_state[history_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    with st.sidebar:
        st.subheader(f"历史对话 - {selected_name}")
        if st.button("➕ 新对话", use_container_width=True):
            new_id = create_conversation(user_id, chat_type, avatar_id=avatar_id, title="新对话")
            st.session_state[session_key] = new_id
            st.session_state.pop(history_key, None)
            st.rerun()

        conversations = get_user_conversations(user_id, chat_type, avatar_id=avatar_id, limit=50)
        for conv in conversations:
            conv_id_loop = conv['id']
            title = conv['title']
            cols = st.columns([4, 1])
            with cols[0]:
                if st.button(title, key=f"avatar_conv_{conv_id_loop}", use_container_width=True):
                    st.session_state[session_key] = conv_id_loop
                    st.session_state.pop(f"avatar_history_{conv_id_loop}", None)
                    st.rerun()
            with cols[1]:
                if st.button("🗑️", key=f"avatar_del_{conv_id_loop}"):
                    delete_conversation(conv_id_loop)
                    if st.session_state[session_key] == conv_id_loop:
                        new_id = create_conversation(user_id, chat_type, avatar_id=avatar_id, title="新对话")
                        st.session_state[session_key] = new_id
                        st.session_state.pop(f"avatar_history_{new_id}", None)
                    st.rerun()

    agent = FamilyAvatarAgent()
    if prompt := st.chat_input("说点什么..."):
        st.session_state[history_key].append({"role": "user", "content": prompt})
        save_message(conv_id, "user", prompt)
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = agent.get_avatar_response(
                    avatar_data,
                    st.session_state.user_name,
                    prompt,
                    st.session_state[history_key]
                )
                st.write(response)

        st.session_state[history_key].append({"role": "assistant", "content": response})
        save_message(conv_id, "assistant", response)

        conv_info = get_conversation(conv_id)
        if conv_info and conv_info['title'] == "新对话":
            new_title = prompt[:20] + ("..." if len(prompt) > 20 else "")
            update_conversation_title(conv_id, new_title)

        st.rerun()