import streamlit as st
from utils.db import get_user_subscription, update_subscription

def show():
    st.title("🌟 升级高级会员")
    user_id = st.session_state.user_id
    sub_type, expiry = get_user_subscription(user_id)

    if sub_type == 'premium':
        st.success(f"✅ 您已是高级会员，有效期至：{expiry}")
        st.balloons()
        return

    st.markdown("""
    ## 选择适合您的计划
    | 功能 | 免费版 | 高级版 |
    |------|--------|--------|
    | 陪伴聊天 | ✅ | ✅ |
    | 基础用药提醒 | ✅ | ✅ |
    | 附近好去处 | ✅ | ✅ |
    | **深度体检报告解读**（历史趋势、风险预测） | ❌ | ✅ |
    | **AI慢病管理计划** | ❌ | ✅ |
    | **7x24小时异常行为预警** | ❌ | ✅ |
    | **家人AI分身** | ❌ | ✅ |
    """)

    plan = st.radio("选择方案", ["月付 ¥19.9/月", "年付 ¥199/年（省16%）"], horizontal=True)
    if plan == "月付 ¥19.9/月":
        days = 30
        price = 19.9
    else:
        days = 365
        price = 199

    st.markdown(f"### 应付金额：**¥{price}** （模拟支付）")

    # 模拟支付按钮
    if st.button("立即支付（模拟）", type="primary"):
        # 1. 更新数据库中的订阅信息
        update_subscription(user_id, 'premium', days=days)

        # 2. 刷新 session_state 中的缓存标记（让侧边栏下次重新加载订阅）
        st.session_state.user_subscription = 'premium'
        # 重新获取过期时间（update_subscription 内部已计算并存储，但未返回）
        # 为了同步 expiry，可以再查询一次
        _, new_expiry = get_user_subscription(user_id)
        st.session_state.subscription_expiry = new_expiry
        # 重要：重置订阅加载标记，强制侧边栏重新加载缓存
        st.session_state.subscription_loaded = False

        st.success("支付成功！您已是高级会员")
        st.balloons()
        # 延迟一秒钟让用户看到成功消息，然后刷新页面以更新侧边栏菜单
        st.rerun()