import streamlit as st
from utils.db import create_family_avatar, get_user_by_id
from utils.auth import check_premium

def show():
    st.title("🤖 创建家人AI分身")

    if not check_premium(st.session_state.user_id):
        st.error("🔒 创建AI分身是高级会员功能，请先升级会员。")
        if st.button("前往升级"):
            st.session_state.nav_page = "🌟 升级会员"
            st.rerun()
        st.stop()

    elder_id = st.session_state.get("target_elder_id")
    family_id = st.session_state.get("target_family_id")
    if not elder_id or not family_id:
        st.error("缺少必要参数，请从家人绑定页面进入。")
        st.stop()

    elder = get_user_by_id(elder_id)
    family = get_user_by_id(family_id)
    if not elder or not family:
        st.error("用户信息错误")
        st.stop()

    st.markdown(f"为老人 **{elder[2]}** 创建家人 **{family[2]}** 的AI分身")


    with st.form("avatar_form"):
        avatar_name = st.text_input("分身显示名称", value=family[2])
        personality = st.text_area(
            "性格描述",
            placeholder="例如：他是一个幽默风趣、爱讲故事的人，说话时常带着微笑，喜欢用反问句。"
        )
        speech_samples = st.text_area(
            "说话样本（可选）",
            placeholder="提供几句家人常说的话，帮助AI模仿口吻。例如：\n- “闺女，今天吃啥好吃的了？”\n- “别老熬夜，身体要紧。”"
        )

        submitted = st.form_submit_button("创建分身")

        if submitted:
            # 在 submitted 分支内，最开头临时加：
            st.write("Debug: 表单已提交")
            st.write(f"elder_id={elder_id}, family_id={family_id}")
            st.write(f"avatar_name={avatar_name}, personality={personality[:20]}…")
            if not personality:
                st.error("请至少填写性格描述")
            else:
                # 调试：打印将要插入的数据
                st.write(f"准备插入：user_id={elder_id}, family_id={family_id}, name={avatar_name}, personality={personality[:20]}...")
                try:
                    result = create_family_avatar(elder_id, family_id, avatar_name, personality, speech_samples)
                    st.success(f"数据库返回结果：{result}")
                    st.success(f"分身「{avatar_name}」创建成功！")
                    # 清除临时状态并跳转
                    if "target_elder_id" in st.session_state:
                        del st.session_state.target_elder_id
                    if "target_family_id" in st.session_state:
                        del st.session_state.target_family_id
                    st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败：{e}")
                    # 打印完整异常信息（部署日志中也能看到）
                    import traceback
                    st.code(traceback.format_exc())

    if st.button("取消"):
        del st.session_state.target_elder_id
        del st.session_state.target_family_id
        st.session_state.nav_page = "👨‍👩‍👧 家人绑定"
        st.rerun()