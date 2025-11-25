"""
数据库连接管理
"""
import pymysql
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings


class DatabaseConnection:
    """MySQL数据库连接管理器"""

    def __init__(self):
        """初始化数据库连接配置"""
        self.config = {
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "user": settings.MYSQL_USER,
            "password": settings.MYSQL_PASSWORD,
            "database": settings.MYSQL_DATABASE,
            "charset": settings.MYSQL_CHARSET,
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": False
        }

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.config)

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """
        获取数据库游标（上下文管理器）

        Args:
            commit: 是否自动提交事务

        Yields:
            数据库游标
        """
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
            if commit:
                connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
            connection.close()

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            查询结果列表
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新SQL（INSERT、UPDATE、DELETE）

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            影响的行数
        """
        with self.get_cursor(commit=True) as cursor:
            affected_rows = cursor.execute(sql, params)
            return affected_rows

    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            影响的行数
        """
        with self.get_cursor(commit=True) as cursor:
            affected_rows = cursor.executemany(sql, params_list)
            return affected_rows

    def get_last_insert_id(self, sql: str, params: tuple = None) -> int:
        """
        执行插入并返回最后插入的ID

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            最后插入的ID
        """
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid

    def init_database(self):
        """初始化数据库和表"""
        try:
            # 首先连接到MySQL服务器（不指定数据库）
            config_without_db = self.config.copy()
            config_without_db.pop("database")
            connection = pymysql.connect(**config_without_db)
            cursor = connection.cursor()

            # 创建数据库（如果不存在）
            cursor.execute(f"""
                CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            connection.commit()
            cursor.close()
            connection.close()

            # 创建表
            self._create_tables()

            # 创建默认管理员账号
            self._create_default_admin()

            print(f"✓ 数据库 {settings.MYSQL_DATABASE} 初始化完成")

        except Exception as e:
            print(f"✗ 数据库初始化失败: {str(e)}")
            raise

    def _create_tables(self):
        """创建所有表"""
        with self.get_cursor(commit=True) as cursor:
            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE COMMENT '用户邮箱（登录账号）',
                    password_hash VARCHAR(255) NOT NULL COMMENT '加密后的密码',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                    last_login_at TIMESTAMP NULL COMMENT '最后登录时间',
                    is_active TINYINT(1) DEFAULT 1 COMMENT '是否激活',
                    INDEX idx_email (email),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
            """)

            # 对话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL COMMENT '用户ID',
                    title VARCHAR(255) NOT NULL DEFAULT '新对话' COMMENT '对话标题',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                    is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_is_deleted (is_deleted)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话表';
            """)

            # 消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL COMMENT '对话ID',
                    role ENUM('user', 'assistant', 'system') NOT NULL COMMENT '消息角色',
                    content TEXT NOT NULL COMMENT '消息内容',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    INDEX idx_conversation_id (conversation_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';
            """)

            # 验证码表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS captcha_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code_key VARCHAR(64) NOT NULL UNIQUE COMMENT '验证码键',
                    code_value VARCHAR(10) NOT NULL COMMENT '验证码值',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
                    INDEX idx_code_key (code_key),
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验证码表';
            """)

    def _create_default_admin(self):
        """创建默认管理员账号"""
        from passlib.hash import bcrypt

        # 检查管理员是否已存在
        with self.get_cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", ("admin@tpl.cntaiping.com",))
            if cursor.fetchone():
                return  # 管理员已存在

        # 创建管理员账号
        password_hash = bcrypt.hash("123456")
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                ("admin@tpl.cntaiping.com", password_hash)
            )
            print("✓ 默认管理员账号已创建: admin@tpl.cntaiping.com / 123456")


# 创建全局数据库实例
db = DatabaseConnection()


def init_db():
    """初始化数据库"""
    db.init_database()


if __name__ == "__main__":
    # 测试数据库连接和初始化
    init_db()
