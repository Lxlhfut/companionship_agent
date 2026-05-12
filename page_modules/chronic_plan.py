import streamlit as st
from utils.db import (
    get_chronic_profile, upsert_chronic_profile,
    save_management_plan, get_user_plans, update_plan_text, delete_plan, get_plan_by_id
)
from agents.chronic_disease_agent import ChronicDiseaseAgent
from utils.auth import check_premium

# ---------- 缓存辅助函数 ----------
def get_cached_profile(user_id):
    """获取慢病档案（优先从缓存读取）"""
    cache_key = f"chronic_profile_{user_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = get_chronic_profile(user_id)
    return st.session_state[cache_key]

def refresh_cached_profile(user_id):
    """刷新档案缓存（在保存档案后调用）"""
    cache_key = f"chronic_profile_{user_id}"
    st.session_state[cache_key] = get_chronic_profile(user_id)

def get_cached_plans(user_id):
    """获取历史计划列表（优先从缓存读取）"""
    cache_key = f"chronic_plans_{user_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = get_user_plans(user_id)
    return st.session_state[cache_key]

def refresh_cached_plans(user_id):
    """刷新计划列表缓存（在增删改后调用）"""
    cache_key = f"chronic_plans_{user_id}"
    st.session_state[cache_key] = get_user_plans(user_id)

def show():
    st.title("📋 AI慢病管理计划")
    user_id = st.session_state.user_id
    if not check_premium(user_id):
        st.warning("高级会员功能")
        return

    agent = ChronicDiseaseAgent()
    profile = get_cached_profile(user_id)   # 使用缓存

    tab1, tab2 = st.tabs(["管理档案与生成", "历史计划"])

    # ---------- 标签1：档案编辑与生成 ----------
    with tab1:
        with st.expander("编辑个人慢病档案"):
            with st.form("chronic_form"):
                # 从缓存中读取当前值并作为表单默认值
                if profile:
                    current_disease = profile[1] if profile[1] else "高血压"
                    current_weight = float(profile[4]) if profile[4] is not None else 65.0
                    current_height = int(profile[5]) if profile[5] is not None else 165
                    current_bp_target = profile[7] if profile[7] else "120/80"
                    current_sugar_target = float(profile[6]) if profile[6] is not None else 6.1
                    current_meds = profile[8] if profile[8] else ""
                    current_activity = profile[9] if profile[9] else "轻度活动"
                else:
                    current_disease = "高血压"
                    current_weight = 65.0
                    current_height = 165
                    current_bp_target = "120/80"
                    current_sugar_target = 6.1
                    current_meds = ""
                    current_activity = "轻度活动"

                disease = st.selectbox("主要慢病", ["高血压", "糖尿病", "高血脂", "其他"],
                                       index=["高血压", "糖尿病", "高血脂", "其他"].index(
                                           current_disease) if current_disease in ["高血压", "糖尿病", "高血脂",
                                                                                   "其他"] else 0)
                weight = st.number_input("体重(kg)", 30.0, 200.0, current_weight, step=0.1)
                height = st.number_input("身高(cm)", 100, 250, current_height, step=1)
                bp_target = st.text_input("血压控制目标", current_bp_target)
                sugar_target = st.number_input("空腹血糖目标(mmol/L)", 3.0, 10.0, current_sugar_target, step=0.1)
                meds = st.text_area("每日用药（格式：药名,剂量,时间）", current_meds)
                activity = st.selectbox("活动水平", ["久坐", "轻度活动", "中度活动"],
                                        index=["久坐", "轻度活动", "中度活动"].index(
                                            current_activity) if current_activity in ["久坐", "轻度活动",
                                                                                      "中度活动"] else 1)

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
                    refresh_cached_profile(user_id)
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
                    # 刷新计划列表缓存
                    refresh_cached_plans(user_id)
                    st.success("该计划已自动保存到历史记录")
                    st.rerun()

    # ---------- 标签2：历史计划管理 ----------
    with tab2:
        st.subheader("📂 历史管理计划")
        plans = get_cached_plans(user_id)   # 使用缓存
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
                    # 删除后刷新缓存
                    refresh_cached_plans(user_id)
                    # 如果删除的是正在查看或编辑的计划，清除相关状态
                    if "view_plan_id" in st.session_state and st.session_state.view_plan_id == plan_id:
                        del st.session_state.view_plan_id
                    if "edit_plan_id" in st.session_state and st.session_state.edit_plan_id == plan_id:
                        del st.session_state.edit_plan_id
                        st.session_state.edit_mode = False
                    st.success("已删除")
                    st.rerun()
            st.divider()

        # 查看计划详情（单独显示）
        if "view_plan_id" in st.session_state and st.session_state.view_plan_id:
            plan_id = st.session_state.view_plan_id
            plan = get_plan_by_id(plan_id)   # 单条详情无需缓存（只查一次）
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
                        # 更新后刷新列表缓存
                        refresh_cached_plans(user_id)
                        st.success("已更新")
                        del st.session_state.edit_plan_id
                        st.session_state.edit_mode = False
                        st.rerun()
                with col_c:
                    if st.button("取消", key="cancel_edit"):
                        del st.session_state.edit_plan_id
                        st.session_state.edit_mode = False
                        st.rerun()