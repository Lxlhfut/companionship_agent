import streamlit as st
from dotenv import load_dotenv
import os
from utils.db import get_user_subscription, init_db
from agents.chat_agent import ChatAgent
from agents.report_agent import ReportAgent
from agents.place_agent import PlaceAgent
from agents.reminder_agent import ReminderAgent

# 本地开发：从 .env 加载
load_dotenv()

# 云端部署：优先从 st.secrets 读取，覆盖环境变量
if "DPAPI_KEY" in st.secrets:
    os.environ["DPAPI_KEY"] = st.secrets["DPAPI_KEY"]
if "AMAP_API_KEY" in st.secrets:
    os.environ["AMAP_API_KEY"] = st.secrets["AMAP_API_KEY"]

# 初始化数据库
init_db()

# 页面配置
st.set_page_config(page_title="银龄陪伴", page_icon="👴", layout="wide")

# 会话状态初始化
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "chat_agent" not in st.session_state:
    st.session_state.chat_agent = ChatAgent()
if "report_agent" not in st.session_state:
    st.session_state.report_agent = ReportAgent()
if "place_agent" not in st.session_state:
    st.session_state.place_agent = PlaceAgent()
if "reminder_agent" not in st.session_state:
    st.session_state.reminder_agent = ReminderAgent()
# 新增：页面间跳转控制
if "nav_page" not in st.session_state:
    st.session_state.nav_page = None

# 登录后设置订阅状态
if st.session_state.user_id:
    sub_type, expiry = get_user_subscription(st.session_state.user_id)
    st.session_state.user_subscription = sub_type
    st.session_state.subscription_expiry = expiry
else:
    st.session_state.user_subscription = 'free'
    st.session_state.subscription_expiry = None

# 侧边栏导航
with st.sidebar:
    st.title("👴 银龄陪伴")
    if st.session_state.user_id:
        st.success(f"欢迎, {st.session_state.user_name}")

        # 如果正在进行页面跳转（nav_page 有值），则显示提示和返回按钮
        if st.session_state.nav_page:
            st.info(f"📌 当前页面：{st.session_state.nav_page}")
            if st.button("返回首页"):
                st.session_state.nav_page = None
                st.rerun()
            page = st.session_state.nav_page   # 直接使用跳转目标页面
        else:
            # 基础导航项
            nav_options = [
                "🏠 首页",
                "💬 陪伴聊天",
                "💊 今日用药提醒",
                # "📋 体检报告",
                "🌳 周边好去处",
                "👨‍👩‍👧 家人绑定"
            ]
            # 高级会员专属功能
            if st.session_state.get('user_subscription') == 'premium':
                nav_options.extend([
                    "🔬 深度体检报告",
                    "📋 慢病管理计划",
                    "⚠️ 异常预警设置",
                    "💬 家人AI分身"
                ])
            else:
                nav_options.append(["🌟 升级会员", "📋 体检报告"])

            page = st.radio("导航", nav_options, key="nav_radio")

        if st.button("退出登录"):
            # 退出时清除所有用户状态
            for key in ["user_id", "user_name", "user_subscription", "subscription_expiry",
                        "chat_memory", "chat_history", "nav_page"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        page = "🔐 登录/注册"

# 路由分发
# 注意：page 可能来自 radio 或 nav_page，确保覆盖所有可能值
if page == "🔐 登录/注册":
    import page_modules.login as login_page
    login_page.show()
elif page == "🏠 首页":
    import page_modules.home as home_page
    home_page.show()
elif page == "💬 陪伴聊天":
    import page_modules.chat as chat_page
    chat_page.show()
elif page == "💊 今日用药提醒":
    import page_modules.reminder as reminder_page
    reminder_page.show()
elif page == "📋 体检报告":
    import page_modules.report as report_page
    report_page.show()
elif page == "🌳 周边好去处":
    import page_modules.places as places_page
    places_page.show()
elif page == "👨‍👩‍👧 家人绑定":
    import page_modules.family as family_page
    family_page.show()
elif page == "🌟 升级会员":
    import page_modules.upgrade as upgrade_page
    upgrade_page.show()
elif page == "🔬 深度体检报告":
    import page_modules.advanced_report as adv_report
    adv_report.show()
elif page == "📋 慢病管理计划":
    import page_modules.chronic_plan as chronic_plan
    chronic_plan.show()
elif page == "⚠️ 异常预警设置":
    import page_modules.alerts as alerts
    alerts.show()
elif page == "💬 家人AI分身":
    import page_modules.avatar_chat as avatar_chat
    avatar_chat.show()
elif page == "🤖 创建分身":
    import page_modules.create_avatar as create_avatar
    create_avatar.show()
elif page == "✏️ 编辑分身":
    import page_modules.edit_avatar as edit_avatar
    edit_avatar.show()

# 页面路由执行完毕后，如果 nav_page 仍未被清除，则重置（避免影响下一次交互）
# 但注意：不要在页面内部 rerun 之前清除，否则会造成死循环
# 这里仅在页面未触发 rerun 时生效
if st.session_state.nav_page and page == st.session_state.nav_page and page != "🏠 首页":
    pass  # 保留，待页面内部自行清除
else:
    st.session_state.nav_page = None