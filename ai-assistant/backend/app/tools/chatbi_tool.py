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
from datetime import datetime, date
from decimal import Decimal
import sys
import os
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings

# 配置日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime、date和Decimal类型"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class StarrocksConnection:
    """Starrocks 数据库连接管理器"""

    def __init__(self, host: str = None, port: int = None,
                 user: str = None, password: str = None):
        """初始化数据库连接配置"""
        # 从配置文件读取连接信息
        self.host = host or settings.STARROCKS_HOST
        self.port = port or settings.STARROCKS_PORT
        self.user = user or settings.STARROCKS_USER
        self.password = password or settings.STARROCKS_PASSWORD
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
        """获取数据库schema信息，包含表注释和字段注释"""
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

                        # 获取表注释
                        cursor.execute(f"SHOW TABLE STATUS FROM {db} LIKE '{table_name}'")
                        table_status = cursor.fetchone()
                        table_comment = ""
                        if table_status and table_status.get('Comment'):
                            table_comment = f" // {table_status['Comment']}"

                        schema_info.append(f"\n  表: {db}.{table_name}{table_comment}")

                        # 获取表结构（包含字段注释）
                        cursor.execute(f"SHOW FULL COLUMNS FROM {db}.{table_name}")
                        columns = cursor.fetchall()

                        for col in columns:
                            field_name = col['Field']
                            field_type = col['Type']
                            # 获取字段注释
                            comment = col.get('Comment', '')
                            comment_info = f" // {comment}" if comment else ""
                            schema_info.append(f"    - {field_name} ({field_type}){comment_info}")

            return "\n".join(schema_info) if schema_info else "未找到数据库表信息"

        except Exception as e:
            return f"获取schema失败: {str(e)}"

    def get_table_schema(self, database: str, table: str) -> str:
        """
        获取指定表的schema信息，包含表注释和字段注释

        Args:
            database: 数据库名称
            table: 表名称

        Returns:
            表结构的详细描述，包含中文注释
        """
        try:
            schema_info = []
            schema_info.append(f"数据库: {database}")
            schema_info.append(f"表名: {table}")
            schema_info.append(f"完整表名: {database}.{table}")

            # 获取表注释
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW TABLE STATUS FROM {database} LIKE '{table}'")
                table_status = cursor.fetchone()
                if table_status and table_status.get('Comment'):
                    schema_info.append(f"表说明: {table_status['Comment']}")

            schema_info.append("\n字段信息:")

            # 获取字段详细信息（包含注释）
            with self.connection.cursor() as cursor:
                # 使用 SHOW FULL COLUMNS 获取完整的字段信息，包括注释
                cursor.execute(f"SHOW FULL COLUMNS FROM {database}.{table}")
                columns = cursor.fetchall()

                for col in columns:
                    field_name = col['Field']
                    field_type = col['Type']
                    null_info = "允许NULL" if col['Null'] == 'YES' else "不允许NULL"
                    key_info = f", 键类型: {col['Key']}" if col['Key'] else ""
                    default_info = f", 默认值: {col['Default']}" if col['Default'] else ""

                    # 获取字段注释（中文说明）
                    comment = col.get('Comment', '')
                    comment_info = f" // {comment}" if comment else ""

                    schema_info.append(
                        f"  - {field_name}: {field_type} ({null_info}{key_info}{default_info}){comment_info}"
                    )

            return "\n".join(schema_info)

        except Exception as e:
            return f"获取表 {database}.{table} 的schema失败: {str(e)}"


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

        log_prefix = "[chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql]"

        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的SQL专家。根据用户的自然语言问题和表结构信息，生成对应的SQL查询语句。

重要要求：
1. **只返回SQL语句，不要有任何其他说明文字**
2. **必须使用完整的表名**（格式：数据库名.表名，例如：sales_db.orders）
3. 使用标准的MySQL语法（Starrocks兼容MySQL协议）
4. 如果需要限制返回行数，默认使用 LIMIT 100
5. 确保SQL语句的安全性，防止SQL注入
6. 优先使用schema中明确提供的字段名，不要臆测
7. 处理时间对比分析需求（同比、环比、同期）

