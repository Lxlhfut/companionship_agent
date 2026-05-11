import streamlit as st
from utils.db import create_user, authenticate_user

def show():
    st.title("🔐 登录 / 注册")
    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        username = st.text_input("用户名", key="login_username")
        password = st.text_input("密码", type="password", key="login_password")
        if st.button("登录"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.user_id = user[0]
                st.session_state.user_name = user[1]
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误")

    with tab2:
        new_username = st.text_input("用户名", key="reg_username")
        new_password = st.text_input("密码", type="password", key="reg_password")
        name = st.text_input("姓名")
        age = st.number_input("年龄", min_value=0, max_value=120, step=1)
        phone = st.text_input("手机号")
        if st.button("注册"):
            if not new_username or not new_password or not name:
                st.error("请填写必填项")
            else:
                user_id = create_user(new_username, new_password, name, age, phone)
                if user_id:
                    st.success("注册成功，请登录")
                else:
                    st.error("用户名已存在")