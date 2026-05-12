import streamlit as st
import pandas as pd
import json
from utils.auth import check_premium
from agents.enhanced_report_agent import EnhancedReportAgent
from utils.db import save_health_report, get_user_reports

def show():
    st.title("🔬 深度体检报告分析")
    user_id = st.session_state.user_id

    # 检查会员权限
    if not check_premium(user_id):
        st.warning("此功能为高级会员专属，请先升级")
        if st.button("前往升级"):
            st.session_state.nav_page = "🌟 升级会员"
            st.rerun()
        return

    # ---------- 缓存 Agent 实例 ----------
    if "enhanced_report_agent" not in st.session_state:
        st.session_state.enhanced_report_agent = EnhancedReportAgent()
    agent = st.session_state.enhanced_report_agent

    # ---------- 缓存：用户报告列表的版本号 ----------
    # 用于检测是否有新报告上传，从而决定是否需要重新分析
    if "last_report_count" not in st.session_state:
        st.session_state.last_report_count = len(get_user_reports(user_id))

    tab1, tab2 = st.tabs(["上传新报告", "历史趋势分析"])

    # ========== 选项卡1：上传新报告 ==========
    with tab1:
        uploaded = st.file_uploader("上传体检报告 PDF", type="pdf")
        if uploaded:
            with st.spinner("解析中..."):
                from agents.report_agent import ReportAgent
                basic_agent = ReportAgent()
                text = basic_agent.extract_text_from_pdf(uploaded)
                if not text:
                    st.error("无法提取文本，请确保PDF为文本格式")
                else:
                    indicators = agent.extract_indicators(text)
                    st.success("指标提取成功")
                    st.json(indicators)
                    save_health_report(user_id, text, json.dumps(indicators, ensure_ascii=False))
                    # 上传成功后，清除历史分析结果缓存，并更新报告计数
                    if "analysis_result" in st.session_state:
                        del st.session_state.analysis_result
                    if "history_data" in st.session_state:
                        del st.session_state.history_data
                    st.session_state.last_report_count = len(get_user_reports(user_id))
                    st.rerun()

    # ========== 选项卡2：历史趋势分析 ==========
    with tab2:
        st.subheader("历史指标趋势与风险分析")

        # 检查是否有新报告（用户可能通过其他方式上传，或刷新页面）
        current_count = len(get_user_reports(user_id))
        if current_count != st.session_state.last_report_count:
            # 报告数量变化，清除缓存
            if "analysis_result" in st.session_state:
                del st.session_state.analysis_result
            if "history_data" in st.session_state:
                del st.session_state.history_data
            st.session_state.last_report_count = current_count

        # 如果已有缓存的分析结果，直接展示；否则执行分析
        if st.button("开始分析") or ("analysis_result" in st.session_state):
            with st.spinner("AI分析中..."):
                # 如果缓存中没有分析结果，则执行分析
                if "analysis_result" not in st.session_state:
                    history, analysis = agent.analyze_trends(user_id)
                    st.session_state.history_data = history
                    st.session_state.analysis_result = analysis
                else:
                    history = st.session_state.history_data
                    analysis = st.session_state.analysis_result

                if history:
                    # 绘制趋势图
                    dates = [h['date'] for h in history]
                    all_keys = set()
                    for h in history:
                        all_keys.update(h['indicators'].keys())

                    for key in all_keys:
                        vals = []
                        for h in history:
                            val = h['indicators'].get(key, None)
                            try:
                                vals.append(float(val))
                            except (ValueError, TypeError):
                                vals.append(None)
                        if any(v is not None for v in vals):
                            chart_data = pd.DataFrame({'日期': dates, key: vals})
                            st.line_chart(chart_data.set_index('日期'))
                    st.markdown(analysis)
                else:
                    st.info(analysis)