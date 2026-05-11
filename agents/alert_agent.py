from datetime import datetime, timedelta
from utils.db import get_alert_rules
import os

class AlertAgent:
    def check_inactivity(self, user_id, last_activity_time):
        rules = get_alert_rules(user_id)
        if not rules:   # 空列表或无规则
            return False, None
        for rule in rules:
            if rule[2] == 'inactivity':
                try:
                    hours = int(rule[3]) if rule[3].isdigit() else 24
                except:
                    hours = 24
                if datetime.now() - last_activity_time > timedelta(hours=hours):
                    return True, f"老人已超过{hours}小时无活动迹象"
        return False, None

    def send_notification(self, family_members, message):
        # 后续可接入真实通知
        for member in family_members:
            print(f"[通知] 发送给 {member[1]}: {message}")
        return True