## 时间对比分析概念：

### 1. 同比（Year-over-Year, YoY）
- **定义**: 与去年同一时期相比的变化情况
- **识别关键词**: "同比"、"去年同期"、"上年同期"、"与去年相比"
- **计算方法**: 同比增长率 = (本期数据 - 去年同期数据) / 去年同期数据 × 100%
- **SQL处理**:
  - 需要查询两个时间段的数据：当前期间和去年同期
  - 日期处理：使用 DATE_SUB(当前日期, INTERVAL 1 YEAR) 或类似函数
  - 示例：查询2024年3月销售额同比 → 需要查询2024年3月和2023年3月的数据

### 2. 环比（Period-over-Period）
- **定义**: 与上一个相邻周期相比的变化情况
- **识别关键词**: "环比"、"上月"、"上季度"、"上周"、"较上期"
- **计算方法**: 环比增长率 = (本期数据 - 上期数据) / 上期数据 × 100%
- **SQL处理**:
  - 月环比：对比相邻两个月，如2024年3月 vs 2024年2月
  - 周环比：对比相邻两周
  - 日环比：对比相邻两天
  - 日期处理：使用 DATE_SUB(当前日期, INTERVAL 1 MONTH/WEEK/DAY)

### 3. 同期
- **定义**: 去年的相同时间段，用作同比分析的对比基准
- **识别关键词**: "同期"、"去年同期"、"上年同期"
- **使用场景**: 通常与同比一起使用，如"与去年同期相比"
- **SQL处理**: 计算去年的对应日期范围

## 时间对比分析示例：

**用户问题**: "查询今年3月销售额同比增长情况"
**分析步骤**:
1. 识别时间对比类型：同比（Year-over-Year）
2. 确定时间范围：今年3月（2024-03） vs 去年3月（2023-03）
3. 构建查询：查询两个时间段的销售额数据
4. 计算增长率：(今年3月销售额 - 去年3月销售额) / 去年3月销售额 × 100%

**用户问题**: "本月销售额环比上月如何"
**分析步骤**:
1. 识别时间对比类型：环比（Month-over-Month）
2. 确定时间范围：本月 vs 上月
3. 构建查询：查询连续两个月的销售额数据
4. 计算增长率：(本月销售额 - 上月销售额) / 上月销售额 × 100%

表结构信息：
{schema_info}

注意事项：
- 上述schema信息已经包含了完整的表名（数据库名.表名）
- 请在SQL中使用这个完整的表名
- **重点关注字段后面的注释（//后面的中文说明）**，这是字段的中文含义
- 根据用户的中文查询需求，通过注释信息找到对应的英文字段名
- 例如：用户问"查询销售额"，如果看到字段 `sales_amount (decimal) // 销售金额`，则应该使用 `sales_amount` 字段
- 仔细查看字段类型，确保查询条件的数据类型匹配
- 对于时间字段，注意使用正确的日期函数

