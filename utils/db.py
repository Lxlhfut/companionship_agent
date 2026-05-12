import os
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import datetime, timedelta

# ---------- 数据库配置 ----------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL in environment secrets")


def get_db_connection():
    """返回一个 PostgreSQL 连接对象"""
    return psycopg2.connect(DATABASE_URL)


def execute_sql(sql, params=None, fetch_one=False, fetch_all=False, commit=True):
    """通用执行 SQL，自动管理连接和游标"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        if commit:
            conn.commit()
        if fetch_one:
            row = cur.fetchone()
            return row
        if fetch_all:
            rows = cur.fetchall()
            return rows
        return None
    finally:
        cur.close()
        conn.close()


def alter_table_add_column_if_not_exists(table, column, col_type):
    """PostgreSQL 中安全添加列（若不存在）"""
    # 检查列是否存在
    sql_check = """
        SELECT column_name FROM information_schema.columns 
        WHERE table_name=%s AND column_name=%s
    """
    exists = execute_sql(sql_check, (table, column), fetch_one=True)
    if not exists:
        execute_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


# ---------- 初始化数据库（建表） ----------
def init_db():
    """创建所有需要的表（幂等）"""
    # 用户表（包含订阅字段）
    execute_sql("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            phone TEXT,
            created_at TIMESTAMP,
            subscription TEXT DEFAULT 'free',
            subscription_expiry TIMESTAMP
        )
    """)

    # 家人绑定表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS family_bindings (
            id SERIAL PRIMARY KEY,
            elder_id INTEGER REFERENCES users(id),
            family_id INTEGER REFERENCES users(id),
            relationship TEXT,
            created_at TIMESTAMP
        )
    """)

    # 用药提醒表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            medicine_name TEXT NOT NULL,
            dosage TEXT,
            time_of_day TEXT NOT NULL,
            days_of_week TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP
        )
    """)

    # 体检报告记录表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS health_reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_text TEXT,
            extracted_indicators TEXT
        )
    """)

    # 慢病档案表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS chronic_disease_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE REFERENCES users(id),
            disease_type TEXT,
            diagnosis_date TEXT,
            weight REAL,
            height REAL,
            blood_sugar_target REAL,
            blood_pressure_target TEXT,
            daily_medications TEXT,
            activity_level TEXT
        )
    """)

    # 异常预警规则表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            rule_type TEXT,
            threshold TEXT,
            notification_method TEXT,
            enabled INTEGER DEFAULT 1
        )
    """)

    # 家人分身数据表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS family_avatars (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            family_id INTEGER REFERENCES users(id),
            avatar_name TEXT,
            personality TEXT,
            speech_samples TEXT,
            voice_model_path TEXT,
            created_at TIMESTAMP
        )
    """)

    # 健康管理计划表
    execute_sql("""
        CREATE TABLE IF NOT EXISTS management_plans (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            plan_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ---------- 用户订阅相关 ----------
def get_user_subscription(user_id):
    sql = "SELECT subscription, subscription_expiry FROM users WHERE id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    if row:
        sub_type, expiry = row[0], row[1]
        if sub_type == 'premium' and expiry:
            if expiry < datetime.now():
                update_subscription(user_id, 'free')
                return 'free', None
        return sub_type, expiry
    return 'free', None


def update_subscription(user_id, sub_type, days=30):
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if sub_type == 'premium' else None
    sql = "UPDATE users SET subscription = %s, subscription_expiry = %s WHERE id = %s"
    execute_sql(sql, (sub_type, expiry, user_id))


# ---------- 用户管理 ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password, name, age=None, phone=None):
    sql = """
        INSERT INTO users (username, password_hash, name, age, phone, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    try:
        row = execute_sql(sql, (username, hash_password(password), name, age, phone, datetime.now()), fetch_one=True)
        return row[0] if row else None
    except psycopg2.IntegrityError:
        return None


def authenticate_user(username, password):
    sql = "SELECT id, name FROM users WHERE username = %s AND password_hash = %s"
    row = execute_sql(sql, (username, hash_password(password)), fetch_one=True)
    return row if row else None


def get_user_by_id(user_id):
    sql = "SELECT id, username, name, age, phone FROM users WHERE id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    return row


# ---------- 家人绑定 ----------
def add_family_binding(elder_id, family_id, relationship):
    sql = "INSERT INTO family_bindings (elder_id, family_id, relationship, created_at) VALUES (%s, %s, %s, %s)"
    execute_sql(sql, (elder_id, family_id, relationship, datetime.now()))
    return True


def get_family_members(elder_id):
    sql = """
        SELECT u.id, u.name, fb.relationship
        FROM family_bindings fb
        JOIN users u ON fb.family_id = u.id
        WHERE fb.elder_id = %s
    """
    rows = execute_sql(sql, (elder_id,), fetch_all=True)
    return rows or []


def get_elders_for_family(family_id):
    sql = """
        SELECT u.id, u.name, fb.relationship
        FROM family_bindings fb
        JOIN users u ON fb.elder_id = u.id
        WHERE fb.family_id = %s
    """
    rows = execute_sql(sql, (family_id,), fetch_all=True)
    return rows or []


# ---------- 用药提醒 ----------
def add_reminder(user_id, medicine_name, dosage, time_of_day, days_of_week=""):
    sql = """
        INSERT INTO reminders (user_id, medicine_name, dosage, time_of_day, days_of_week, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute_sql(sql, (user_id, medicine_name, dosage, time_of_day, days_of_week, datetime.now()))
    return True


def get_reminders(user_id):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = %s AND active = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []


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
    return row


def check_duplicate_reminder(user_id, medicine_name, time_of_day, exclude_id=None):
    if exclude_id:
        sql = "SELECT id FROM reminders WHERE user_id=%s AND medicine_name=%s AND time_of_day=%s AND id != %s"
        params = (user_id, medicine_name, time_of_day, exclude_id)
    else:
        sql = "SELECT id FROM reminders WHERE user_id=%s AND medicine_name=%s AND time_of_day=%s"
        params = (user_id, medicine_name, time_of_day)
    row = execute_sql(sql, params, fetch_one=True)
    return row[0] if row else None


def get_reminders_at_time(user_id, time_str, weekday=None):
    sql = "SELECT id, medicine_name, dosage, time_of_day, days_of_week, active FROM reminders WHERE user_id = %s AND active = 1 AND time_of_day = %s"
    rows = execute_sql(sql, (user_id, time_str), fetch_all=True)
    if not rows:
        return []
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
    sql = "INSERT INTO health_reports (user_id, report_text, extracted_indicators) VALUES (%s, %s, %s)"
    execute_sql(sql, (user_id, report_text, indicators_json))


def get_user_reports(user_id):
    sql = "SELECT id, upload_date, extracted_indicators FROM health_reports WHERE user_id = %s ORDER BY upload_date ASC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []


# ---------- 慢病档案 ----------
def upsert_chronic_profile(user_id, disease_type, weight, height,
                           blood_sugar_target, blood_pressure_target,
                           daily_medications, activity_level):
    sql = """
        INSERT INTO chronic_disease_profiles
            (user_id, disease_type, weight, height, blood_sugar_target, blood_pressure_target, daily_medications, activity_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            disease_type = EXCLUDED.disease_type,
            weight = EXCLUDED.weight,
            height = EXCLUDED.height,
            blood_sugar_target = EXCLUDED.blood_sugar_target,
            blood_pressure_target = EXCLUDED.blood_pressure_target,
            daily_medications = EXCLUDED.daily_medications,
            activity_level = EXCLUDED.activity_level
    """
    execute_sql(sql, (user_id, disease_type, weight, height, blood_sugar_target,
                      blood_pressure_target, daily_medications, activity_level))


def get_chronic_profile(user_id):
    sql = "SELECT * FROM chronic_disease_profiles WHERE user_id = %s"
    row = execute_sql(sql, (user_id,), fetch_one=True)
    return row


# ---------- 预警规则 ----------
def add_alert_rule(user_id, rule_type, threshold, notification_method):
    sql = "INSERT INTO alert_rules (user_id, rule_type, threshold, notification_method) VALUES (%s, %s, %s, %s)"
    execute_sql(sql, (user_id, rule_type, threshold, notification_method))


def get_alert_rules(user_id):
    sql = "SELECT id, user_id, rule_type, threshold, notification_method, enabled FROM alert_rules WHERE user_id = %s AND enabled = 1"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []


# ---------- 家人分身 ----------
def create_family_avatar(user_id, family_id, avatar_name, personality, speech_samples):
    sql = "INSERT INTO family_avatars (user_id, family_id, avatar_name, personality, speech_samples) VALUES (%s, %s, %s, %s, %s)"
    execute_sql(sql, (user_id, family_id, avatar_name, personality, speech_samples))
    return True


def get_family_avatars_for_elder(user_id):
    sql = """
        SELECT fa.id, fa.avatar_name, u.name as family_name, fa.personality
        FROM family_avatars fa
        JOIN users u ON fa.family_id = u.id
        WHERE fa.user_id = %s
    """
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []


def get_avatar(avatar_id):
    sql = """
        SELECT fa.*, u.name as family_name
        FROM family_avatars fa
        JOIN users u ON fa.family_id = u.id
        WHERE fa.id = %s
    """
    row = execute_sql(sql, (avatar_id,), fetch_one=True)
    return row


def get_avatar_by_family_and_elder(family_id, elder_id):
    sql = "SELECT id, avatar_name, personality, speech_samples FROM family_avatars WHERE family_id = %s AND user_id = %s"
    row = execute_sql(sql, (family_id, elder_id), fetch_one=True)
    return row


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
    sql = "INSERT INTO management_plans (user_id, plan_text) VALUES (%s, %s) RETURNING id"
    row = execute_sql(sql, (user_id, plan_text), fetch_one=True)
    return row[0] if row else None


def get_user_plans(user_id):
    sql = "SELECT id, plan_text, created_at FROM management_plans WHERE user_id = %s ORDER BY created_at DESC"
    rows = execute_sql(sql, (user_id,), fetch_all=True)
    return rows or []


def get_plan_by_id(plan_id):
    sql = "SELECT id, user_id, plan_text FROM management_plans WHERE id = %s"
    row = execute_sql(sql, (plan_id,), fetch_one=True)
    return row


def update_plan_text(plan_id, new_text):
    sql = "UPDATE management_plans SET plan_text = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    execute_sql(sql, (new_text, plan_id))


def delete_plan(plan_id):
    sql = "DELETE FROM management_plans WHERE id = %s"
    execute_sql(sql, (plan_id,))