import streamlit as st
from utils.db import get_avatar, update_family_avatar, get_user_by_id

def show():
    st.title("✏️ 编辑家人AI分身")

    # ----- 权限检查：使用已缓存的订阅状态 -----
    if st.session_state.get("user_subscription") != "premium":
        st.error("此功能为高级会员专属，请先升级。")
        if st.button("前往升级"):
            st.session_state.nav_page = "🌟 升级会员"
            st.rerun()
        st.stop()

    # 获取要编辑的分身 ID
    avatar_id = st.session_state.get("editing_avatar_id")
    if not avatar_id:
        st.error("没有选择要编辑的分身，请从家人绑定页面进入。")
        if st.button("返回家人绑定"):
            st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
            st.rerun()
        st.stop()

    # ----- 从缓存或数据库加载分身数据 -----
    cache_key = f"avatar_{avatar_id}"
    if cache_key not in st.session_state:
        # 首次加载，从数据库读取
        avatar_data = get_avatar(avatar_id)
        if not avatar_data:
            st.error("分身不存在")
            if st.button("返回家人绑定"):
                st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
                st.rerun()
            st.stop()
        # 存入缓存，假设 get_avatar 返回元组，索引需根据实际返回值调整
        st.session_state[cache_key] = avatar_data
    else:
        avatar_data = st.session_state[cache_key]

    # 根据你的 get_avatar 返回值结构调整索引
    # 假设返回字段顺序是: (id, user_id, family_id, avatar_name, personality, speech_samples, voice_model_path, created_at, family_name)
    avatar_name = avatar_data[3] if len(avatar_data) > 3 else ""
    personality = avatar_data[4] if len(avatar_data) > 4 else ""
    speech_samples = avatar_data[5] if len(avatar_data) > 5 else ""

    # ----- 编辑表单 -----
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
                # 1. 更新数据库
                update_family_avatar(avatar_id, new_name, new_personality, new_speech)
                # 2. 清除缓存，下次进入页面或家人绑定页会重新加载
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.success("分身信息已更新")
                # 3. 清理编辑状态并跳转
                if "editing_avatar_id" in st.session_state:
                    del st.session_state.editing_avatar_id
                st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
                st.rerun()
        if cancelled:
            # 取消编辑，直接跳转，不清除缓存（保留原数据以备下次编辑）
            if "editing_avatar_id" in st.session_state:
                del st.session_state.editing_avatar_id
            st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
            st.rerun()