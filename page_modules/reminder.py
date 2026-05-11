import streamlit as st
from utils.db import (
    add_reminder, get_reminders, delete_reminder, update_reminder,
    get_reminder_by_id, check_duplicate_reminder, get_reminders_at_time
)
import datetime
import time as time_module
import pandas as pd



def format_weekdays(days_str):
    """将 "0,2,4" 转换为 "周一、周三、周五" """
    if not days_str:
        return "每天"
    week_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days = [int(d.strip()) for d in days_str.split(',') if d.strip()]
    return "、".join([week_map[d] for d in days])


def parse_weekdays(selected_days):
    """将选中的星期列表转换为存储格式"""
    if not selected_days:
        return ""
    week_indices = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    indices = [str(week_indices[d]) for d in selected_days]
    return ",".join(indices)


def show():
    st.title("💊 今日用药提醒")
    user_id = st.session_state.user_id

    # 初始化状态变量
    if "editing_reminder_id" not in st.session_state:
        st.session_state.editing_reminder_id = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0  # 0=我的提醒, 1=添加提醒
    if "show_success_msg" not in st.session_state:
        st.session_state.show_success_msg = False
    if "success_msg_content" not in st.session_state:
        st.session_state.success_msg_content = ""
    if "show_conflict_analysis" not in st.session_state:
        st.session_state.show_conflict_analysis = False
    if "conflict_data" not in st.session_state:
        st.session_state.conflict_data = None

    # 显示成功消息（自动消失）
    if st.session_state.show_success_msg:
        st.success(st.session_state.success_msg_content)
        time_module.sleep(3)  # 使用别名
        st.session_state.show_success_msg = False
        st.rerun()

    # 获取今天的提醒
    today = datetime.datetime.now()
    current_time = today.time()
    current_weekday = today.weekday()

    all_reminders = get_reminders(user_id)

    # 筛选今天需要服用的药物
    today_reminders = []
    for r in all_reminders:
        r_id, name, dosage, time_str, days_str, active = r
        if not active:
            continue
        # 检查星期
        if days_str:
            allowed_days = [int(d.strip()) for d in days_str.split(',') if d.strip()]
            if current_weekday not in allowed_days:
                continue
        # 解析时间
        reminder_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        today_reminders.append({
            "id": r_id,
            "name": name,
            "dosage": dosage,
            "time": reminder_time,
            "time_str": time_str,
            "days_str": days_str
        })

    # 按时间排序
    today_reminders.sort(key=lambda x: x["time"])

    # 显示今日用药列表
    st.subheader(f"📅 {today.strftime('%Y年%m月%d日 %A')}")

    if today_reminders:
        st.markdown("""
        <style>
        .expired-medicine {
            color: gray;
            text-decoration: line-through;
            opacity: 0.7;
        }
        .active-medicine {
            color: #2e7d32;
            font-weight: 500;
        }
        .current-medicine {
            color: #1976d2;
            font-weight: bold;
            background-color: #e3f2fd;
            padding: 4px 8px;
            border-radius: 4px;
        }
        </style>
        """, unsafe_allow_html=True)

        for med in today_reminders:
            is_expired = med["time"] < current_time
            is_current = abs((datetime.datetime.combine(today.date(), med["time"]) -
                              datetime.datetime.combine(today.date(), current_time)).total_seconds()) < 1800  # 30分钟内

            if is_expired:
                st.markdown(
                    f'<span class="expired-medicine">✅ {med["name"]} {med["dosage"]} - {med["time_str"]} (已过时)</span>',
                    unsafe_allow_html=True)
            elif is_current:
                st.markdown(
                    f'<span class="current-medicine">🔔 {med["name"]} {med["dosage"]} - {med["time_str"]} (现在该准备服药了)</span>',
                    unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="active-medicine">⏰ {med["name"]} {med["dosage"]} - {med["time_str"]}</span>',
                            unsafe_allow_html=True)
    else:
        st.info("今天没有需要服用的药物")

    st.divider()

    # 主标签页（使用session_state控制激活的tab）
    tab1, tab2 = st.tabs(["📋 所有提醒", "➕ 添加提醒"])

    # 根据active_tab自动切换
    if st.session_state.active_tab == 1:
        # 切换到添加提醒tab（通过JS）
        st.markdown("""
        <script>
            setTimeout(function() {
                var tabs = window.parent.document.querySelectorAll('button[role="tab"]');
                if (tabs.length >= 2) {
                    tabs[1].click();
                }
            }, 100);
        </script>
        """, unsafe_allow_html=True)
        st.session_state.active_tab = 0  # 重置

    # ---------- 标签页1：所有提醒 ----------
    with tab1:
        reminders = get_reminders(user_id)
        if not reminders:
            st.info("还没有用药提醒，点击「添加提醒」创建")
        else:
            # 转换为DataFrame便于展示
            df_data = []
            for r in reminders:
                r_id, name, dosage, time_str, days_str, active = r
                df_data.append({
                    "ID": r_id,
                    "药品": name,
                    "剂量": dosage,
                    "时间": time_str,
                    "重复": format_weekdays(days_str),
                    "状态": "✅ 启用" if active else "⏸️ 停用"
                })
            df = pd.DataFrame(df_data)

            st.dataframe(
                df[["药品", "剂量", "时间", "重复", "状态"]],
                use_container_width=True,
                hide_index=True
            )

            # 操作区域
            st.subheader("管理提醒")
            selected_id = st.selectbox(
                "选择要操作的提醒",
                options=[r[0] for r in reminders],
                format_func=lambda x: f"ID:{x} - {next((r[1] for r in reminders if r[0] == x), '')}"
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ 编辑", use_container_width=True):
                    st.session_state.editing_reminder_id = selected_id
                    st.rerun()
            with col2:
                if st.button("🗑️ 删除", use_container_width=True):
                    delete_reminder(selected_id)
                    st.session_state.show_success_msg = True
                    st.session_state.success_msg_content = "删除成功！"
                    st.rerun()
            with col3:
                current = get_reminder_by_id(selected_id)
                if current:
                    new_active = 0 if current[5] else 1
                    action = "停用" if current[5] else "启用"
                    if st.button(f"⏸️ {action}", use_container_width=True):
                        update_reminder(selected_id, current[1], current[2], current[3], current[4], new_active)
                        st.session_state.show_success_msg = True
                        st.session_state.success_msg_content = f"已{action}"
                        st.rerun()

            # 编辑表单
            if st.session_state.editing_reminder_id:
                edit_id = st.session_state.editing_reminder_id
                reminder = get_reminder_by_id(edit_id)
                if reminder:
                    st.divider()
                    st.subheader(f"✏️ 编辑提醒 (ID: {edit_id})")
                    with st.form("edit_reminder_form"):
                        med = st.text_input("药品名称", value=reminder[1])
                        dosage = st.text_input("剂量", value=reminder[2])
                        time = st.time_input("提醒时间", value=datetime.datetime.strptime(reminder[3], "%H:%M").time())
                        current_days = []
                        if reminder[4]:
                            indices = [int(i) for i in reminder[4].split(',')]
                            week_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                            current_days = [week_map[i] for i in indices]
                        days = st.multiselect(
                            "重复日期（不选则每天）",
                            ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                            default=current_days
                        )
                        active = st.checkbox("启用提醒", value=bool(reminder[5]))

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            submitted = st.form_submit_button("保存修改")
                        with col_cancel:
                            cancel = st.form_submit_button("取消")

                        if submitted:
                            time_str = time.strftime("%H:%M")
                            days_str = parse_weekdays(days)
                            duplicate_id = check_duplicate_reminder(user_id, med, time_str, exclude_id=edit_id)
                            if duplicate_id:
                                st.error("已存在相同药品和时间的提醒，请修改时间或药品名")
                            else:
                                update_reminder(edit_id, med, dosage, time_str, days_str, 1 if active else 0)
                                st.session_state.show_success_msg = True
                                st.session_state.success_msg_content = "修改成功！"
                                st.session_state.editing_reminder_id = None
                                st.rerun()
                        if cancel:
                            st.session_state.editing_reminder_id = None
                            st.rerun()

    # ---------- 标签页2：添加提醒 ----------
    with tab2:
        with st.form("add_reminder_form"):
            medicine = st.text_input("药品名称")
            dosage = st.text_input("剂量（如：1片）")
            time = st.time_input("提醒时间", value=datetime.time(8, 0))
            days = st.multiselect(
                "重复日期（不选则每天提醒）",
                ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            )
            submitted = st.form_submit_button("添加提醒")

            if submitted:
                if not medicine:
                    st.error("请填写药品名称")
                else:
                    time_str = time.strftime("%H:%M")
                    days_str = parse_weekdays(days)

                    # 检查重复
                    duplicate_id = check_duplicate_reminder(user_id, medicine, time_str)
                    if duplicate_id:
                        st.error("已存在相同药品和时间的提醒！")
                    else:
                        # 检查冲突
                        existing_same_time = get_reminders_at_time(user_id, time_str)
                        conflict_meds = []
                        for r in existing_same_time:
                            if not days_str or not r[4]:  # 至少有一个是每天
                                conflict_meds.append(r)
                            elif set(days_str.split(',')) & set(r[4].split(',')):  # 有交集
                                conflict_meds.append(r)

                        if conflict_meds:
                            st.session_state.conflict_data = {
                                "medicine": medicine,
                                "dosage": dosage,
                                "time_str": time_str,
                                "days_str": days_str,
                                "conflict_meds": conflict_meds
                            }
                            st.session_state.show_conflict_analysis = True
                            st.rerun()
                        else:
                            # 无冲突，直接添加
                            add_reminder(user_id, medicine, dosage, time_str, days_str)
                            st.session_state.show_success_msg = True
                            st.session_state.success_msg_content = "添加成功！"
                            st.session_state.active_tab = 0
                            st.rerun()

        # 处理冲突分析
        if st.session_state.show_conflict_analysis and st.session_state.conflict_data:
            data = st.session_state.conflict_data
            st.warning(f"⚠️ 同一时间已有 {len(data['conflict_meds'])} 种药物需要服用")
            conflict_names = ", ".join([r[1] for r in data['conflict_meds']])
            st.write(f"已有药物：{conflict_names}")
            st.write(f"新添加：{data['medicine']} {data['dosage']}")

            analyze = st.checkbox("需要AI分析同时服用的安全性吗？", key="analyze_checkbox")

            if analyze:
                if st.button("开始AI分析"):
                    with st.spinner("AI分析中..."):
                        all_meds = list(data['conflict_meds'])
                        all_meds.append((None, data['medicine'], data['dosage'], data['time_str'], data['days_str'], 1))
                        suggestion = st.session_state.reminder_agent.analyze_conflicts(all_meds)
                        st.info(f"💡 用药建议：\n\n{suggestion}")
                        st.session_state.ai_suggestion = suggestion

            st.divider()
            confirm = st.checkbox("我已知晓，仍要添加", key="confirm_add")

            if confirm:
                if st.button("确认添加", type="primary"):
                    add_reminder(user_id, data['medicine'], data['dosage'], data['time_str'], data['days_str'])
                    st.session_state.show_success_msg = True
                    st.session_state.success_msg_content = "添加成功！"
                    st.session_state.show_conflict_analysis = False
                    st.session_state.conflict_data = None
                    st.session_state.active_tab = 0
                    st.rerun()

            if st.button("取消添加"):
                st.session_state.show_conflict_analysis = False
                st.session_state.conflict_data = None
                st.rerun()