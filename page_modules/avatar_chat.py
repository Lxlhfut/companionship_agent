import streamlit as st
from utils.db import get_family_avatars_for_elder, get_avatar
from agents.family_avatar_agent import FamilyAvatarAgent
from utils.auth import check_premium

def show():

    st.title("💬 家人AI分身")
    user_id = st.session_state.user_id
    if not check_premium(user_id):
        st.warning("高级会员功能")
        return

    agent = FamilyAvatarAgent()
    avatars = get_family_avatars_for_elder(user_id)
    if not avatars:
        st.info("还没有家人为你创建AI分身。\n\n请让你的子女登录后，在「家人绑定 - 我照料的老人」旁点击「创建分身」。")
        return

    avatar_names = [a[1] for a in avatars]
    selected = st.selectbox("选择你想聊天的家人", avatar_names)
    avatar_id = avatars[avatar_names.index(selected)][0]
    avatar_data = get_avatar(avatar_id)

    if "avatar_history" not in st.session_state:
        st.session_state.avatar_history = []

    for msg in st.session_state.avatar_history:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("说点什么..."):
        st.session_state.avatar_history.append({"role": "user", "content": prompt})
        with st.spinner("思考中..."):
            response = agent.get_avatar_response(
                avatar_data, st.session_state.user_name,
                prompt, st.session_state.avatar_history
            )
        st.session_state.avatar_history.append({"role": "assistant", "content": response})
        st.rerun()