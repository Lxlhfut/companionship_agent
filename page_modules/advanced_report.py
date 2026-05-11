import streamlit as st
import pandas as pd
import json
from utils.auth import check_premium
from agents.enhanced_report_agent import EnhancedReportAgent
from utils.db import save_health_report

def show():
    st.title("🔬 深度体检报告分析")
    user_id = st.session_state.user_id
    if not check_premium(user_id):
        st.warning("此功能为高级会员专属，请先升级")
        if st.button("前往升级"):
            st.session_state.nav_page = "🌟 升级会员"
            st.rerun()
        return

    agent = EnhancedReportAgent()
    tab1, tab2 = st.tabs(["上传新报告", "历史趋势分析"])

    with tab1:
        uploaded = st.file_uploader("上传体检报告 PDF", type="pdf")
        if uploaded:
            with st.spinner("解析中..."):
                # 复用原有的报告解析器提取文本
                from agents.report_agent import ReportAgent
                basic_agent = ReportAgent()
                text = basic_agent.extract_text_from_pdf(uploaded)
                if not text:
                    st.error("无法提取文本，请确保PDF为文本格式")
                    return
                indicators = agent.extract_indicators(text)
                st.success("指标提取成功")
                st.json(indicators)
                save_health_report(user_id, text, json.dumps(indicators, ensure_ascii=False))
                st.rerun()

    with tab2:
        st.subheader("历史指标趋势与风险分析")
        if st.button("开始分析"):
            with st.spinner("AI分析中..."):
                history, analysis = agent.analyze_trends(user_id)
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
                            # 尝试转换为数值
                            try:
                                vals.append(float(val))
                            except:
                                vals.append(None)
                        if any(v is not None for v in vals):
                            chart_data = pd.DataFrame({'日期': dates, key: vals})
                            st.line_chart(chart_data.set_index('日期'))
                    st.markdown(analysis)
                else:
                    st.info(analysis)