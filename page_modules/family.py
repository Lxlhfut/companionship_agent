import streamlit as st
from utils.db import (
    add_family_binding, get_family_members, get_elders_for_family, get_user_by_id,
    get_avatar_by_family_and_elder, delete_family_avatar
)
from utils.auth import check_premium



def show():
    st.title("👨‍👩‍👧 家人绑定")
    user_id = st.session_state.user_id

    tab1, tab2 = st.tabs(["我的家人", "添加家人"])

    with tab1:
        elders = get_elders_for_family(user_id)
        if elders:
            st.subheader("我照料的老人")
            for e in elders:
                elder_id = e[0]
                # 检查当前用户是否已为这位老人创建了分身
                existing_avatar = get_avatar_by_family_and_elder(user_id, elder_id)

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{e[1]}**（{e[2]}）")
                with col2:
                    if existing_avatar:
                        # 已有分身 → 显示编辑按钮
                        if st.button("✏️ 编辑分身", key=f"edit_avatar_{elder_id}"):
                            st.session_state.editing_avatar_id = existing_avatar[0]
                            st.session_state.nav_page = "✏️ 编辑分身"
                            st.rerun()
                    else:
                        # 无分身 → 显示创建按钮
                        if st.button("🤖 创建分身", key=f"create_avatar_{elder_id}"):
                            st.session_state.target_elder_id = elder_id
                            st.session_state.target_family_id = user_id
                            st.session_state.nav_page = "🤖 创建分身"
                            st.rerun()
                with col3:
                    if existing_avatar:
                        # 删除按钮（使用会话状态实现确认）
                        if st.button("🗑️ 删除分身", key=f"delete_avatar_{elder_id}"):
                            st.session_state.confirm_delete_avatar_id = existing_avatar[0]
                            st.session_state.confirm_delete_avatar_name = existing_avatar[1]
                            st.rerun()
        else:
            st.info("您还没有绑定照料的老人")
        family = get_family_members(user_id)
        if family:
            st.subheader("关注我的家人")
            for f in family:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{f[1]}**（{f[2]}）")
                with col2:
                    if st.button("创建分身", key=f"create_avatar_fam_{f[0]}"):
                        st.session_state.target_elder_id = user_id
                        st.session_state.target_family_id = f[0]
                        st.session_state.nav_page = "🤖 创建分身"
                        st.rerun()
        else:
            st.info("还没有家人关注您")
        if "confirm_delete_avatar_id" in st.session_state:
            avatar_id = st.session_state.confirm_delete_avatar_id
            avatar_name = st.session_state.confirm_delete_avatar_name
            st.warning(f"确定要删除「{avatar_name}」分身吗？此操作不可恢复。")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("确认删除", key="confirm_del"):
                    delete_family_avatar(avatar_id)
                    st.success(f"分身「{avatar_name}」已删除")
                    # 清理状态
                    for key in ["confirm_delete_avatar_id", "confirm_delete_avatar_name"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            with col_no:
                if st.button("取消", key="cancel_del"):
                    for key in ["confirm_delete_avatar_id", "confirm_delete_avatar_name"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

    with tab2:
        st.subheader("添加家人关系")
        search_name = st.text_input("输入家人的用户名")
        if st.button("搜索"):
            import sqlite3
            from utils.db import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, name FROM users WHERE username=?", (search_name,))
            result = c.fetchone()
            conn.close()
            if result:
                st.session_state.searched_user = result
                st.success(f"找到用户：{result[1]}")
            else:
                st.error("未找到该用户")

        if "searched_user" in st.session_state:
            target_id, target_name = st.session_state.searched_user
            relationship = st.selectbox("关系", ["子女", "配偶", "兄弟姐妹", "护工", "其他"])
            if st.button("确认绑定"):
                add_family_binding(user_id, target_id, relationship)
                st.success("绑定成功！")
                del st.session_state.searched_user
                st.rerun()