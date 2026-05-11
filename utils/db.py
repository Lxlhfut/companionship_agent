import os
import libsql_client
import hashlib
from datetime import datetime, timedelta

# ---------- 云数据库配置 ----------
TURSO_URL = os.environ.get("TURSO_URL")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN")

if not TURSO_URL or not TURSO_TOKEN:
    raise ValueError("Missing TURSO_URL or TURSO_TOKEN in environment secrets")

def get_db_connection():
    """返回一个 Turso 同步客户端"""
    return libsql_client.create_client_sync(
        url=TURSO_URL,
        auth_token=TURSO_TOKEN
    )

# ---------- 辅助函数：执行SQL并可选返回结果 ----------
def execute_sql(sql, parameters=None, fetch_one=False, fetch_all=False):
    """通用执行 SQL，可选返回结果"""
    with get_db_connection() as conn:
        if parameters:
            cursor = conn.execute(sql, parameters)
        else:
            cursor = conn.execute(sql)
        conn.commit()
        if fetch_one:
            row = cursor.fetchone()
            return row
        if fetch_all:
            rows = cursor.fetchall()
            return rows
        return None

# ---------- 初始化数据库（建表） ----------
def init_db():
    """创建所有需要的表（幂等）"""
    sqls = [
        # 用户表
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            phone TEXT,
            created_at TIMESTAMP
        )
        """,
        # 后续添加字段（订阅相关）
        "ALTER TABLE users ADD COLUMN subscription TEXT DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN subscription_expiry TIMESTAMP",
        # 家人绑定表
        """
        CREATE TABLE IF NOT EXISTS family_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER NOT NULL,
            family_id INTEGER NOT NULL,
            relationship TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(elder_id) REFERENCES users(id),
            FOREIGN KEY(family_id) REFERENCES users(id)
        )
        """,
        # 用药提醒表
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL,
            dosage TEXT,
            time_of_day TEXT NOT NULL,
            days_of_week TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        # 体检报告记录表
        """
        CREATE TABLE IF NOT EXISTS health_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_text TEXT,
            extracted_indicators TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        # 慢病档案表
        """
        CREATE TABLE IF NOT EXISTS chronic_disease_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            disease_type TEXT,
            diagnosis_date TEXT,
            weight REAL,
            height REAL,
            blood_sugar_target REAL,
            blood_pressure_target TEXT,
            daily_medications TEXT,
            activity_level TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        # 异常预警规则表
        """
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            rule_type TEXT,
            threshold TEXT,
            notification_method TEXT,
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        # 家人分身数据表
        """
        CREATE TABLE IF NOT EXISTS family_avatars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            family_id INTEGER NOT NULL,
            avatar_name TEXT,
            personality TEXT,
            speech_samples TEXT,
            voice_model_path TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(family_id) REFERENCES users(id)
        )
        """,
        # 健康管理计划表
        """
        CREATE TABLE IF NOT EXISTS management_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    ]

    with get_db_connection() as conn:
        # 执行建表语句
        for sql in sqls:
            try:
                conn.execute(sql)
            except Exception as e:
                # 如果是因为重复字段等错误，忽略（表结构已存在）
                if "duplicate column name" not in str(e).lower():
                    raise
        conn.commit()

    # 额外确保订阅字段确实存在（上面 ALTER 可能因已存在而失败，再手动检查）
    with get_db_connection() as conn:
        res = conn.execute("PRAGMA table_info(users)").fetchall()
        columns = [row[1] for row in res]
        if "subscription" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN subscription TEXT DEFAULT 'free'")
        if "subscription_expiry" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN subscription_expiry TIMESTAMP")
        conn.commit()

# ---------- 用户订阅相关 ----------
def get_user_subscription(user_id):
    sql = "SELECT subscription, subscription_expiry FROM users WHERE id = ?"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    if row:
        sub_type, expiry_str = row[0], row[1]
        if sub_type == 'premium' and expiry_str:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            if expiry < datetime.now():
                update_subscription(user_id, 'free')
                return 'free', None
        return sub_type, expiry_str
    return 'free', None

def update_subscription(user_id, sub_type, days=30):
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if sub_type == 'premium' else None
    sql = "UPDATE users SET subscription = ?, subscription_expiry = ? WHERE id = ?"
    execute_sql(sql, (sub_type, expiry, user_id))

# ---------- 用户管理 ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, name, age=None, phone=None):
    sql = """INSERT INTO users (username, password_hash, name, age, phone, created_at)
             VALUES (?, ?, ?, ?, ?, ?)"""
    try:
        execute_sql(sql, (username, hash_password(password), name, age, phone, datetime.now()))
        # 获取新插入的 id
        row = execute_sql("SELECT last_insert_rowid()", fetch_one=True)
        return row[0] if row else None
    except Exception:
        return None

def authenticate_user(username, password):
    sql = "SELECT id, name FROM users WHERE username = ? AND password_hash = ?"
    row = execute_sql(sql, (username, hash_password(password)), fetch_one=True)
    return row if row else None

def get_user_by_id(user_id):
    sql = "SELECT id, username, name, age, phone FROM users WHERE id = ?"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    return row

# ---------- 家人绑定 ----------
def add_family_binding(elder_id, family_id, relationship):
    sql = "INSERT INTO family_bindings (elder_id, family_id, relationship, created_at) VALUES (?, ?, ?, ?)"
    execute_sql(sql, (elder_id, family_id, relationship, datetime.now()))
    return True

def get_family_members(elder_id):
    sql = """SELECT u.id, u.name, fb.relationship
             FROM family_bindings fb
             JOIN users u ON fb.family_id = u.id
             WHERE fb.elder_id = ?"""
    rows = execute_sql(sql, (elder_id,), fetch_all=True)
    return rows or []

def get_elders_for_family(family_id):
    sql = """SELECT u.id, u.name, fb.relationship
             FROM family_bindings fb
             JOIN users u ON fb.elder_id = u.id
             WHERE fb.family_id = ?"""
    rows = execute_sql(sql, (family_id,), fetch_all=True)
    return rows or []

# ---------- 用药提醒 ----------
def add_reminder(user_id, medicine_name, dosage, time_of_day, days_of_week=""):
    sql = """INSERT INTO reminders (user_id, medicine_name, dosage, time_of_day, days_of_week, created_at)
             VALUES (?, ?, ?, ?, ?, ?)"""
    execute_sql(sql, (user_id, medicine_name, dosage, time_of_day, days_of_week, datetime.now()))
    return True

def get_reminders(user_id):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = ? AND active = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []

def update_reminder(reminder_id, medicine_name, dosage, time_of_day, days_of_week, active=1):
    sql = "UPDATE reminders SET medicine_name=?, dosage=?, time_of_day=?, days_of_week=?, active=? WHERE id=?"
    execute_sql(sql, (medicine_name, dosage, time_of_day, days_of_week, active, reminder_id))
    return True

def delete_reminder(reminder_id):
    sql = "DELETE FROM reminders WHERE id = ?"
    execute_sql(sql, (reminder_id,))
    return True

def get_reminder_by_id(reminder_id):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE id = ?"
    row = execute_sql(sql, (reminder_id,), fetch_one=True)
    return row

def check_duplicate_reminder(user_id, medicine_name, time_of_day, exclude_id=None):
    if exclude_id:
        sql = "SELECT id FROM reminders WHERE user_id=? AND medicine_name=? AND time_of_day=? AND id != ?"
        params = (user_id, medicine_name, time_of_day, exclude_id)
    else:
        sql = "SELECT id FROM reminders WHERE user_id=? AND medicine_name=? AND time_of_day=?"
        params = (user_id, medicine_name, time_of_day)
    row = execute_sql(sql, params, fetch_one=True)
    return row[0] if row else None

def get_reminders_at_time(user_id, time_str, weekday=None):
    # 先查所有符合时间的激活提醒
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = ? AND active = 1 AND time_of_day = ?"
    rows = execute_sql(sql, (user_id, time_str), fetch_all=True)
    if not rows:
        return []
    # 如果没给 weekday，取当前星期几（0=周一）
    if weekday is None:
        weekday = datetime.now().weekday()
    due = []
    for r in rows:
        r_id, name, dosage, t_str, days_week, active = r
        if days_week:
            allowed = [int(d.strip()) for d in days_week.split(',') if d.strip()]
            if weekday not in allowed:
                continue
        due.append(r)
    return due

# ---------- 体检报告 ----------
def save_health_report(user_id, report_text, indicators_json):
    sql = "INSERT INTO health_reports (user_id, report_text, extracted_indicators) VALUES (?, ?, ?)"
    execute_sql(sql, (user_id, report_text, indicators_json))

def get_user_reports(user_id):
    sql = "SELECT id, upload_date, extracted_indicators FROM health_reports WHERE user_id = ? ORDER BY upload_date ASC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []

# ---------- 慢病档案 ----------
def upsert_chronic_profile(user_id, disease_type, weight, height,
                           blood_sugar_target, blood_pressure_target,
                           daily_medications, activity_level):
    sql = """INSERT OR REPLACE INTO chronic_disease_profiles
             (user_id, disease_type, weight, height, blood_sugar_target, blood_pressure_target, daily_medications, activity_level)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
    execute_sql(sql, (user_id, disease_type, weight, height, blood_sugar_target,
                      blood_pressure_target, daily_medications, activity_level))

