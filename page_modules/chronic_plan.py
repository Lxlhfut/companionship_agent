import streamlit as st
from utils.db import (
    get_chronic_profile, upsert_chronic_profile,
    save_management_plan, get_user_plans, update_plan_text, delete_plan, get_plan_by_id
)
from agents.chronic_disease_agent import ChronicDiseaseAgent
from utils.auth import check_premium

def show():
    st.title("📋 AI慢病管理计划")
    user_id = st.session_state.user_id
    if not check_premium(user_id):
        st.warning("高级会员功能")
        return

    agent = ChronicDiseaseAgent()
    profile = get_chronic_profile(user_id)

    tab1, tab2 = st.tabs(["管理档案与生成", "历史计划"])

    # ---------- 标签1：档案编辑与生成 ----------
    with tab1:
        with st.expander("编辑个人慢病档案"):
            with st.form("chronic_form"):
                disease = st.selectbox("主要慢病", ["高血压", "糖尿病", "高血脂", "其他"])
                weight = st.number_input("体重(kg)", 30.0, 200.0, 65.0)
                height = st.number_input("身高(cm)", 100, 250, 165)
                bp_target = st.text_input("血压控制目标", "120/80")
                sugar_target = st.number_input("空腹血糖目标(mmol/L)", 3.0, 10.0, 6.1)
                meds = st.text_area("每日用药（格式：药名,剂量,时间）")
                activity = st.selectbox("活动水平", ["久坐", "轻度活动", "中度活动"])

                if st.form_submit_button("保存档案"):
                    upsert_chronic_profile(
                        user_id,
                        disease_type=disease,
                        weight=weight,
                        height=height,
                        blood_pressure_target=bp_target,
                        blood_sugar_target=sugar_target,
                        daily_medications=meds,
                        activity_level=activity
                    )
                    st.success("档案已更新")
                    st.rerun()

        if profile is None:
            st.warning("请先填写慢病档案")
        else:
            if st.button("生成今日管理计划"):
                with st.spinner("AI正在生成专属计划..."):
                    plan = agent.generate_plan(profile)
                    st.markdown("### 今日计划")
                    st.write(plan)

                    # 保存计划到数据库
                    save_management_plan(user_id, plan)
                    st.success("该计划已自动保存到历史记录")

    # ---------- 标签2：历史计划管理 ----------
    with tab2:
        st.subheader("📂 历史管理计划")
        plans = get_user_plans(user_id)
        if not plans:
            st.info("暂无保存的计划，请先生成。")
            return

        for plan in plans:
            plan_id, text, created = plan
            col1, col2, col3, col4 = st.columns([6,1,1,1])
            with col1:
                st.write(f"**日期**: {created}")
                st.caption(text[:150] + "..." if len(text) > 150 else text)
            with col2:
                if st.button("详细", key=f"view_{plan_id}"):
                    st.session_state.view_plan_id = plan_id
                    st.session_state.edit_mode = False
                    st.rerun()
            with col3:
                if st.button("编辑", key=f"edit_{plan_id}"):
                    st.session_state.edit_plan_id = plan_id
                    st.session_state.edit_mode = True
                    st.rerun()
            with col4:
                if st.button("删除", key=f"del_{plan_id}"):
                    delete_plan(plan_id)
                    st.success("已删除")
                    st.rerun()
            st.divider()

        # 查看计划详情（单独显示）
        if "view_plan_id" in st.session_state and st.session_state.view_plan_id:
            plan_id = st.session_state.view_plan_id
            plan = get_plan_by_id(plan_id)
            if plan:
                st.markdown("---")
                st.subheader("计划详情")
                st.write(plan[2])
                if st.button("关闭"):
                    del st.session_state.view_plan_id
                    st.rerun()

        # 编辑计划
        if "edit_plan_id" in st.session_state and st.session_state.edit_mode:
            plan_id = st.session_state.edit_plan_id
            plan = get_plan_by_id(plan_id)
            if plan:
                st.markdown("---")
                st.subheader("编辑计划内容")
                new_text = st.text_area("修改计划", value=plan[2], height=300, key="edit_textarea")
                col_s, col_c = st.columns([1,1])
                with col_s:
                    if st.button("保存修改", key="save_edit"):
                        update_plan_text(plan_id, new_text)
                        st.success("已更新")
                        del st.session_state.edit_plan_id
                        st.session_state.edit_mode = False
                        st.rerun()
                with col_c:
                    if st.button("取消", key="cancel_edit"):
                        del st.session_state.edit_plan_id
                        st.session_state.edit_mode = False
                        st.rerun()