#!/usr/bin/env python3
"""检查数据库表结构"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import db

try:
    # 检查conversations表结构
    columns = db.execute_query("DESCRIBE conversations")

    print("=" * 60)
    print("conversations表结构:")
    print("=" * 60)
    for col in columns:
        print(f"{col['Field']:20} {col['Type']:20} {col['Null']:5} {col['Key']:5} {str(col.get('Default', 'NULL')):10}")

    # 检查是否有selected_table字段
    has_selected_table = any(col['Field'] == 'selected_table' for col in columns)

    print("\n" + "=" * 60)
    if has_selected_table:
        print("✓ selected_table字段已存在")
    else:
        print("✗ selected_table字段不存在 - 需要执行数据库迁移！")
        print("\n请运行以下Python命令添加字段：")
        print("python migrations/add_selected_table.py")
        print("\n或直接执行SQL：")
        print("ALTER TABLE conversations ADD COLUMN selected_table TEXT NULL COMMENT '选中的表信息（JSON格式）' AFTER title;")
    print("=" * 60)

except Exception as e:
    print(f"❌ 数据库检查失败: {str(e)}")
    print("\n请检查：")
    print("1. MySQL服务是否正在运行")
    print("2. .env文件中的数据库配置是否正确")
    print("3. 数据库smart_chat_bi_meta是否已创建")
    import traceback
    traceback.print_exc()
