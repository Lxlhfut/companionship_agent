import streamlit as st

def show():
    st.title("📋 体检报告解读")
    # st.markdown("上传体检报告 PDF 文件，AI 帮您解读重点指标（仅供参考）")

    user_id = st.session_state.user_id

    # ---------- 从 session_state 获取订阅信息（避免数据库查询）----------
    # 如果订阅状态未加载，尝试从缓存中读取（app.py 中已保证登录后加载）
    subscription = st.session_state.get("user_subscription", "free")
    if subscription is None:
        subscription = "free"

    is_premium = (subscription == "premium")

    # 检查权限（使用缓存状态，不再调用 check_premium）
    if not is_premium:
        st.warning("🔒 深度解读为高级会员功能，免费版仅提供基础摘要")
        # 只允许基础文本提取
        uploaded_file = st.file_uploader("上传体检报告 PDF（基础解析）", type="pdf")
        if uploaded_file:
            text = st.session_state.report_agent.extract_text_from_pdf(uploaded_file)
            st.text_area("报告原文", text[:500] + "..." if len(text) > 500 else text)
            with st.spinner("正在解析报告..."):
                text = st.session_state.report_agent.extract_text_from_pdf(uploaded_file)
            if text:
                st.success("解析成功！")
                with st.expander("查看原文"):
                    st.text(text[:500] + "..." if len(text) > 500 else text)

                if st.button("开始解读"):
                    with st.spinner("AI 分析中..."):
                        interpretation = st.session_state.report_agent.interpret(text)
                        st.markdown("### 📊 解读结果")
                        st.write(interpretation)
            else:
                st.error("无法提取文字，请确保 PDF 为文本格式而非扫描图片")
            st.info("升级会员解锁深度解读、趋势分析和风险预测")
        return

    # ---------- 高级会员的完整报告解读功能 ----------
    # （原代码中未提供，实际此页面只是基础版，高级版在 advanced_report.py）
    # 若你想在此处增加高级功能，可继续补充。
    st.info("您已是高级会员，请前往「深度体检报告」页面获取完整解读服务。")
    # 也可直接在此处提供高级解读，但为避免重复，保持跳转逻辑。
    if st.button("前往深度体检报告"):
        st.session_state.nav_page = "🔬 深度体检报告"
        st.rerun()