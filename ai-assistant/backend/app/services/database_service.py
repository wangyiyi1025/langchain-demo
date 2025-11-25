"""
数据库元数据服务 - 提供数据库和表的元数据信息
"""
from typing import List, Dict, Optional
import pymysql
from pymysql.cursors import DictCursor


class DatabaseService:
    """数据库元数据服务"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9030,
        user: str = "admin",
        password: str = "123456"
    ):
        """
        初始化数据库服务
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 用户名
            password: 密码
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None

    def connect(self) -> bool:
        """
        连接数据库
        Returns:
            bool: 连接是否成功
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            return True
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_databases(self) -> List[str]:
        """
        获取所有数据库列表
        Returns:
            List[str]: 数据库名称列表
        """
        if not self.connection:
            if not self.connect():
                return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                results = cursor.fetchall()
                # 过滤掉系统数据库
                system_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', '_statistics_'}
                databases = [row['Database'] for row in results if row['Database'] not in system_dbs]
                return sorted(databases)
        except Exception as e:
            print(f"获取数据库列表失败: {str(e)}")
            return []

    def get_tables(self, database: str) -> List[str]:
        """
        获取指定数据库的所有表
        Args:
            database: 数据库名称
        Returns:
            List[str]: 表名称列表
        """
        if not self.connection:
            if not self.connect():
                return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW TABLES FROM `{database}`")
                results = cursor.fetchall()
                # 根据不同数据库的返回格式提取表名
                key = f'Tables_in_{database}'
                tables = [row[key] for row in results if key in row]
                return sorted(tables)
        except Exception as e:
            print(f"获取表列表失败: {str(e)}")
            return []

    def get_table_schema(self, database: str, table: str) -> List[Dict]:
        """
        获取表的Schema信息
        Args:
            database: 数据库名称
            table: 表名称
        Returns:
            List[Dict]: 字段信息列表
        """
        if not self.connection:
            if not self.connect():
                return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"DESC `{database}`.`{table}`")
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"获取表结构失败: {str(e)}")
            return []

    def get_tables_with_comments(self, database: str) -> List[Dict[str, str]]:
        """
        获取指定数据库的所有表及其注释
        Args:
            database: 数据库名称
        Returns:
            List[Dict]: [{"name": "table_name", "comment": "table_comment"}]
        """
        if not self.connection:
            if not self.connect():
                return []

        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT TABLE_NAME as name, TABLE_COMMENT as comment
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                """
                cursor.execute(query, (database,))
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"获取表注释失败: {str(e)}")
            return []

    def get_all_metadata(self) -> Dict[str, List[str]]:
        """
        获取所有数据库及其表的元数据
        Returns:
            Dict[str, List[str]]: {数据库名: [表名列表]}
        """
        metadata = {}
        databases = self.get_databases()

        for db in databases:
            tables = self.get_tables(db)
            if tables:  # 只包含有表的数据库
                metadata[db] = tables

        return metadata

    def get_all_metadata_with_comments(self) -> Dict[str, List[Dict[str, str]]]:
        """
        获取所有数据库及其表的元数据（包含注释）
        Returns:
            Dict[str, List[Dict]]: {数据库名: [{"name": "表名", "comment": "注释"}]}
        """
        metadata = {}
        databases = self.get_databases()

        for db in databases:
            tables = self.get_tables_with_comments(db)
            if tables:  # 只包含有表的数据库
                metadata[db] = tables

        return metadata

    def search_tables(self, keyword: str) -> List[Dict[str, str]]:
        """
        根据关键字搜索表
        Args:
            keyword: 搜索关键字
        Returns:
            List[Dict]: [{"database": "db_name", "table": "table_name"}]
        """
        results = []
        metadata = self.get_all_metadata()

        keyword_lower = keyword.lower()
        for database, tables in metadata.items():
            for table in tables:
                if keyword_lower in table.lower():
                    results.append({
                        "database": database,
                        "table": table,
                        "full_name": f"{database}.{table}"
                    })

        return results

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 全局数据库服务实例
_database_service_instance = None


def get_database_service() -> DatabaseService:
    """
    获取数据库服务实例（单例模式）
    Returns:
        DatabaseService: 数据库服务实例
    """
    global _database_service_instance
    if _database_service_instance is None:
        _database_service_instance = DatabaseService()
        _database_service_instance.connect()
    return _database_service_instance
