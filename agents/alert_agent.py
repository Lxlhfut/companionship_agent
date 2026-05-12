from datetime import datetime, timedelta
from utils.db import get_alert_rules
import streamlit as st

class AlertAgent:
    def __init__(self):
        # 无需特别初始化
        pass

    def _get_rules_cached(self, user_id):
        """从缓存或数据库获取预警规则，避免重复查询"""
        cache_key = f"alert_rules_{user_id}"
        if cache_key not in st.session_state:
            rules = get_alert_rules(user_id)
            # 确保 rules 是列表（即使为空也存入缓存）
            st.session_state[cache_key] = rules if rules else []
        return st.session_state[cache_key]

    def check_inactivity(self, user_id, last_activity_time):
        """
        检查用户是否长时间未活动
        :param user_id: 用户ID
        :param last_activity_time: datetime 对象，表示最后一次活动时间
        :return: (是否触发警报, 警报消息)
        """
        rules = self._get_rules_cached(user_id)
        for rule in rules:
            # 适配字典格式（我们的 db.py 返回字典列表）
            if isinstance(rule, dict):
                rule_type = rule.get("rule_type")
                threshold = rule.get("threshold")
            else:  # 兼容旧元组格式，假设顺序为 (id, user_id, rule_type, threshold, notification_method, enabled)
                rule_type = rule[2] if len(rule) > 2 else None
                threshold = rule[3] if len(rule) > 3 else None

            if rule_type == 'inactivity':
                # 解析阈值（例如 "24" 表示24小时）
                try:
                    hours = int(threshold) if threshold and str(threshold).isdigit() else 24
                except:
                    hours = 24
                if datetime.now() - last_activity_time > timedelta(hours=hours):
                    return True, f"老人已超过{hours}小时无活动迹象"
        return False, None

    def send_notification(self, family_members, message):
        """
        发送通知给家人（可扩展真实通知渠道）
        :param family_members: 家人列表，每项应为 (id, name, ...)
        :param message: 消息内容
        """
        # 后续可接入真实通知（邮箱、短信、webhook等）
        for member in family_members:
            # member 可能是元组或字典，确保能获取姓名
            if isinstance(member, dict):
                name = member.get('name', '家人')
            else:
                name = member[1] if len(member) > 1 else '家人'
            print(f"[通知] 发送给 {name}: {message}")
        return True

    def refresh_rules_cache(self, user_id):
        """强制刷新预警规则缓存（在增加/删除规则后调用）"""
        cache_key = f"alert_rules_{user_id}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        # 重新加载
        self._get_rules_cached(user_id)