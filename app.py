import streamlit as st

# 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="银龄陪伴",
    page_icon="👴",
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a Bug': None,
        'About': None,
    }
)

# 使用 CSS 先隐藏基本元素
hide_css = """
<style>
/* 隐藏右下角 footer */
footer {display: none !important;}
/* 隐藏右上角菜单（三点）*/
#MainMenu {visibility: hidden !important; display: none !important;}
/* 隐藏整个顶栏（可选，会隐藏 "Manage app" 按钮，但没关系）*/
header {visibility: hidden !important; display: none !important;}
/* 针对可能动态生成的元素 */
.st-emotion-cache-1v0mbdj, .st-emotion-cache-1w3j6wz {
    display: none !important;
}
</style>
"""
st.markdown(hide_css, unsafe_allow_html=True)

# 使用 JavaScript 直接删除元素（100% 可靠）
hide_js = """
<script>
function removeStreamlitBranding() {
    // 删除 footer（右下角）
    const footer = document.querySelector('footer');
    if (footer) footer.remove();
    // 删除右上角菜单按钮
    const mainMenu = document.querySelector('#MainMenu');
    if (mainMenu) mainMenu.remove();
    // 删除可能存在的其他品牌容器
    const brandContainers = document.querySelectorAll('.st-emotion-cache-1v0mbdj, .st-emotion-cache-1w3j6wz');
    brandContainers.forEach(el => el.remove());
}
// 立即执行
removeStreamlitBranding();
// 监听 DOM 变化，防止动态添加
const observer = new MutationObserver(removeStreamlitBranding);
observer.observe(document.body, { childList: true, subtree: true });
</script>
"""
st.markdown(hide_js, unsafe_allow_html=True)

# 以下所有代码都放在 set_page_config 之后
from dotenv import load_dotenv
import os

load_dotenv()

from utils.db import get_user_subscription, init_db, get_user_by_id, get_reminders, get_family_members, \
    get_elders_for_family
from agents.chat_agent import ChatAgent
from agents.report_agent import ReportAgent
from agents.place_agent import PlaceAgent
from agents.reminder_agent import ReminderAgent

# 云端部署：优先从 st.secrets 读取
if "DPAPI_KEY" in st.secrets:
    os.environ["DPAPI_KEY"] = st.secrets["DPAPI_KEY"]
if "AMAP_API_KEY" in st.secrets:
    os.environ["AMAP_API_KEY"] = st.secrets["AMAP_API_KEY"]

# ---------- 初始化数据库（仅一次） ----------
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# ---------- 会话状态初始化 ----------
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
if "nav_page" not in st.session_state:
    st.session_state.nav_page = None

# 用户订阅信息缓存（避免每次侧边栏都查数据库）
if "user_subscription" not in st.session_state:
    st.session_state.user_subscription = 'free'
if "subscription_expiry" not in st.session_state:
    st.session_state.subscription_expiry = None
if "subscription_loaded" not in st.session_state:
    st.session_state.subscription_loaded = False

# 其它常用数据缓存标记（登录后一次性加载）
if "user_profile_loaded" not in st.session_state:
    st.session_state.user_profile_loaded = False

# ---------- 辅助缓存函数 ----------
def refresh_user_subscription():
    """从数据库加载订阅信息并缓存"""
    if st.session_state.user_id:
        sub_type, expiry = get_user_subscription(st.session_state.user_id)
        st.session_state.user_subscription = sub_type
        st.session_state.subscription_expiry = expiry
        st.session_state.subscription_loaded = True
    else:
        st.session_state.user_subscription = 'free'
        st.session_state.subscription_expiry = None
        st.session_state.subscription_loaded = False

def load_user_cache():
    """登录后只加载基本用户信息，其他数据在页面中懒加载"""
    if not st.session_state.user_id:
        return
    # 仅加载用户基本信息（不加载提醒、家人列表等）
    st.session_state.user_profile = get_user_by_id(st.session_state.user_id)
    # 设置缓存已加载标记
    st.session_state.user_profile_loaded = True
    # 注意：不再加载 reminders_cache, family_members_cache 等

# ---------- 侧边栏导航 ----------
with st.sidebar:
    st.title("👴 银龄陪伴")
    if st.session_state.user_id:
        # 仅在首次登录或用户信息变更时加载订阅信息
        if not st.session_state.subscription_loaded:
            refresh_user_subscription()
        # 仅在首次登录时加载其他缓存数据
        if not st.session_state.user_profile_loaded:
            load_user_cache()
        st.success(f"欢迎, {st.session_state.user_name}")

        # 页面跳转处理
        if st.session_state.nav_page:
            st.info(f"📌 当前页面：{st.session_state.nav_page}")
            if st.button("返回首页"):
                st.session_state.nav_page = None
                st.rerun()
            page = st.session_state.nav_page
        else:
            nav_options = [
                "🏠 首页",
                "💬 陪伴聊天",
                "💊 今日用药提醒",
                "🌳 周边好去处",
                "👨‍👩‍👧 家人绑定"
            ]
            # 高级会员专属功能
            if st.session_state.user_subscription == 'premium':
                nav_options.extend([
                    "🔬 深度体检报告",
                    "📋 慢病管理计划",
                    "⚠️ 异常预警设置",
                    "💬 家人AI分身"
                ])
            else:
                nav_options.append("📋 体检报告")
                nav_options.append("🌟 升级会员")

            page = st.radio("导航", nav_options, key="nav_radio")

        if st.button("退出登录"):
            # 清除所有用户相关状态
            keys_to_clear = [
                "user_id", "user_name", "user_subscription", "subscription_expiry",
                "subscription_loaded", "user_profile_loaded", "user_profile",
                "reminders_cache", "family_members_cache", "chat_memory",
                "chat_history", "nav_page","elders_cache"    # 新增
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    else:
        page = "🔐 登录/注册"

# ---------- 路由分发 ----------
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

# # 清理导航跳转标记
# if st.session_state.nav_page and page == st.session_state.nav_page:
#     st.session_state.nav_page = None
# 在路由分发之后
# 如果当前页面正是 nav_page 意图的页面（且不是首页），不清空
if st.session_state.nav_page and page == st.session_state.nav_page and page != "🏠 首页":
    pass  # 保留，待页面内部自行清除
else:
    st.session_state.nav_page = None