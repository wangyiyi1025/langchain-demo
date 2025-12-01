"""
数据库迁移脚本：将 messages 表的 content 字段从 TEXT 改为 MEDIUMTEXT

TEXT 类型最大 65,535 字节（约 65KB）
MEDIUMTEXT 类型最大 16,777,215 字节（约 16MB）

运行方式：
    python migrate_content_field.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db


def migrate_content_field():
    """将 messages 表的 content 字段从 TEXT 改为 MEDIUMTEXT"""
    print("开始迁移 messages 表的 content 字段...")

    try:
        with db.get_cursor(commit=True) as cursor:
            # 修改字段类型
            sql = """
                ALTER TABLE messages
                MODIFY COLUMN content MEDIUMTEXT NOT NULL COMMENT '消息内容'
            """
            cursor.execute(sql)
            print("✅ 迁移成功！content 字段已从 TEXT 改为 MEDIUMTEXT")

            # 验证修改
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'messages'
                AND COLUMN_NAME = 'content'
            """)
            result = cursor.fetchone()
            print(f"✅ 验证结果：{result}")

    except Exception as e:
        print(f"❌ 迁移失败：{str(e)}")
        raise


if __name__ == "__main__":
    migrate_content_field()
