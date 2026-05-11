import streamlit as st
from utils.auth import check_premium
def show():
    st.title("📋 体检报告解读")
    # st.markdown("上传体检报告 PDF 文件，AI 帮您解读重点指标（仅供参考）")

    # uploaded_file = st.file_uploader("选择 PDF 文件", type="pdf")
    user_id = st.session_state.user_id

    # 检查权限
    if not check_premium(user_id):
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
