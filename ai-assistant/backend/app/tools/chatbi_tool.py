"""
ChatBI 数据分析工具
支持自然语言查询 Starrocks 数据库并生成可视化图表
"""
from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
import pymysql
import pandas as pd
import json
import base64
from io import BytesIO
from typing import Dict, Any, Optional, List
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class StarrocksConnection:
    """Starrocks 数据库连接管理器"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9030,
                 user: str = "admin", password: str = "123456"):
        """初始化数据库连接配置"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            raise Exception(f"数据库连接失败: {str(e)}")

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()

    def execute_query(self, sql: str) -> List[Dict]:
        """执行SQL查询"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                return result
        except Exception as e:
            raise Exception(f"SQL执行失败: {str(e)}")

    def get_database_schema(self, database: Optional[str] = None) -> str:
        """获取数据库schema信息"""
        try:
            schema_info = []

            # 获取所有数据库
            if database:
                databases = [database]
            else:
                with self.connection.cursor() as cursor:
                    cursor.execute("SHOW DATABASES")
                    databases = [row['Database'] for row in cursor.fetchall()]

            for db in databases:
                # 跳过系统数据库
                if db in ['information_schema', 'mysql', 'performance_schema', '__internal_schema']:
                    continue

                schema_info.append(f"\n数据库: {db}")

                # 获取数据库中的表
                with self.connection.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES FROM {db}")
                    tables = cursor.fetchall()

                    for table_row in tables[:5]:  # 只显示前5个表
                        table_name = list(table_row.values())[0]
                        schema_info.append(f"\n  表: {db}.{table_name}")

                        # 获取表结构
                        cursor.execute(f"DESC {db}.{table_name}")
                        columns = cursor.fetchall()

                        for col in columns:
                            schema_info.append(f"    - {col['Field']} ({col['Type']})")

            return "\n".join(schema_info) if schema_info else "未找到数据库表信息"

        except Exception as e:
            return f"获取schema失败: {str(e)}"


class ChatBIAnalyzer:
    """ChatBI 分析器，使用LLM进行数据分析"""

    def __init__(self):
        """初始化分析器"""
        self.llm = ChatTongyi(
            model=settings.QWEN_MODEL,
            temperature=0.1,  # 较低的温度以获得更准确的SQL
            max_tokens=2000,
        )
        self.db = StarrocksConnection()

    def natural_language_to_sql(self, question: str, schema_info: str) -> str:
        """将自然语言问题转换为SQL查询"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的SQL专家。根据用户的自然语言问题和数据库schema，生成对应的SQL查询语句。

要求：
1. 只返回SQL语句，不要有任何其他说明文字
2. SQL语句要完整且可执行
3. 使用标准的MySQL语法（Starrocks兼容MySQL协议）
4. 如果需要限制返回行数，默认使用 LIMIT 100
5. 确保SQL语句的安全性，防止SQL注入

数据库Schema信息：
{schema_info}

