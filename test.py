import sqlite3
import pymysql
from dotenv import load_dotenv
load_dotenv()
from utils.db import get_db_connection  # 假设该函数使用 @st.cache_resource 缓存

SQLITE_DB_PATH = "data/users1.db"

TABLES_MAPPING = {
    "users": ["id", "username", "password_hash", "name", "age", "phone", "created_at", "subscription", "subscription_expiry"],
    "family_bindings": ["id", "elder_id", "family_id", "relationship", "created_at"],
    "reminders": ["id", "user_id", "medicine_name", "dosage", "time_of_day", "days_of_week", "active", "created_at"],
    "health_reports": ["id", "user_id", "upload_date", "report_text", "extracted_indicators"],
    "chronic_disease_profiles": ["id", "user_id", "disease_type", "diagnosis_date", "weight", "height",
                                 "blood_sugar_target", "blood_pressure_target", "daily_medications", "activity_level"],
    "alert_rules": ["id", "user_id", "rule_type", "threshold", "notification_method", "enabled"],
    "family_avatars": ["id", "user_id", "family_id", "avatar_name", "personality", "speech_samples", "voice_model_path", "created_at"],
    "management_plans": ["id", "user_id", "plan_text", "created_at", "updated_at"]
}

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_DB_PATH)

def normalize_datetime(dt_str):
    """将 SQLite 中的日期字符串转换为 MySQL 可接受的格式（去掉微秒）"""
    if dt_str and isinstance(dt_str, str):
        if '.' in dt_str:
            dt_str = dt_str.split('.')[0]
        return dt_str
    return dt_str

def migrate_all():
    # 1. 获取一个持久的 TiDB 连接（不要重复获取和关闭）
    tidb_conn = get_db_connection()
    tidb_cursor = tidb_conn.cursor()

    # 2. 临时禁用外键检查，避免顺序依赖
    tidb_cursor.execute("SET FOREIGN_KEY_CHECKS=0")

    # 3. 连接 SQLite
    sqlite_conn = get_sqlite_connection()
    sqlite_cursor = sqlite_conn.cursor()

    try:
        for table_name, columns in TABLES_MAPPING.items():
            print(f"正在迁移表: {table_name}...")

            # 读取 SQLite 数据
            sqlite_cursor.execute(f"SELECT {','.join(columns)} FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            if not rows:
                print(f"表 {table_name} 无数据，跳过")
                continue

            placeholders = ','.join(['%s'] * len(columns))
            insert_sql = f"INSERT IGNORE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

            inserted = 0
            failed = 0
            for row in rows:
                # 处理日期字段（转为字符串并去掉微秒）
                row = list(row)
                for i, val in enumerate(row):
                    if val and isinstance(val, str) and ('-' in val or ':' in val):
                        row[i] = normalize_datetime(val)

                try:
                    tidb_cursor.execute(insert_sql, row)
                    tidb_conn.commit()
                    inserted += 1
                except pymysql.Error as e:
                    print(f"  插入失败: {row} -> 错误 {e.args[0]}: {e.args[1]}")
                    tidb_conn.rollback()
                    failed += 1
                except Exception as e:
                    print(f"  未知错误: {row} -> {e}")
                    tidb_conn.rollback()
                    failed += 1

            print(f"表 {table_name} 完成，成功插入 {inserted} 条，失败 {failed} 条")
    finally:
        # 恢复外键检查
        tidb_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        tidb_conn.commit()
        # 不要关闭 tidb_conn，因为它是全局缓存的，关闭会导致后续在 app 中出错
        # 只关闭游标和 SQLite 连接
        tidb_cursor.close()
        sqlite_conn.close()

    print("所有数据迁移完成！")

if __name__ == "__main__":
    migrate_all()