请根据以上表结构信息生成SQL查询。
"""),
            ("human", "{question}")
        ])

        # 记录LLM调用
        logger.info(f"\n{'='*100}")
        logger.info(f"{log_prefix} LLM调用开始")
        logger.info(f"{'='*100}")
        logger.info(f"【请求】用户问题: {question}")
        logger.info(f"【请求】Schema信息:\n{schema_info}")

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "schema_info": schema_info
        })

        logger.info(f"【响应】LLM原始返回:\n{response.content}")

        # 提取SQL语句（清理可能的markdown代码块格式）
        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        sql = sql.strip()
        logger.info(f"【结果】提取的SQL: {sql}")
        logger.info(f"{log_prefix} LLM调用完成")
        logger.info(f"{'='*100}\n")

        return sql

    def analyze_data_and_suggest_chart(self, data: List[Dict], question: str) -> Dict[str, Any]:
        """分析数据并建议合适的图表类型"""

        log_prefix = "[chatbi_tool.py::ChatBIAnalyzer::analyze_data_and_suggest_chart]"

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

        # 记录LLM调用
        logger.info(f"\n{'='*100}")
        logger.info(f"{log_prefix} LLM调用开始")
        logger.info(f"{'='*100}")
        logger.info(f"【请求】用户问题: {question}")
        logger.info(f"【请求】数据列名: {', '.join(columns)}")
        logger.info(f"【请求】数据行数: {row_count}")
        logger.info(f"【请求】数据统计:\n{data_stats}")

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "columns": ", ".join(columns),
            "row_count": row_count,
            "sample_data": sample_data,
            "data_stats": data_stats
        })

        logger.info(f"【响应】LLM原始返回:\n{response.content}")

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
            logger.info(f"【结果】图表建议: {json.dumps(suggestion, ensure_ascii=False, indent=2)}")
            logger.info(f"{log_prefix} LLM调用完成")
            logger.info(f"{'='*100}\n")
            return suggestion
        except Exception as e:
            # 如果解析失败，返回默认建议
            logger.error(f"【错误】解析失败: {str(e)}")
            default_suggestion = {
                "chart_type": "table",
                "reason": f"无法解析建议: {str(e)}",
                "title": "查询结果"
            }
            logger.info(f"【结果】使用默认建议: {json.dumps(default_suggestion, ensure_ascii=False)}")
            logger.info(f"{log_prefix} LLM调用完成（失败，使用默认值）")
            logger.info(f"{'='*100}\n")
            return default_suggestion

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

    def analyze(self, question: str, database: Optional[str] = None, table: Optional[str] = None) -> str:
        """
        分析自然语言问题，生成SQL并返回结果和可视化配置

        Args:
            question: 用户的自然语言问题
            database: 指定的数据库名称（可选）
            table: 指定的表名称（可选，强烈推荐提供）

        Returns:
            分析结果的JSON字符串
        """
        try:
            # 连接数据库
            self.db.connect()

            # 获取schema信息（如果指定了表，只获取该表的schema）
            if database and table:
                schema_info = self.db.get_table_schema(database, table)
            else:
                schema_info = self.db.get_database_schema(database)

            if "失败" in schema_info:
                return json.dumps({
                    "success": False,
                    "error": "无法获取数据库schema信息",
                    "schema_info": schema_info
                }, ensure_ascii=False, indent=2)

            # 生成SQL（会有LLM调用日志）
            sql = self.natural_language_to_sql(question, schema_info)

            # 执行查询
            result_data = self.db.execute_query(sql)

            # 分析数据并建议图表（会有LLM调用日志）
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

            return json.dumps(response, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

        except Exception as e:
            logger.error(f"[chatbi_tool.py::ChatBIAnalyzer::analyze] 执行失败: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "question": question
            }, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

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
def chatbi_query(question: str, database: str = None, table: str = None) -> str:
    """
    使用自然语言查询 Starrocks 数据库并进行数据分析和可视化

    Args:
        question: 自然语言问题，例如 "查询销售额前10的产品" 或 "分析最近30天的用户增长趋势"
        database: 指定要查询的数据库名称（推荐）
        table: 指定要查询的表名称（强烈推荐，可显著提高查询准确性和速度）

    Returns:
        包含查询结果、SQL语句和可视化建议的JSON字符串

    Examples:
        - chatbi_query("查询用户总数", database="user_db", table="users")
        - chatbi_query("显示最近一周的订单金额趋势", database="sales_db", table="orders")
        - chatbi_query("分析各地区的销售额占比", database="sales_db", table="sales_data")

    注意：
        - 强烈建议同时提供 database 和 table 参数，这样可以：
          1. 减少 LLM 处理的数据量，提高响应速度
          2. 提高 SQL 生成的准确性
          3. 避免在多表环境中产生歧义
    """
    analyzer = get_analyzer()
    return analyzer.analyze(question, database, table)


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
