from dotenv import load_dotenv
load_dotenv()   # 加载 .env 文件中的环境变量

from utils.db import init_db, create_user

init_db()
user_id = create_user("testuser", "123456", "测试用户")
print(f"Created user id: {user_id}")