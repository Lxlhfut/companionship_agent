#!/usr/bin/env python3
"""测试 Turso 数据库连接"""

import os
import sys

# ========== 在这里直接填写你的 URL 和 Token（测试用）==========
# 注意：测试完成后务必删除硬编码，改用环境变量
TURSO_URL = "libsql://companionshipdb-lxlhfut.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3Nzg0ODU0OTAsImlkIjoiMDE5ZTE1ZjktNjkwMS03YzJiLTlmN2YtNzM0NmRhY2Q5YWQwIiwicmlkIjoiM2M3NTA4MGEtYThlYS00MDY1LTg2NTctMTMyMjA5YzY3NGYyIn0.BMXb3Gh9HdXiz_LWWZDtKtDXNwsviP9v2CmbEQzf_UefY1ACF5jYF15AZ81wIXC9YXDeicureVD9VDqKjepoDQ"
# ============================================================

def main():
    print("1. 尝试导入 libsql_client...")
    try:
        import libsql_client
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请先安装: pip install libsql-client")
        return

    print("2. 尝试创建客户端连接...")
    try:
        client = libsql_client.create_client_sync(
            url=TURSO_URL,
            auth_token=TURSO_TOKEN
        )
        print("✅ 客户端创建成功")
    except Exception as e:
        print(f"❌ 创建客户端失败: {e}")
        return

    print("3. 尝试执行简单查询（SELECT 1）...")
    try:
        with client:
            cursor = client.execute("SELECT 1")
            row = cursor.fetchone()
            print(f"✅ 查询成功，结果: {row}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return

    print("4. 尝试创建测试表并插入数据...")
    try:
        with client:
            client.execute("CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY, val TEXT)")
            client.execute("INSERT INTO _test (val) VALUES (?)", ("hello turso",))
            cursor = client.execute("SELECT val FROM _test")
            row = cursor.fetchone()
            print(f"✅ 写入读取成功: {row}")
            # 清理测试表
            client.execute("DROP TABLE _test")
    except Exception as e:
        print(f"❌ 表操作失败: {e}")
        return

    print("🎉 所有测试通过！你的 Turso 连接配置正确。")

if __name__ == "__main__":
    main()
