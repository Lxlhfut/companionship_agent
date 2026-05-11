import sqlite3
import hashlib
from datetime import datetime, timedelta
import time as time_module  # 避免与变量冲突
DB_PATH = "data/users.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  name TEXT NOT NULL,
                  age INTEGER,
                  phone TEXT,
                  created_at TIMESTAMP)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN subscription TEXT DEFAULT 'free'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN subscription_expiry TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    # 家人绑定表
    c.execute('''CREATE TABLE IF NOT EXISTS family_bindings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  elder_id INTEGER NOT NULL,
                  family_id INTEGER NOT NULL,
                  relationship TEXT,
                  created_at TIMESTAMP,
                  FOREIGN KEY(elder_id) REFERENCES users(id),
                  FOREIGN KEY(family_id) REFERENCES users(id))''')
    # 用药提醒表
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  medicine_name TEXT NOT NULL,
                  dosage TEXT,
                  time_of_day TEXT NOT NULL,
                  days_of_week TEXT,
                  active INTEGER DEFAULT 1,
                  created_at TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    # 体检报告记录表
    c.execute('''CREATE TABLE IF NOT EXISTS health_reports
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      report_text TEXT,
                      extracted_indicators TEXT,  -- JSON格式的指标字典
                      FOREIGN KEY(user_id) REFERENCES users(id))''')

    # 慢病档案表
    c.execute('''CREATE TABLE IF NOT EXISTS chronic_disease_profiles
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER UNIQUE NOT NULL,
                      disease_type TEXT,          -- 如 hypertension, diabetes
                      diagnosis_date TEXT,
                      weight REAL,
                      height REAL,
                      blood_sugar_target REAL,
                      blood_pressure_target TEXT,
                      daily_medications TEXT,     -- JSON
                      activity_level TEXT,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')

    # 异常预警规则表
    c.execute('''CREATE TABLE IF NOT EXISTS alert_rules
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      rule_type TEXT,             -- 如 inactivity, fall, device_offline
                      threshold TEXT,             -- 阈值设置
                      notification_method TEXT,   -- 如 sms, email, app
                      enabled INTEGER DEFAULT 1,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')

    # 家人分身数据表
    c.execute('''CREATE TABLE IF NOT EXISTS family_avatars
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,   -- 老人ID
                      family_id INTEGER NOT NULL, -- 家人ID
                      avatar_name TEXT,
                      personality TEXT,           -- 性格描述
                      speech_samples TEXT,        -- 语气样本
                      voice_model_path TEXT,      -- 可选语音模型
                      created_at TIMESTAMP,
                      FOREIGN KEY(user_id) REFERENCES users(id),
                      FOREIGN KEY(family_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS management_plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  plan_text TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

def get_user_subscription(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT subscription, subscription_expiry FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        # 检查是否过期
        if row[0] == 'premium' and row[1]:
            expiry = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
            if expiry < datetime.now():
                # 过期自动降级
                update_subscription(user_id, 'free')
                return 'free', None
        return row[0], row[1]
    return 'free', None

# 更新订阅状态
def update_subscription(user_id, sub_type, days=30):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if sub_type == 'premium' else None
    c.execute("UPDATE users SET subscription=?, subscription_expiry=? WHERE id=?",
              (sub_type, expiry, user_id))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password, name, age=None, phone=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, name, age, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (username, hash_password(password), name, age, phone, datetime.now()))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE username=? AND password_hash=?",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user if user else None


def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, name, age, phone FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user


# 家人绑定相关函数...
def add_family_binding(elder_id, family_id, relationship):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO family_bindings (elder_id, family_id, relationship, created_at) VALUES (?, ?, ?, ?)",
              (elder_id, family_id, relationship, datetime.now()))
    conn.commit()
    conn.close()
    return True


def get_family_members(elder_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT u.id, u.name, fb.relationship 
                 FROM family_bindings fb 
                 JOIN users u ON fb.family_id = u.id 
                 WHERE fb.elder_id=?''', (elder_id,))
    members = c.fetchall()
    conn.close()
    return members


def get_elders_for_family(family_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT u.id, u.name, fb.relationship 
                 FROM family_bindings fb 
                 JOIN users u ON fb.elder_id = u.id 
                 WHERE fb.family_id=?''', (family_id,))
    elders = c.fetchall()
    conn.close()
    return elders


# 提醒相关函数...
def add_reminder(user_id, medicine_name, dosage, time_of_day, days_of_week=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO reminders (user_id, medicine_name, dosage, time_of_day, days_of_week, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (user_id, medicine_name, dosage, time_of_day, days_of_week, datetime.now()))
    conn.commit()
    conn.close()
    return True


def get_reminders(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id=? AND active=1",
        (user_id,))
    reminders = c.fetchall()
    conn.close()
    return reminders


# 在原有基础上增加/修改以下函数

def update_reminder(reminder_id, medicine_name, dosage, time_of_day, days_of_week, active=1):
    """更新用药提醒"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE reminders 
                 SET medicine_name=?, dosage=?, time_of_day=?, days_of_week=?, active=?
                 WHERE id=?''',
              (medicine_name, dosage, time_of_day, days_of_week, active, reminder_id))
    conn.commit()
    conn.close()
    return True


def delete_reminder(reminder_id):
    """删除用药提醒"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()
    return True


def get_reminder_by_id(reminder_id):
    """获取单条提醒详情"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE id=?",
              (reminder_id,))
    r = c.fetchone()
    conn.close()
    return r


