import streamlit as st
from utils.db import get_user_subscription

def check_premium(user_id):
    """检查是否为有效高级会员"""
    sub_type, expiry = get_user_subscription(user_id)
    return sub_type == 'premium'

def premium_required(page_func):
    """装饰器：需要高级会员才能访问"""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('user_id'):
            st.error("请先登录")
            st.stop()
        if not check_premium(st.session_state.user_id):
            st.warning("🔒 此功能为高级会员专属，请先升级")
            st.markdown("[点击升级会员](#)")  # 可替换为跳转升级页面的按钮
            # 实际使用按钮跳转
            if st.button("前往升级"):
                st.session_state.nav_radio = "🌟 升级会员"
                st.rerun()
            st.stop()
        return page_func(*args, **kwargs)
    return wrapper