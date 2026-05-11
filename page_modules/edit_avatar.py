import streamlit as st
from utils.db import get_avatar, update_family_avatar, get_user_by_id
from utils.auth import check_premium


def show():
    st.title("✏️ 编辑家人AI分身")

    # 权限检查
    if not check_premium(st.session_state.user_id):
        st.error("此功能为高级会员专属，请先升级。")
        if st.button("前往升级"):
            st.session_state.nav_page = "🌟 升级会员"
            st.rerun()
        st.stop()

    avatar_id = st.session_state.get("editing_avatar_id")
    if not avatar_id:
        st.error("没有选择要编辑的分身，请从家人绑定页面进入。")
        if st.button("返回家人绑定"):
            st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
            st.rerun()
        st.stop()

    avatar_data = get_avatar(avatar_id)
    if not avatar_data:
        st.error("分身不存在")
        if st.button("返回家人绑定"):
            st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
            st.rerun()
        st.stop()

    # avatar_data 列顺序示例: (id, user_id, family_id, avatar_name, personality, speech_samples, voice_model_path, created_at, family_name)
    # 根据你实际 get_avatar 返回的字段调整索引
    avatar_name = avatar_data[3]
    personality = avatar_data[4]
    speech_samples = avatar_data[5]

    with st.form("edit_avatar_form"):
        new_name = st.text_input("分身显示名称", value=avatar_name)
        new_personality = st.text_area("性格描述", value=personality)
        new_speech = st.text_area("说话样本（可选）", value=speech_samples if speech_samples else "")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("保存修改")
        with col2:
            cancelled = st.form_submit_button("取消")

        if submitted:
            if not new_personality:
                st.error("请至少填写性格描述")
            else:
                update_family_avatar(avatar_id, new_name, new_personality, new_speech)
                st.success("分身信息已更新")
                # 清理状态并返回家人页面
                if "editing_avatar_id" in st.session_state:
                    del st.session_state.editing_avatar_id
                st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
                st.rerun()
        if cancelled:
            if "editing_avatar_id" in st.session_state:
                del st.session_state.editing_avatar_id
            st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
            st.rerun()