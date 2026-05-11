import streamlit as st
from utils.db import get_alert_rules, add_alert_rule
from utils.auth import check_premium

def show():
    st.title("⚠️ 异常行为预警设置")
    user_id = st.session_state.user_id
    if not check_premium(user_id):
        st.warning("高级会员功能")
        return

    # 显示当前规则
    st.subheader("当前预警规则")
    rules = get_alert_rules(user_id)
    for r in rules:
        st.write(f"{r[2]} - 阈值: {r[3]} - 通知方式: {r[4]}")

    # 添加新规则
    with st.form("add_alert"):
        rule_type = st.selectbox("预警类型", ["inactivity (无活动)", "device_offline (设备离线)", "fall (跌倒检测)"])
        threshold = st.text_input("阈值", "24 小时")
        method = st.multiselect("通知方式", ["APP推送", "短信", "微信"])
        if st.form_submit_button("添加规则"):
            add_alert_rule(user_id, rule_type, threshold, ",".join(method))
            st.success("规则已添加")
            st.rerun()