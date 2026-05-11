import streamlit as st
from utils.db import get_user_by_id, get_family_members, get_elders_for_family, get_reminders
from datetime import datetime, timedelta
from agents.alert_agent import AlertAgent

def show():
    st.title(f"🏠 欢迎回来，{st.session_state.user_name}")
    user = get_user_by_id(st.session_state.user_id)
    reminders = get_reminders(st.session_state.user_id)
    family = get_family_members(st.session_state.user_id)
    elders = get_elders_for_family(st.session_state.user_id)

    alert_agent = AlertAgent()
    # 假设 last_activity 存储在session或数据库，这里模拟为12小时前
    last_activity = datetime.now() - timedelta(hours=12)
    alert_triggered, alert_msg = alert_agent.check_inactivity(st.session_state.user_id, last_activity)
    if alert_triggered:
        st.error(f"⚠️ {alert_msg}")

    # 第一行：问候语和时间
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        greeting = "早上好"
        emoji = "🌅"
    elif 12 <= current_hour < 14:
        greeting = "中午好"
        emoji = "☀️"
    elif 14 <= current_hour < 18:
        greeting = "下午好"
        emoji = "🌤️"
    else:
        greeting = "晚上好"
        emoji = "🌙"

    st.caption(f"{emoji} {greeting}，今天是 {datetime.now().strftime('%Y年%m月%d日 %A')}")

    st.divider()

    # 第二行：核心数据卡片
    col1, col2, col3, col4 = st.columns(4)

    # with col1:
    #     st.metric(
    #         label="👤 年龄",
    #         value=f"{user[3]}岁" if user[3] else "未填写"
    #     )

    with col2:
        st.metric(
            label="💊 今日用药",
            value=f"{len(reminders)} 项"
        )

    with col3:
        st.metric(
            label="👨‍👩‍👧 关注家人",
            value=f"{len(elders)} 人"
        )

    with col4:
        st.metric(
            label="❤️ 关注我的",
            value=f"{len(family)} 人"
        )

    st.divider()

    # 第三行：今日用药提醒列表
    st.subheader("💊 今日用药提醒")
    if reminders:
        # 按时间排序
        reminders_sorted = sorted(reminders, key=lambda x: x[3])
        for r in reminders_sorted[:5]:  # 最多显示5条
            medicine_name = r[1]
            dosage = r[2]
            time_str = r[3]
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{medicine_name}**")
                with col2:
                    st.write(f"剂量：{dosage}")
                with col3:
                    st.write(f"⏰ {time_str}")
                st.divider()
    else:
        st.info("暂无用药提醒，点击左侧「用药提醒」添加")

    # 第四行：健康小贴士（每日更新）
    st.divider()
    st.subheader("📋 健康小贴士")

    # 根据年龄和季节生成不同的小贴士
    tips = [
        "💧 每天喝够8杯水，保持身体水分充足",
        "🚶 饭后散步30分钟，有助于消化和睡眠",
        "😴 保持规律作息，晚上11点前入睡",
        "🧠 多与人交流、下棋、看书，保持大脑活跃",
        "🥗 多吃蔬菜水果，少吃油腻食物",
        "🏥 定期体检，关注血压血糖变化",
        "☀️ 每天晒太阳15分钟，补充维生素D",
        "🪑 久坐后记得站起来活动一下",
        "📞 常和家人通电话，保持心情愉快",
        "💊 按时服药，不要随意停药"
    ]

    import random
    # 根据日期生成固定的随机数，让同一天显示相同的小贴士
    day_seed = datetime.now().day + datetime.now().month
    random.seed(day_seed)
    selected_tip = random.choice(tips)

    st.success(f"💡 {selected_tip}")

    # 第五行：家人关怀动态（如果有绑定家人）
    if family or elders:
        st.divider()
        st.subheader("👨‍👩‍👧 家人关怀")

        tab1, tab2 = st.tabs(["关注我的家人", "我关注的老人"])

        with tab1:
            if family:
                for f in family:
                    st.write(f"• {f[1]}（{f[2]}）正在关注您的健康")
            else:
                st.info("还没有家人关注您，点击左侧「家人绑定」添加")

        with tab2:
            if elders:
                for e in elders:
                    st.write(f"• {e[1]}（{e[2]}）")
                    # 这里可以扩展显示老人的健康摘要
            else:
                st.info("您还没有关注其他老人，点击左侧「家人绑定」添加")