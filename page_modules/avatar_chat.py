import streamlit as st
from utils.db import get_family_avatars_for_elder, get_avatar
from agents.family_avatar_agent import FamilyAvatarAgent
from utils.auth import check_premium

def show():
    st.title("💬 家人AI分身")
    user_id = st.session_state.user_id

    # 从 session_state 中获取订阅状态（已在 app.py 中缓存），避免重复调用数据库
    if st.session_state.get("user_subscription", 'free') != 'premium':
        st.warning("高级会员功能")
        return

    # 初始化或获取缓存的家人分身列表
    cache_key_avatars = f"avatars_{user_id}"
    if cache_key_avatars not in st.session_state:
        st.session_state[cache_key_avatars] = get_family_avatars_for_elder(user_id)

    avatars = st.session_state[cache_key_avatars]
    if not avatars:
        st.info("还没有家人为你创建AI分身。\n\n请让你的子女登录后，在「家人绑定 - 我照料的老人」旁点击「创建分身」。")
        return

    avatar_names = [a[1] for a in avatars]
    selected = st.selectbox("选择你想聊天的家人", avatar_names)
    avatar_id = avatars[avatar_names.index(selected)][0]

    # 缓存当前分身的详细信息（避免每次切换都查询数据库）
    cache_key_avatar_data = f"avatar_data_{avatar_id}"
    if cache_key_avatar_data not in st.session_state:
        st.session_state[cache_key_avatar_data] = get_avatar(avatar_id)

    avatar_data = st.session_state[cache_key_avatar_data]

    # 聊天历史缓存（每个分身独立，使用分身 ID 作为后缀）
    history_key = f"avatar_history_{avatar_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # 显示历史消息
    for msg in st.session_state[history_key]:
        st.chat_message(msg["role"]).write(msg["content"])

    agent = FamilyAvatarAgent()   # 注意：Agent 内部可能也有外部 API 调用，可单独考虑缓存
    if prompt := st.chat_input("说点什么..."):
        st.session_state[history_key].append({"role": "user", "content": prompt})
        with st.spinner("思考中..."):
            response = agent.get_avatar_response(
                avatar_data,
                st.session_state.user_name,
                prompt,
                st.session_state[history_key]
            )
        st.session_state[history_key].append({"role": "assistant", "content": response})
        st.rerun()