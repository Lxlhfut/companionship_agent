import os
import hashlib
from datetime import datetime, timedelta
import pymysql
from pymysql.cursors import DictCursor

# ---------- TiDB Cloud 配置 ----------
TIDB_HOST = os.environ.get("TIDB_HOST")
TIDB_PORT = int(os.environ.get("TIDB_PORT", 4000))
TIDB_USER = os.environ.get("TIDB_USER")
TIDB_PASSWORD = os.environ.get("TIDB_PASSWORD")
TIDB_DATABASE = os.environ.get("TIDB_DATABASE", "companionship_db")

if not all([TIDB_HOST, TIDB_USER, TIDB_PASSWORD]):
    raise ValueError("Missing TiDB Cloud configuration: TIDB_HOST, TIDB_USER, TIDB_PASSWORD must be set")

def get_db_connection():
    """返回一个 PyMySQL 连接对象（自动提交，使用字典游标）"""
    conn = pymysql.connect(
        host=TIDB_HOST,
        port=TIDB_PORT,
        user=TIDB_USER,
        password=TIDB_PASSWORD,
        database=TIDB_DATABASE,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True,
        ssl={'ssl': {'ca': None}}  # TiDB Cloud 要求 SSL
    )
    return conn

def execute_sql(sql, params=None, fetch_one=False, fetch_all=False, commit=True):
    """通用执行 SQL，可选返回单行或全部行"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if commit:
            conn.commit()
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        cursor.close()
        return result
    finally:
        conn.close()

# ---------- 初始化数据库（建表，幂等）----------
def init_db():
    """创建所有需要的表（如果不存在）"""
    # 用户表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            age INT,
            phone VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription VARCHAR(50) DEFAULT 'free',
            subscription_expiry TIMESTAMP NULL
        )
    """)
    # 家人绑定表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS family_bindings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            elder_id INT NOT NULL,
            family_id INT NOT NULL,
            relationship VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (elder_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (family_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 用药提醒表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            medicine_name VARCHAR(255) NOT NULL,
            dosage VARCHAR(100),
            time_of_day VARCHAR(50) NOT NULL,
            days_of_week VARCHAR(100),
            active INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 体检报告记录表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS health_reports (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_text TEXT,
            extracted_indicators TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 慢病档案表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS chronic_disease_profiles (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT UNIQUE NOT NULL,
            disease_type VARCHAR(255),
            diagnosis_date VARCHAR(50),
            weight DOUBLE,
            height DOUBLE,
            blood_sugar_target DOUBLE,
            blood_pressure_target VARCHAR(100),
            daily_medications TEXT,
            activity_level VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 异常预警规则表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            rule_type VARCHAR(100),
            threshold VARCHAR(255),
            notification_method VARCHAR(100),
            enabled INT DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 家人分身数据表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS family_avatars (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            family_id INT NOT NULL,
            avatar_name VARCHAR(255),
            personality TEXT,
            speech_samples TEXT,
            voice_model_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (family_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    # 健康管理计划表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS management_plans (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            plan_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

# ---------- 用户订阅相关 ----------
def get_user_subscription(user_id):
    sql = "SELECT subscription, subscription_expiry FROM users WHERE id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    if row:
        sub_type = row['subscription']
        expiry_str = row['subscription_expiry']
        if sub_type == 'premium' and expiry_str:
            if expiry_str < datetime.now():
                update_subscription(user_id, 'free')
                return 'free', None
        return sub_type, expiry_str
    return 'free', None

def update_subscription(user_id, sub_type, days=30):
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if sub_type == 'premium' else None
    sql = "UPDATE users SET subscription = %s, subscription_expiry = %s WHERE id = %s"
    execute_sql(sql, (sub_type, expiry, user_id))

# ---------- 用户管理 ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, name, age=None, phone=None):
    sql = """INSERT INTO users (username, password_hash, name, age, phone, created_at)
             VALUES (%s, %s, %s, %s, %s, %s)"""
    try:
        execute_sql(sql, (username, hash_password(password), name, age, phone, datetime.now()))
        last_id = execute_sql("SELECT LAST_INSERT_ID() as id", fetch_one=True)
        return last_id['id'] if last_id else None
    except Exception:
        return None

def authenticate_user(username, password):
    sql = "SELECT id, name FROM users WHERE username = %s AND password_hash = %s"
    row = execute_sql(sql, (username, hash_password(password)), fetch_one=True)
    return (row['id'], row['name']) if row else None

def get_user_by_id(user_id):
    sql = "SELECT id, username, name, age, phone FROM users WHERE id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    return (row['id'], row['username'], row['name'], row['age'], row['phone']) if row else None

# ---------- 家人绑定 ----------
def add_family_binding(elder_id, family_id, relationship):
    sql = "INSERT INTO family_bindings (elder_id, family_id, relationship, created_at) VALUES (%s, %s, %s, %s)"
    execute_sql(sql, (elder_id, family_id, relationship, datetime.now()))
    return True

def get_family_members(elder_id):
    sql = """SELECT u.id, u.name, fb.relationship
             FROM family_bindings fb
             JOIN users u ON fb.family_id = u.id
             WHERE fb.elder_id = %s"""
    rows = execute_sql(sql, (elder_id,), fetch_all=True)
    return [(row['id'], row['name'], row['relationship']) for row in rows] if rows else []

def get_elders_for_family(family_id):
    sql = """SELECT u.id, u.name, fb.relationship
             FROM family_bindings fb
             JOIN users u ON fb.elder_id = u.id
             WHERE fb.family_id = %s"""
    rows = execute_sql(sql, (family_id,), fetch_all=True)
    return [(row['id'], row['name'], row['relationship']) for row in rows] if rows else []

# ---------- 用药提醒 ----------
def add_reminder(user_id, medicine_name, dosage, time_of_day, days_of_week=""):
    sql = """INSERT INTO reminders (user_id, medicine_name, dosage, time_of_day, days_of_week, created_at)
             VALUES (%s, %s, %s, %s, %s, %s)"""
    execute_sql(sql, (user_id, medicine_name, dosage, time_of_day, days_of_week, datetime.now()))
    return True

def get_reminders(user_id):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = %s AND active = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return [(row['id'], row['medicine_name'], row['dosage'], row['time_of_day'], row['days_of_week'], row['active']) for row in rows] if rows else []

def update_reminder(reminder_id, medicine_name, dosage, time_of_day, days_of_week, active=1):
    sql = "UPDATE reminders SET medicine_name=%s, dosage=%s, time_of_day=%s, days_of_week=%s, active=%s WHERE id=%s"
    execute_sql(sql, (medicine_name, dosage, time_of_day, days_of_week, active, reminder_id))
    return True

def delete_reminder(reminder_id):
    sql = "DELETE FROM reminders WHERE id = %s"
    execute_sql(sql, (reminder_id,))
    return True

def get_reminder_by_id(reminder_id):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE id = %s"
    row = execute_sql(sql, (reminder_id,), fetch_one=True)
    return (row['id'], row['medicine_name'], row['dosage'], row['time_of_day'], row['days_of_week'], row['active']) if row else None

def check_duplicate_reminder(user_id, medicine_name, time_of_day, exclude_id=None):
    if exclude_id:
        sql = "SELECT id FROM reminders WHERE user_id=%s AND medicine_name=%s AND time_of_day=%s AND id != %s"
        params = (user_id, medicine_name, time_of_day, exclude_id)
    else:
        sql = "SELECT id FROM reminders WHERE user_id=%s AND medicine_name=%s AND time_of_day=%s"
        params = (user_id, medicine_name, time_of_day)
    row = execute_sql(sql, params, fetch_one=True)
    return row['id'] if row else None

def get_reminders_at_time(user_id, time_str, weekday=None):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = %s AND active = 1 AND time_of_day = %s"
    rows = execute_sql(sql, (user_id, time_str), fetch_all=True)
    if not rows:
        return []
    if weekday is None:
        weekday = datetime.now().weekday()
    due = []
    for r in rows:
        days_of_week = r['days_of_week']
        if days_of_week:
            allowed = [int(d.strip()) for d in days_of_week.split(',') if d.strip()]
            if weekday not in allowed:
                continue
        due.append((r['id'], r['medicine_name'], r['dosage'], r['time_of_day'], r['days_of_week'], r['active']))
    return due

# ---------- 体检报告 ----------
def save_health_report(user_id, report_text, indicators_json):
    sql = "INSERT INTO health_reports (user_id, report_text, extracted_indicators) VALUES (%s, %s, %s)"
    execute_sql(sql, (user_id, report_text, indicators_json))

def get_user_reports(user_id):
    sql = "SELECT id, upload_date, extracted_indicators FROM health_reports WHERE user_id = %s ORDER BY upload_date ASC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return [(row['id'], row['upload_date'], row['extracted_indicators']) for row in rows] if rows else []

# ---------- 慢病档案 ----------
def upsert_chronic_profile(user_id, disease_type, weight, height,
                           blood_sugar_target, blood_pressure_target,
                           daily_medications, activity_level):
    sql = """INSERT INTO chronic_disease_profiles
             (user_id, disease_type, weight, height, blood_sugar_target, blood_pressure_target, daily_medications, activity_level)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE
             disease_type=VALUES(disease_type), weight=VALUES(weight), height=VALUES(height),
             blood_sugar_target=VALUES(blood_sugar_target), blood_pressure_target=VALUES(blood_pressure_target),
             daily_medications=VALUES(daily_medications), activity_level=VALUES(activity_level)"""
    execute_sql(sql, (user_id, disease_type, weight, height, blood_sugar_target,
                      blood_pressure_target, daily_medications, activity_level))

def get_chronic_profile(user_id):
    sql = "SELECT * FROM chronic_disease_profiles WHERE user_id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    if row:
        return tuple(row.values())
    return None

# ---------- 预警规则 ----------
def add_alert_rule(user_id, rule_type, threshold, notification_method):
    sql = "INSERT INTO alert_rules (user_id, rule_type, threshold, notification_method) VALUES (%s, %s, %s, %s)"
    execute_sql(sql, (user_id, rule_type, threshold, notification_method))

def get_alert_rules(user_id):
    sql = "SELECT id, user_id, rule_type, threshold, notification_method, enabled FROM alert_rules WHERE user_id = %s AND enabled = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return [(row['id'], row['user_id'], row['rule_type'], row['threshold'], row['notification_method'], row['enabled']) for row in rows] if rows else []

# ---------- 家人分身 ----------
def create_family_avatar(user_id, family_id, avatar_name, personality, speech_samples):
    sql = "INSERT INTO family_avatars (user_id, family_id, avatar_name, personality, speech_samples) VALUES (%s, %s, %s, %s, %s)"
    execute_sql(sql, (user_id, family_id, avatar_name, personality, speech_samples))
    return True

def get_family_avatars_for_elder(user_id):
    sql = """SELECT fa.id, fa.avatar_name, u.name as family_name, fa.personality
             FROM family_avatars fa
             JOIN users u ON fa.family_id = u.id
             WHERE fa.user_id = %s"""
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return [(row['id'], row['avatar_name'], row['family_name'], row['personality']) for row in rows] if rows else []

def get_avatar(avatar_id):
    sql = """SELECT fa.*, u.name as family_name
             FROM family_avatars fa
             JOIN users u ON fa.family_id = u.id
             WHERE fa.id = %s"""
    row = execute_sql(sql, (avatar_id,), fetch_one=True)
    if row:
        return tuple(row.values())
    return None

def get_avatar_by_family_and_elder(family_id, elder_id):
    sql = "SELECT id, avatar_name, personality, speech_samples FROM family_avatars WHERE family_id = %s AND user_id = %s"
    row = execute_sql(sql, (family_id, elder_id), fetch_one=True)
    if row:
        return (row['id'], row['avatar_name'], row['personality'], row['speech_samples'])
    return None

def update_family_avatar(avatar_id, avatar_name, personality, speech_samples):
    sql = "UPDATE family_avatars SET avatar_name=%s, personality=%s, speech_samples=%s WHERE id=%s"
    execute_sql(sql, (avatar_name, personality, speech_samples, avatar_id))
    return True

def delete_family_avatar(avatar_id):
    sql = "DELETE FROM family_avatars WHERE id = %s"
    execute_sql(sql, (avatar_id,))
    return True

# ---------- 管理计划 ----------
def save_management_plan(user_id, plan_text):
    sql = "INSERT INTO management_plans (user_id, plan_text) VALUES (%s, %s)"
    execute_sql(sql, (user_id, plan_text))
    last_id = execute_sql("SELECT LAST_INSERT_ID() as id", fetch_one=True)
    return last_id['id'] if last_id else None

def get_user_plans(user_id):
    sql = "SELECT id, plan_text, created_at FROM management_plans WHERE user_id = %s ORDER BY created_at DESC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return [(row['id'], row['plan_text'], row['created_at']) for row in rows] if rows else []

def get_plan_by_id(plan_id):
    sql = "SELECT id, user_id, plan_text FROM management_plans WHERE id = %s"
    row = execute_sql(sql, (plan_id,), fetch_one=True)
    if row:
        return (row['id'], row['user_id'], row['plan_text'])
    return None

def update_plan_text(plan_id, new_text):
    sql = "UPDATE management_plans SET plan_text = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    execute_sql(sql, (new_text, plan_id))

def delete_plan(plan_id):
    sql = "DELETE FROM management_plans WHERE id = %s"
    execute_sql(sql, (plan_id,))