def get_chronic_profile(user_id):
    sql = "SELECT * FROM chronic_disease_profiles WHERE user_id = ?"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    return row

# ---------- 预警规则 ----------
def add_alert_rule(user_id, rule_type, threshold, notification_method):
    sql = "INSERT INTO alert_rules (user_id, rule_type, threshold, notification_method) VALUES (?, ?, ?, ?)"
    execute_sql(sql, (user_id, rule_type, threshold, notification_method))

def get_alert_rules(user_id):
    sql = "SELECT id, user_id, rule_type, threshold, notification_method, enabled FROM alert_rules WHERE user_id = ? AND enabled = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []

# ---------- 家人分身 ----------
def create_family_avatar(user_id, family_id, avatar_name, personality, speech_samples):
    sql = "INSERT INTO family_avatars (user_id, family_id, avatar_name, personality, speech_samples) VALUES (?, ?, ?, ?, ?)"
    execute_sql(sql, (user_id, family_id, avatar_name, personality, speech_samples))
    return True

def get_family_avatars_for_elder(user_id):
    sql = """SELECT fa.id, fa.avatar_name, u.name as family_name, fa.personality
             FROM family_avatars fa
             JOIN users u ON fa.family_id = u.id
             WHERE fa.user_id = ?"""
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []

def get_avatar(avatar_id):
    sql = """SELECT fa.*, u.name as family_name
             FROM family_avatars fa
             JOIN users u ON fa.family_id = u.id
             WHERE fa.id = ?"""
    row = execute_sql(sql, (avatar_id,), fetch_one=True)
    return row

def get_avatar_by_family_and_elder(family_id, elder_id):
    sql = "SELECT id, avatar_name, personality, speech_samples FROM family_avatars WHERE family_id = ? AND user_id = ?"
    row = execute_sql(sql, (family_id, elder_id), fetch_one=True)
    return row

def update_family_avatar(avatar_id, avatar_name, personality, speech_samples):
    sql = "UPDATE family_avatars SET avatar_name=?, personality=?, speech_samples=? WHERE id=?"
    execute_sql(sql, (avatar_name, personality, speech_samples, avatar_id))
    return True

def delete_family_avatar(avatar_id):
    sql = "DELETE FROM family_avatars WHERE id = ?"
    execute_sql(sql, (avatar_id,))
    return True

# ---------- 管理计划 ----------
def save_management_plan(user_id, plan_text):
    sql = "INSERT INTO management_plans (user_id, plan_text) VALUES (?, ?)"
    execute_sql(sql, (user_id, plan_text))
    row = execute_sql("SELECT last_insert_rowid()", fetch_one=True)
    return row[0] if row else None

def get_user_plans(user_id):
    sql = "SELECT id, plan_text, created_at FROM management_plans WHERE user_id = ? ORDER BY created_at DESC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []

def get_plan_by_id(plan_id):
    sql = "SELECT id, user_id, plan_text FROM management_plans WHERE id = ?"
    row = execute_sql(sql, (plan_id,), fetch_one=True)
    return row

def update_plan_text(plan_id, new_text):
    sql = "UPDATE management_plans SET plan_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    execute_sql(sql, (new_text, plan_id))

def delete_plan(plan_id):
    sql = "DELETE FROM management_plans WHERE id = ?"
    execute_sql(sql, (plan_id,))