请根据以上schema信息生成SQL查询。
"""),
            ("human", "{question}")
        ])

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "schema_info": schema_info
        })

        # 提取SQL语句（清理可能的markdown代码块格式）
        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        return sql.strip()

    def analyze_data_and_suggest_chart(self, data: List[Dict], question: str) -> Dict[str, Any]:
        """分析数据并建议合适的图表类型"""

        if not data:
            return {
                "chart_type": "none",
                "reason": "查询结果为空",
                "config": {}
            }

        # 转换为DataFrame进行分析
        df = pd.DataFrame(data)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个数据可视化专家。根据查询结果和用户问题，建议最合适的图表类型。

可用的图表类型：
1. bar - 柱状图：适合比较不同类别的数值
2. line - 折线图：适合展示趋势变化
3. pie - 饼图：适合展示占比关系
4. scatter - 散点图：适合展示两个变量的关系
5. table - 表格：适合展示详细数据
6. area - 面积图：适合展示趋势和累积
7. heatmap - 热力图：适合展示矩阵数据

请以JSON格式返回建议，格式如下：
{{
    "chart_type": "图表类型",
    "reason": "选择原因",
    "x_axis": "X轴字段名（如果适用）",
    "y_axis": "Y轴字段名或字段列表（如果适用）",
    "title": "图表标题"
}}

只返回JSON，不要有其他文字。
"""),
            ("human", """
用户问题: {question}

数据列名: {columns}
数据行数: {row_count}
数据示例（前3行）:
{sample_data}

数据统计信息:
{data_stats}
""")
        ])

        # 准备数据信息
        columns = list(df.columns)
        row_count = len(df)
        sample_data = df.head(3).to_string()

        # 生成统计信息
        stats_info = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                stats_info.append(f"{col}: 数值型, 范围 {df[col].min()} - {df[col].max()}")
            else:
                unique_count = df[col].nunique()
                stats_info.append(f"{col}: 分类型, {unique_count} 个不同值")

        data_stats = "\n".join(stats_info)

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "columns": ", ".join(columns),
            "row_count": row_count,
            "sample_data": sample_data,
            "data_stats": data_stats
        })

        try:
            # 解析JSON响应
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            suggestion = json.loads(content.strip())
            return suggestion
        except Exception as e:
            # 如果解析失败，返回默认建议
            return {
                "chart_type": "table",
                "reason": f"无法解析建议: {str(e)}",
                "title": "查询结果"
            }

    def generate_chart_config(self, data: List[Dict], chart_suggestion: Dict) -> Dict[str, Any]:
        """生成图表配置"""
        if not data:
            return {}

        df = pd.DataFrame(data)
        chart_type = chart_suggestion.get("chart_type", "table")

        # 基础配置
        config = {
            "type": chart_type,
            "title": chart_suggestion.get("title", "数据分析结果"),
            "data": data[:100]  # 限制数据量
        }

        # 根据图表类型添加特定配置
        if chart_type in ["bar", "line", "area"]:
            config["x_axis"] = chart_suggestion.get("x_axis", df.columns[0])
            config["y_axis"] = chart_suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        elif chart_type == "pie":
            config["label_field"] = chart_suggestion.get("x_axis", df.columns[0])
            config["value_field"] = chart_suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        elif chart_type == "scatter":
            config["x_axis"] = chart_suggestion.get("x_axis", df.columns[0])
            config["y_axis"] = chart_suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        return config

    def analyze(self, question: str, database: Optional[str] = None) -> str:
        """
        分析自然语言问题，生成SQL并返回结果和可视化配置

        Args:
            question: 用户的自然语言问题
            database: 指定的数据库名称（可选）

        Returns:
            分析结果的JSON字符串
        """
        try:
            # 连接数据库
            self.db.connect()

            # 获取schema信息
            schema_info = self.db.get_database_schema(database)

            if "未找到" in schema_info or "失败" in schema_info:
                return json.dumps({
                    "success": False,
                    "error": "无法获取数据库schema信息",
                    "schema_info": schema_info
                }, ensure_ascii=False, indent=2)

            # 生成SQL
            sql = self.natural_language_to_sql(question, schema_info)

            # 执行查询
            result_data = self.db.execute_query(sql)

            # 分析数据并建议图表
            chart_suggestion = self.analyze_data_and_suggest_chart(result_data, question)

            # 生成图表配置
            chart_config = self.generate_chart_config(result_data, chart_suggestion)

            # 准备返回结果
            response = {
                "success": True,
                "question": question,
                "sql": sql,
                "row_count": len(result_data),
                "data": result_data[:50],  # 只返回前50行数据
                "chart_suggestion": chart_suggestion,
                "chart_config": chart_config,
                "message": f"成功执行查询，返回 {len(result_data)} 行数据"
            }

            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "question": question
            }, ensure_ascii=False, indent=2)

        finally:
            # 关闭数据库连接
            self.db.close()


# 创建全局分析器实例
_analyzer = None

def get_analyzer():
    """获取分析器实例（单例模式）"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ChatBIAnalyzer()
    return _analyzer


@tool
def chatbi_query(question: str, database: str = None) -> str:
    """
    使用自然语言查询 Starrocks 数据库并进行数据分析和可视化

    Args:
        question: 自然语言问题，例如 "查询销售额前10的产品" 或 "分析最近30天的用户增长趋势"
        database: 指定要查询的数据库名称（可选）

    Returns:
        包含查询结果、SQL语句和可视化建议的JSON字符串

    Examples:
        - "查询用户表中的总记录数"
        - "显示最近一周的订单金额趋势"
        - "分析各地区的销售额占比"
    """
    analyzer = get_analyzer()
    return analyzer.analyze(question, database)


@tool
def chatbi_get_schema(database: str = None) -> str:
    """
    获取 Starrocks 数据库的表结构信息

    Args:
        database: 指定要查询的数据库名称（可选），不指定则返回所有数据库信息

    Returns:
        数据库schema信息的字符串描述
    """
    try:
        db = StarrocksConnection()
        db.connect()
        schema_info = db.get_database_schema(database)
        db.close()

        return f"数据库Schema信息：\n\n{schema_info}"
    except Exception as e:
        return f"获取schema失败: {str(e)}"