def check_duplicate_reminder(user_id, medicine_name, time_of_day, exclude_id=None):
    """检查是否存在重复提醒（同用户、同药品、同时段）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if exclude_id:
        c.execute('''SELECT id FROM reminders 
                     WHERE user_id=? AND medicine_name=? AND time_of_day=? AND id!=?''',
                  (user_id, medicine_name, time_of_day, exclude_id))
    else:
        c.execute('''SELECT id FROM reminders 
                     WHERE user_id=? AND medicine_name=? AND time_of_day=?''',
                  (user_id, medicine_name, time_of_day))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def get_reminders_at_time(user_id, time_str, weekday=None):
    """获取特定时间点的提醒（考虑每周重复）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 查询所有该用户激活的提醒
    c.execute('''SELECT id, medicine_name, dosage, time_of_day, days_of_week, active 
                 FROM reminders 
                 WHERE user_id=? AND active=1 AND time_of_day=?''',
              (user_id, time_str))
    all_reminders = c.fetchall()
    conn.close()

    # 过滤：如果设置了星期，需要匹配当前星期
    if weekday is None:
        import datetime
        weekday = datetime.datetime.now().weekday()  # 0=周一 ... 6=周日

    due = []
    for r in all_reminders:
        r_id, name, dosage, time_str_db, days_of_week, active = r
        if days_of_week:
            # days_of_week 存储为逗号分隔的数字字符串，如 "0,2,4"
            allowed_days = [int(d.strip()) for d in days_of_week.split(',') if d.strip()]
            if weekday not in allowed_days:
                continue
        due.append(r)
    return due

# 体检报告相关
def save_health_report(user_id, report_text, indicators_json):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO health_reports (user_id, report_text, extracted_indicators) VALUES (?,?,?)",
              (user_id, report_text, indicators_json))
    conn.commit()
    conn.close()

def get_user_reports(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, upload_date, extracted_indicators FROM health_reports WHERE user_id=? ORDER BY upload_date ASC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# 慢病档案
def upsert_chronic_profile(user_id, disease_type, weight, height,
                           blood_sugar_target, blood_pressure_target,
                           daily_medications, activity_level):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO chronic_disease_profiles
                 (user_id, disease_type, weight, height,
                  blood_sugar_target, blood_pressure_target,
                  daily_medications, activity_level)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (user_id, disease_type, weight, height,
               blood_sugar_target, blood_pressure_target,
               daily_medications, activity_level))
    conn.commit()
    conn.close()

def get_chronic_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM chronic_disease_profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# 预警规则
def add_alert_rule(user_id, rule_type, threshold, notification_method):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO alert_rules (user_id, rule_type, threshold, notification_method)
                 VALUES (?,?,?,?)''', (user_id, rule_type, threshold, notification_method))
    conn.commit()
    conn.close()

def get_alert_rules(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, rule_type, threshold, notification_method, enabled FROM alert_rules WHERE user_id=? AND enabled=1", (user_id,))
    rules = c.fetchall()
    conn.close()
    return rules if rules else []   # 确保返回列表

# 家人分身
# utils/db.py 底部

def create_family_avatar(user_id, family_id, avatar_name, personality, speech_samples):
    """为老人(user_id)创建一个家人(family_id)的AI分身"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO family_avatars 
                 (user_id, family_id, avatar_name, personality, speech_samples)
                 VALUES (?,?,?,?,?)''',
              (user_id, family_id, avatar_name, personality, speech_samples))
    conn.commit()
    conn.close()
    return True

def get_family_avatars_for_elder(user_id):
    """获取指定老人的所有分身列表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT fa.id, fa.avatar_name, u.name as family_name, fa.personality
                 FROM family_avatars fa
                 JOIN users u ON fa.family_id = u.id
                 WHERE fa.user_id=?''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_avatar(avatar_id):
    """获取单个分身的详细信息（用于聊天）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT fa.*, u.name as family_name
                 FROM family_avatars fa
                 JOIN users u ON fa.family_id = u.id
                 WHERE fa.id=?''', (avatar_id,))
    row = c.fetchone()
    conn.close()
    return row


def save_management_plan(user_id, plan_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO management_plans (user_id, plan_text) VALUES (?,?)",
              (user_id, plan_text))
    conn.commit()
    plan_id = c.lastrowid
    conn.close()
    return plan_id


def get_user_plans(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, plan_text, created_at FROM management_plans WHERE user_id=? ORDER BY created_at DESC",
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_plan_by_id(plan_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, plan_text FROM management_plans WHERE id=?", (plan_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_plan_text(plan_id, new_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE management_plans SET plan_text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
              (new_text, plan_id))
    conn.commit()
    conn.close()

def delete_plan(plan_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM management_plans WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()

def get_avatar_by_family_and_elder(family_id, elder_id):
    """查询指定家人为指定老人创建的分身，用于判断是否存在并获取 ID"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, avatar_name, personality, speech_samples FROM family_avatars WHERE family_id=? AND user_id=?",
              (family_id, elder_id))
    row = c.fetchone()
    conn.close()
    return row   # 返回 (id, avatar_name, personality, speech_samples) 或 None

def update_family_avatar(avatar_id, avatar_name, personality, speech_samples):
    """更新分身信息"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE family_avatars SET avatar_name=?, personality=?, speech_samples=? WHERE id=?",
              (avatar_name, personality, speech_samples, avatar_id))
    conn.commit()
    conn.close()
    return True

def delete_family_avatar(avatar_id):
    """删除分身"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM family_avatars WHERE id=?", (avatar_id,))
    conn.commit()
    conn.close()
    return True

