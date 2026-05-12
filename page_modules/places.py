import streamlit as st
import pandas as pd
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import os
import hashlib
import json


def show():
    st.title("🌳 周边养老好去处")
    st.markdown("输入城市和参照地点，选择或输入场所类型，AI帮您寻找并排序")

    # 初始化状态
    if "place_chat_history" not in st.session_state:
        st.session_state.place_chat_history = []
    if "current_place_type" not in st.session_state:
        st.session_state.current_place_type = "公园"
    if "current_city" not in st.session_state:
        st.session_state.current_city = ""
    if "ref_location_name" not in st.session_state:
        st.session_state.ref_location_name = ""
    if "ref_lon" not in st.session_state:
        st.session_state.ref_lon = None
    if "ref_lat" not in st.session_state:
        st.session_state.ref_lat = None
    if "pois" not in st.session_state:
        st.session_state.pois = []
    if "total_count" not in st.session_state:
        st.session_state.total_count = 0
    if "custom_keyword" not in st.session_state:
        st.session_state.custom_keyword = ""

    # 初始化缓存字典（用于存储地理编码、POI搜索结果、AI回答）
    if "geocode_cache" not in st.session_state:
        st.session_state.geocode_cache = {}
    if "poi_search_cache" not in st.session_state:
        st.session_state.poi_search_cache = {}
    if "ai_response_cache" not in st.session_state:
        st.session_state.ai_response_cache = {}

    # 场所类型选择（放在表单外，即时响应）
    place_type_options = ["公园", "医院", "景点", "养老院", "社区中心", "健身广场", "自定义"]
    default_index = place_type_options.index(
        st.session_state.current_place_type) if st.session_state.current_place_type in place_type_options else 0
    selected_type = st.selectbox(
        "📍 场所类型",
        place_type_options,
        index=default_index,
        key="place_type_selector"
    )

    # 当选择变化时更新状态
    if selected_type != st.session_state.current_place_type:
        st.session_state.current_place_type = selected_type
        if selected_type != "自定义":
            st.session_state.custom_keyword = ""
        st.rerun()

    # 搜索表单
    with st.form(key="place_search_form"):
        col1, col2 = st.columns(2)
        with col1:
            city = st.text_input("🏙️ 城市名称", value=st.session_state.current_city)
        with col2:
            ref_place = st.text_input("📍 参照地点（如：XX小区、XX广场等）",
                                      value=st.session_state.ref_location_name,
                                      placeholder="仅用于计算距离的起点")

        # 根据当前类型决定是否显示自定义关键词输入框
        if st.session_state.current_place_type == "自定义":
            custom_keyword = st.text_input("✏️ 输入自定义关键词",
                                           value=st.session_state.custom_keyword,
                                           placeholder="例如：超市、药店、银行等")
        else:
            custom_keyword = ""

        search_btn = st.form_submit_button("🔍 搜索周边")

    if search_btn:
        # 准备搜索关键词
        if st.session_state.current_place_type == "自定义":
            if not custom_keyword.strip():
                st.error("请输入自定义关键词")
                return
            keyword = custom_keyword
            type_for_agent = None
            st.session_state.custom_keyword = custom_keyword
        else:
            keyword = st.session_state.current_place_type
            type_for_agent = st.session_state.current_place_type
            st.session_state.custom_keyword = ""

        st.session_state.current_city = city
        st.session_state.ref_location_name = ref_place

        # 地理编码参照地点（使用缓存）
        ref_lon, ref_lat = None, None
        if ref_place.strip():
            cache_key = f"geocode_{city}_{ref_place}"
            if cache_key in st.session_state.geocode_cache:
                ref_lon, ref_lat = st.session_state.geocode_cache[cache_key]
                if ref_lon is not None:
                    st.success(f"已定位参照点：{ref_place}")
                else:
                    st.warning("无法解析参照地点，将使用城市中心作为参照。")
            else:
                with st.spinner("正在解析参照地点坐标..."):
                    lon, lat = st.session_state.place_agent.geocode(ref_place, city)
                    if lon is not None:
                        ref_lon, ref_lat = lon, lat
                        st.session_state.geocode_cache[cache_key] = (lon, lat)
                        st.success(f"已定位参照点：{ref_place}")
                    else:
                        st.session_state.geocode_cache[cache_key] = (None, None)
                        st.warning("无法解析参照地点，将使用城市中心作为参照。")
        else:
            st.session_state.ref_lon = None
            st.session_state.ref_lat = None

        st.session_state.ref_lon = ref_lon
        st.session_state.ref_lat = ref_lat

        # 清空历史对话（搜索条件改变，旧对话无意义）
        st.session_state.place_chat_history = []

        # POI 搜索（使用缓存）
        # 生成缓存 key（包含城市、关键词、参照坐标、场所类型）
        cache_key = hashlib.md5(
            f"{city}_{keyword}_{ref_lon}_{ref_lat}_{type_for_agent}".encode()
        ).hexdigest()
        if cache_key in st.session_state.poi_search_cache:
            pois, total = st.session_state.poi_search_cache[cache_key]
            st.info("使用缓存结果，未重新搜索。")
        else:
            with st.spinner(f"正在搜索 {city} 的 {keyword} 并智能排序（最多200条）..."):
                pois, total = st.session_state.place_agent.search_places_sorted(
                    keywords=keyword,
                    city=city,
                    place_type=type_for_agent,
                    ref_lon=ref_lon,
                    ref_lat=ref_lat,
                    max_count=200
                )
                st.session_state.poi_search_cache[cache_key] = (pois, total)
        st.session_state.pois = pois
        st.session_state.total_count = total

    # 显示搜索结果（可折叠）
    if st.session_state.pois:
        with st.expander(f"📋 搜索结果（共 {st.session_state.total_count} 条）", expanded=True):
            df_data = []
            for p in st.session_state.pois:
                tel = p.get("tel")
                if isinstance(tel, list):
                    tel = ", ".join([str(t) for t in tel if t]) if tel else "暂无"
                elif tel is None or tel == "":
                    tel = "暂无"
                else:
                    tel = str(tel)
                if "calculated_distance" in p:
                    dist_str = f"{p['calculated_distance']}米"
                else:
                    dist = p.get("distance")
                    if dist:
                        try:
                            dist_str = f"{int(float(dist))}米"
                        except:
                            dist_str = "未知"
                    else:
                        dist_str = "未知"
                df_data.append({
                    "名称": _safe_str(p.get("name", "")),
                    "地址": _safe_str(p.get("address", "")),
                    "电话": tel,
                    "类型": _safe_str(p.get("type", "")),
                    "距离": dist_str
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)

            if st.session_state.total_count > 200:
                st.caption(f"注：仅显示前200条结果（共{st.session_state.total_count}条）")

    elif st.session_state.get("total_count") == 0 and st.session_state.get("current_city"):
        st.warning(f"未找到相关场所，您可以尝试其他关键词或城市。")

    # AI智能问询区域
    if st.session_state.get("current_place_type") or st.session_state.get("custom_keyword"):
        st.divider()
        display_type = st.session_state.current_place_type if st.session_state.current_place_type != "自定义" else st.session_state.custom_keyword
        st.subheader(f"🤖 AI {display_type}助手")
        st.markdown("关于这些场所，您有什么想进一步了解的吗？")

        place_type = st.session_state.current_place_type
        quick_questions = {
            "医院": ["哪个医院看心脏病比较好？", "怎么挂专家号？", "有老年病科吗？"],
            "公园": ["哪个公园适合散步？", "有没有无障碍通道？", "早上几点开门？"],
            "景点": ["有适合老人的景点吗？", "门票有优惠吗？", "交通方便吗？"],
            "养老院": ["哪家养老院服务好？", "收费标准如何？", "可以试住吗？"],
            "社区中心": ["有哪些老年活动？", "有棋牌室吗？", "需要预约吗？"],
            "健身广场": ["晚上有广场舞吗？", "有健身器材吗？", "地面防滑吗？"],
        }
        if place_type in quick_questions:
            qs = quick_questions[place_type]
        else:
            qs = ["推荐一个最近的", "人多吗？", "环境怎么样？"]

        cols = st.columns(len(qs))
        for i, q in enumerate(qs):
            with cols[i]:
                if st.button(q, key=f"quick_q_{i}", use_container_width=True):
                    st.session_state.place_question = q
                    st.rerun()

        # 对话历史
        for msg in st.session_state.place_chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_question = st.chat_input("输入您的问题...")
        if user_question or "place_question" in st.session_state:
            if not user_question and "place_question" in st.session_state:
                user_question = st.session_state.place_question
                del st.session_state.place_question

            st.session_state.place_chat_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.write(user_question)

            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    # AI 回答缓存
                    poi_hash = _get_poi_hash(st.session_state.pois)
                    cache_key = hashlib.md5(
                        f"{user_question}_{display_type}_{st.session_state.current_city}_{poi_hash}".encode()
                    ).hexdigest()
                    if cache_key in st.session_state.ai_response_cache:
                        response = st.session_state.ai_response_cache[cache_key]
                    else:
                        response = generate_place_response(
                            user_question,
                            display_type,
                            st.session_state.current_city,
                            st.session_state.pois
                        )
                        st.session_state.ai_response_cache[cache_key] = response
                    st.write(response)
                    st.session_state.place_chat_history.append({"role": "assistant", "content": response})


def generate_place_response(question, place_type, city, pois):
    poi_summary = ""
    if pois:
        poi_summary = f"在{city}找到以下{place_type}：\n"
        for i, p in enumerate(pois[:5]):
            name = _safe_str(p.get("name", ""))
            addr = _safe_str(p.get("address", ""))
            tel = p.get("tel", "无")
            if isinstance(tel, list):
                tel = ", ".join([str(t) for t in tel if t]) if tel else "无"
            poi_summary += f"{i + 1}. {name}，地址：{addr}，电话：{tel}\n"

    system_prompt = f"""你是一位熟悉{city}本地生活的养老顾问，专门为老年人推荐合适的{place_type}。
你有以下搜索结果作为参考：
{poi_summary}

请根据用户的问题，结合上述地点信息，提供贴心、实用、易理解的建议。如果用户询问挂号、科室等问题，请给出通用指导，并提醒最终需以医院官方信息为准。语气温暖、耐心，考虑老年人需求。"""

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DPAPI_KEY"),
        openai_api_base="https://dpapi.cn/v1",
        temperature=0.7
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=question)]
    resp = llm.invoke(messages)
    return resp.content


def _safe_str(value, default=""):
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if v]) if value else default
    return str(value) if value is not None else default


def _get_poi_hash(pois):
    """从 POI 列表生成一个简短的哈希字符串，用于 AI 回答的缓存 key"""
    if not pois:
        return ""
    # 只取前5个场所的名称和地址作为特征
    short_repr = []
    for p in pois[:5]:
        short_repr.append(f"{p.get('name', '')}|{p.get('address', '')}")
    return hashlib.md5("|".join(short_repr).encode()).hexdigest()