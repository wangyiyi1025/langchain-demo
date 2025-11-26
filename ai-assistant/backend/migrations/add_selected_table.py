#!/usr/bin/env python3
"""
添加selected_table字段到conversations表
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db

def add_selected_table_column():
    """添加selected_table字段"""
    try:
        # 检查字段是否已存在
        columns = db.execute_query("DESCRIBE conversations")
        has_selected_table = any(col['Field'] == 'selected_table' for col in columns)

        if has_selected_table:
            print("✓ selected_table字段已存在，无需添加")
            return True

        print("正在添加selected_table字段...")

        # 添加字段
        db.execute_update("""
            ALTER TABLE conversations
            ADD COLUMN selected_table TEXT NULL
            COMMENT '选中的表信息（JSON格式）'
            AFTER title
        """)

        print("✓ selected_table字段添加成功！")

        # 验证字段已添加
        columns = db.execute_query("DESCRIBE conversations")
        has_selected_table = any(col['Field'] == 'selected_table' for col in columns)

        if has_selected_table:
            print("\n验证成功：")
            print("=" * 60)
            for col in columns:
                if col['Field'] == 'selected_table':
                    print(f"字段名: {col['Field']}")
                    print(f"类型: {col['Type']}")
                    print(f"允许NULL: {col['Null']}")
                    print(f"注释: {col.get('Comment', '')}")
            print("=" * 60)
            return True
        else:
            print("✗ 验证失败：字段未成功添加")
            return False

    except Exception as e:
        print(f"❌ 添加字段失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：添加selected_table字段")
    print("=" * 60)
    success = add_selected_table_column()
    sys.exit(0 if success else 1)
