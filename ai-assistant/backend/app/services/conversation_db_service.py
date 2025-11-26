"""
对话持久化服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import db


class ConversationDBService:
    """对话数据库服务"""

    @staticmethod
    def create_conversation(user_id: int, title: str = "新对话") -> int:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题

        Returns:
            对话ID
        """
        sql = """
            INSERT INTO conversations (user_id, title)
            VALUES (%s, %s)
        """
        conversation_id = db.get_last_insert_id(sql, (user_id, title))
        return conversation_id

    @staticmethod
    def get_conversation(conversation_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取对话信息

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            对话信息
        """
        sql = """
            SELECT id, user_id, title, selected_table, created_at, updated_at
            FROM conversations
            WHERE id = %s AND user_id = %s AND is_deleted = 0
        """
        result = db.execute_query(sql, (conversation_id, user_id))
        if result:
            conversation = result[0]
            # 解析JSON字符串为字典
            if conversation.get('selected_table'):
                import json
                try:
                    conversation['selected_table'] = json.loads(conversation['selected_table'])
                except:
                    conversation['selected_table'] = None
            return conversation
        return None

    @staticmethod
    def list_conversations(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户的对话列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            对话列表
        """
        sql = """
            SELECT
                c.id,
                c.user_id,
                c.title,
                c.selected_table,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s AND c.is_deleted = 0
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        """
        result = db.execute_query(sql, (user_id, limit, offset))

        # 解析selected_table JSON字符串
        import json
        for conversation in result:
            if conversation.get('selected_table'):
                try:
                    conversation['selected_table'] = json.loads(conversation['selected_table'])
                except:
                    conversation['selected_table'] = None

        return result

    @staticmethod
    def count_conversations(user_id: int) -> int:
        """
        统计用户的对话数量

        Args:
            user_id: 用户ID

        Returns:
            对话数量
        """
        sql = """
            SELECT COUNT(*) as total
            FROM conversations
            WHERE user_id = %s AND is_deleted = 0
        """
        result = db.execute_query(sql, (user_id,))
        return result[0]['total'] if result else 0

    @staticmethod
    def update_conversation(conversation_id: int, user_id: int, title: str) -> bool:
        """
        更新对话标题

        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            title: 新标题

        Returns:
            是否更新成功
        """
        sql = """
            UPDATE conversations
            SET title = %s
            WHERE id = %s AND user_id = %s AND is_deleted = 0
        """
        affected_rows = db.execute_update(sql, (title, conversation_id, user_id))
        return affected_rows > 0

    @staticmethod
    def update_selected_table(conversation_id: int, user_id: int, selected_table: Optional[Dict[str, str]]) -> bool:
        """
        更新对话的选中表

        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            selected_table: 选中的表信息 {"database": "db_name", "table": "table_name", "comment": "注释"}

        Returns:
            是否更新成功
        """
        import json
        table_json = json.dumps(selected_table, ensure_ascii=False) if selected_table else None

        sql = """
            UPDATE conversations
            SET selected_table = %s
            WHERE id = %s AND user_id = %s AND is_deleted = 0
        """
        affected_rows = db.execute_update(sql, (table_json, conversation_id, user_id))
        return affected_rows > 0

    @staticmethod
    def delete_conversation(conversation_id: int, user_id: int) -> bool:
        """
        删除对话（软删除）

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        sql = """
            UPDATE conversations
            SET is_deleted = 1
            WHERE id = %s AND user_id = %s
        """
        affected_rows = db.execute_update(sql, (conversation_id, user_id))
        return affected_rows > 0

    @staticmethod
    def add_message(conversation_id: int, role: str, content: str) -> int:
        """
        添加消息到对话

        Args:
            conversation_id: 对话ID
            role: 消息角色 (user, assistant, system)
            content: 消息内容

        Returns:
            消息ID
        """
        sql = """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (%s, %s, %s)
        """
        message_id = db.get_last_insert_id(sql, (conversation_id, role, content))

        # 更新对话的更新时间
        db.execute_update(
            "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
            (conversation_id,)
        )

        return message_id

    @staticmethod
    def get_messages(conversation_id: int, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取对话的消息列表

        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            消息列表
        """
        # 首先验证对话是否属于该用户
        conversation = ConversationDBService.get_conversation(conversation_id, user_id)
        if not conversation:
            return []

        sql = """
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """
        return db.execute_query(sql, (conversation_id, limit))

    @staticmethod
    def clear_messages(conversation_id: int, user_id: int) -> bool:
        """
        清除对话的所有消息

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            是否清除成功
        """
        # 首先验证对话是否属于该用户
        conversation = ConversationDBService.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        sql = """
            DELETE FROM messages
            WHERE conversation_id = %s
        """
        db.execute_update(sql, (conversation_id,))
        return True

    @staticmethod
    def delete_old_messages(days: int = 7) -> int:
        """
        删除指定天数之前的消息

        Args:
            days: 天数

        Returns:
            删除的消息数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        sql = """
            DELETE FROM messages
            WHERE created_at < %s
        """
        affected_rows = db.execute_update(sql, (cutoff_date,))
        return affected_rows

    @staticmethod
    def get_conversation_with_messages(conversation_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取对话及其消息

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            包含消息的对话信息
        """
        conversation = ConversationDBService.get_conversation(conversation_id, user_id)
        if not conversation:
            return None

        messages = ConversationDBService.get_messages(conversation_id, user_id)
        conversation['messages'] = messages

        return conversation


# 创建全局服务实例
conversation_db_service = ConversationDBService()
