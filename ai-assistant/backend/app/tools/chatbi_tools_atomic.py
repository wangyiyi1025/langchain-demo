"""
ChatBI 原子工具 - 职责分离版本
每个工具只做一件事，通过上下文对象传递数据
"""
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import pymysql
import pandas as pd
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, asdict
import sys
import os
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings

# 配置日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ============================================================================
# QueryContext - 工具间上下文传递对象
# ============================================================================

@dataclass
class QueryContext:
    """工具间传递的上下文对象"""
    user_question: str = ""          # 原始用户问题（不修改）
    database: str = ""               # 数据库名
    table: str = ""                  # 表名
    current_time: Dict = None        # 当前时间信息
    schema_info: str = ""            # 表结构信息
    sql: str = ""                    # 生成的SQL
    sql_explanation: str = ""        # SQL解释
    query_result: List[Dict] = None  # 查询数据
    row_count: int = 0               # 数据行数
    data_analysis: Dict = None       # 数据分析结果
    chart_suggestion: Dict = None    # 图表推荐
    chart_config: Dict = None        # 图表配置

    def to_dict(self):
        """转换为字典"""
        return asdict(self)


# ============================================================================
# 时间对比分析知识库 - 唯一业务逻辑定义处
# ============================================================================

TIME_PERIOD_ANALYSIS_KNOWLEDGE = """
### 时间对比分析知识库

### 1. 同比(Year-over-Year, YoY) - 重点!!!
- **定义**: 与去年同一时期相比的变化情况
- **识别关键词**: "同比"、"去年同期"、"上年同期"、"与去年相比"、"YoY"
- **必须查询的数据**:
  - 当前期间的数据
  - 去年同期的数据(日期减1年)
- **SQL实现要点**:
  ```sql
  -- 错误示例(只查当年):
  SELECT ... FROM table WHERE YEAR(date_field) = 2025

  -- 正确示例(查询两年并对比):
  SELECT
    this_year.metric as current_value,
    last_year.metric as last_year_value,
    ((this_year.metric - last_year.metric) / last_year.metric * 100) as yoy_growth_rate
  FROM (
    SELECT ... FROM table WHERE YEAR(date_field) = 2025
  ) this_year
  LEFT JOIN (
    SELECT ... FROM table WHERE YEAR(date_field) = 2024
  ) last_year
  ON this_year.dimension = last_year.dimension
  ```

### 2. 环比(Period-over-Period) - 重点!!!
- **定义**: 与上一个相邻周期相比的变化情况
- **识别关键词**: "环比"、"上月"、"上季度"、"上周"、"较上期"、"MoM"、"QoQ"
- **必须查询的数据**:
  - 当前期间的数据
  - 上一个相邻期间的数据
- **SQL实现要点**:
  - 月环比: DATE_SUB(date_field, INTERVAL 1 MONTH)
  - 季度环比: DATE_SUB(date_field, INTERVAL 1 QUARTER)
  - 周环比: DATE_SUB(date_field, INTERVAL 1 WEEK)

### 3. 同期 - **重点理解!!!**
- **定义**: 截止到某个时间点的累计时间段,强调"到目前为止"的概念
- **识别关键词**: "同期"、"年初至今"、"累计"、"截至目前"
- **与"同比"的区别**:
  - "同比": 强调对比维度(与去年对比)
  - "同期": 强调时间范围(截止到当前时点的累计)
  - "同期同比": 两者结合,指截止当前时点的累计数据与去年同一时点的累计数据对比

- **时间范围计算**:

  **场景A: "2025年同期"(最常见)**
  - 含义: 2025年年初至当前日期(2025-11-27)的累计数据
  - 本年同期: 2025-01-01 至 2025-11-27
  - 去年同期: 2024-01-01 至 2024-11-27
  - SQL条件: `filing_time >= '2025-01-01' AND filing_time <= '2025-11-27'`

  **场景B: "2025年Q3同期"**
  - 含义: 2025年Q3期间与2024年Q3期间对比
  - 本年同期: 2025-07-01 至 2025-09-30
  - 去年同期: 2024-07-01 至 2024-09-30

  **场景C: "本月同期"**
  - 含义: 本月1日至今天的累计数据
  - 本月同期: 2025-11-01 至 2025-11-27
  - 上月同期: 2024-11-01 至 2024-11-27

- **关键判断逻辑**:
  ```
  如果用户问题包含"同期":
    1. 识别时间基准(年/季度/月)
    2. 计算"截止到当前"的日期范围
    3. 计算去年对应的日期范围
    4. 使用精确的日期条件而非YEAR()函数
  ```

## 典型场景SQL模板:

### 场景1: 年度同比(如"2025年XX同比增长前五"，不含"同期"关键词)
**分析步骤**:
1. 识别: "2025年" + "同比" → 需要对比2025年和2024年
2. 识别: "增长前五" → 需要计算增长值/增长率并排序取前5
3. 构建: 分别查询2025和2024数据,JOIN后计算增长

**SQL结构**:
```sql
SELECT
  t1.dimension_field,
  t1.metric_2025,
  t2.metric_2024,
  (t1.metric_2025 - t2.metric_2024) as growth_value,
  ROUND((t1.metric_2025 - t2.metric_2024) / t2.metric_2024 * 100, 2) as growth_rate
FROM (
  SELECT dimension_field, COUNT(*) as metric_2025
  FROM table_name
  WHERE YEAR(date_field) = 2025
  GROUP BY dimension_field
) t1
LEFT JOIN (
  SELECT dimension_field, COUNT(*) as metric_2024
  FROM table_name
  WHERE YEAR(date_field) = 2024
  GROUP BY dimension_field
) t2 ON t1.dimension_field = t2.dimension_field
WHERE t2.metric_2024 IS NOT NULL AND t2.metric_2024 > 0
ORDER BY growth_value DESC
LIMIT 5;
```

### 场景2: 年度同期同比(含"同期"关键词) - **重点!!!**
**用户问题**: "2025年XX同期同比增长最多"
**时间范围**: 2025-01-01至2025-11-27 vs 2024-01-01至2024-11-27(相对当前时间范围，提问时不明确也要默认使用当前时间范围)
**关键点**: 必须使用精确日期范围,不能使用YEAR()函数

**SQL结构**:
```sql
SELECT
  t1.dimension_field,
  t1.metric_current_period,
  t2.metric_last_year_period,
  (t1.metric_current_period - t2.metric_last_year_period) as growth_value,
  ROUND((t1.metric_current_period - t2.metric_last_year_period) / t2.metric_last_year_period * 100, 2) as growth_rate
FROM (
  -- 本年同期: 2025-01-01 至 2025-11-27
  SELECT dimension_field, COUNT(*) as metric_current_period
  FROM table_name
  WHERE date_field >= '2025-01-01' AND date_field <= '2025-11-27'
  GROUP BY dimension_field
) t1
LEFT JOIN (
  -- 去年同期: 2024-01-01 至 2024-11-27
  SELECT dimension_field, COUNT(*) as metric_last_year_period
  FROM table_name
  WHERE date_field >= '2024-01-01' AND date_field <= '2024-11-27'
  GROUP BY dimension_field
) t2 ON t1.dimension_field = t2.dimension_field
WHERE t2.metric_last_year_period IS NOT NULL AND t2.metric_last_year_period > 0
ORDER BY growth_value DESC
LIMIT 5;
```

## 关键检查清单:
遇到同比/环比问题时,请自检:
- [ ] 是否识别出了"同比"或"环比"关键词?
- [ ] 是否查询了**两个时间段**的数据?
- [ ] 是否正确计算了对比期间的日期范围?
- [ ] 是否在SELECT中包含了对比数据或增长率?
- [ ] 对于"增长前N",是否按增长值/增长率排序?
"""


# ============================================================================
# 数据库连接类（保持不变）
# ============================================================================

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

    def get_table_schema(self, database: str, table: str) -> Dict:
        """获取指定表的schema信息，包含表注释和字段注释，返回结构化数据"""
        try:
            # 获取表注释
            table_comment = ""
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW TABLE STATUS FROM {database} LIKE '{table}'")
                table_status = cursor.fetchone()
                if table_status and table_status.get('Comment'):
                    table_comment = table_status['Comment']

            # 获取字段详细信息（包含注释）
            columns_data = []
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW FULL COLUMNS FROM {database}.{table}")
                columns = cursor.fetchall()

                for col in columns:
                    field_name = col['Field']
                    field_type = col['Type']
                    is_nullable = "是" if col['Null'] == 'YES' else "否"
                    key_type = col['Key'] if col['Key'] else "-"
                    default_value = str(col['Default']) if col['Default'] is not None else "-"
                    comment = col.get('Comment', '')

                    columns_data.append({
                        "字段名": field_name,
                        "类型": field_type,
                        "允许NULL": is_nullable,
                        "键类型": key_type,
                        "默认值": default_value,
                        "说明": comment
                    })

            return {
                "database": database,
                "table": table,
                "table_comment": table_comment,
                "columns": columns_data
            }

        except Exception as e:
            raise Exception(f"获取表 {database}.{table} 的schema失败: {str(e)}")

    def get_database_schema(self, database: Optional[str] = None) -> Dict:
        """获取数据库schema信息，返回数据库和表的列表数据"""
        try:
            # 获取所有数据库
            if database:
                databases = [database]
            else:
                with self.connection.cursor() as cursor:
                    cursor.execute("SHOW DATABASES")
                    databases = [row['Database'] for row in cursor.fetchall()]

            # 收集数据库和表信息
            tables_data = []
            for db in databases:
                # 跳过系统数据库
                if db in ['information_schema', 'mysql', 'performance_schema', '__internal_schema']:
                    continue

                # 获取数据库中的表
                with self.connection.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES FROM {db}")
                    tables = cursor.fetchall()

                    for table_row in tables:
                        table_name = list(table_row.values())[0]

                        # 获取表注释
                        cursor.execute(f"SHOW TABLE STATUS FROM {db} LIKE '{table_name}'")
                        table_status = cursor.fetchone()
                        table_comment = ""
                        if table_status and table_status.get('Comment'):
                            table_comment = table_status['Comment']

                        # 获取字段数量
                        cursor.execute(f"SHOW FULL COLUMNS FROM {db}.{table_name}")
                        columns = cursor.fetchall()
                        column_count = len(columns)

                        tables_data.append({
                            "数据库": db,
                            "表名": table_name,
                            "完整表名": f"{db}.{table_name}",
                            "字段数": column_count,
                            "说明": table_comment
                        })

            return {
                "databases": databases if not database else [database],
                "tables": tables_data
            }

        except Exception as e:
            raise Exception(f"获取schema失败: {str(e)}")


# ============================================================================
# LLM 实例（单例）
# ============================================================================

_llm_instance = None

def get_llm():
    """获取LLM实例（单例模式）- 支持任何OpenAI兼容接口"""
    global _llm_instance
    if _llm_instance is None:
        try:
            # 根据配置选择是否使用 Tool Call 适配器
            if settings.USE_TOOL_CALL_ADAPTER:
                from app.utils.tool_call_adapter import create_adapted_llm
                _llm_instance = create_adapted_llm(
                    model=settings.LLM_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    max_retries=settings.LLM_MAX_RETRIES,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
                logger.info(f"LLM实例初始化成功（使用适配器）: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}, base_url={settings.OPENAI_BASE_URL}")
            else:
                _llm_instance = ChatOpenAI(
                    model=settings.LLM_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    max_retries=settings.LLM_MAX_RETRIES,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
                logger.info(f"LLM实例初始化成功: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}, base_url={settings.OPENAI_BASE_URL}")
        except Exception as e:
            logger.error(f"LLM实例初始化失败: {str(e)}")
            raise
    return _llm_instance


# ============================================================================
# 原子工具 1: get_schema_info - 获取表结构（无LLM）
# ============================================================================

@tool
def get_schema_info(database: str, table: str = None) -> str:
    """
    获取数据库表结构信息，以表格方式展示

    这是一个纯数据查询工具，不涉及LLM调用。

    Args:
        database: 数据库名称（必填）
        table: 表名称（可选，如果提供则只返回该表的字段信息）

    Returns:
        JSON字符串，包含schema信息和表格配置

    Examples:
        get_schema_info(database="sales_db")
        get_schema_info(database="sales_db", table="products")
    """
    log_prefix = "[chatbi_tools_atomic.py::get_schema_info]"

    try:
        db = StarrocksConnection()
        db.connect()

        if database and table:
            # 查询指定表的字段信息
            schema_data = db.get_table_schema(database, table)
            db.close()

            # 构建字段信息表格
            columns_data = schema_data["columns"]

            # 构建文本格式的schema_info（供nl_to_sql使用）
            schema_text = []
            schema_text.append(f"数据库: {database}")
            schema_text.append(f"表名: {table}")
            schema_text.append(f"完整表名: {database}.{table}")
            if schema_data["table_comment"]:
                schema_text.append(f"表说明: {schema_data['table_comment']}")
            schema_text.append("\n字段信息:")
            for col in columns_data:
                schema_text.append(f"  - {col['字段名']}: {col['类型']} (允许NULL: {col['允许NULL']}, 键类型: {col['键类型']}, 默认值: {col['默认值']}) // {col['说明']}")

            result = {
                "success": True,
                "scenario": "table_schema",
                "database": database,
                "table": table,
                "table_comment": schema_data["table_comment"],
                "row_count": len(columns_data),
                "data": columns_data,
                "columns": ["字段名", "类型", "允许NULL", "键类型", "默认值", "说明"],
                # 文本格式schema（供nl_to_sql使用）
                "schema_info": "\n".join(schema_text),
                # 表格配置
                "chart_config": {
                    "type": "table",
                    "title": f"表结构 - {database}.{table}" + (f" ({schema_data['table_comment']})" if schema_data['table_comment'] else ""),
                    "data": columns_data
                },
                "message": f"成功获取表 {database}.{table} 的结构，共 {len(columns_data)} 个字段"
            }

        else:
            # 查询数据库中的表列表
            schema_data = db.get_database_schema(database)
            db.close()

            tables_data = schema_data["tables"]

            # 构建文本格式的schema_info（供nl_to_sql使用）
            schema_text = []
            current_db = None
            for table_info in tables_data:
                if table_info["数据库"] != current_db:
                    current_db = table_info["数据库"]
                    schema_text.append(f"\n数据库: {current_db}")
                comment = f" // {table_info['说明']}" if table_info['说明'] else ""
                schema_text.append(f"  表: {table_info['完整表名']} ({table_info['字段数']}个字段){comment}")

            result = {
                "success": True,
                "scenario": "database_schema",
                "database": database,
                "row_count": len(tables_data),
                "data": tables_data,
                "columns": ["数据库", "表名", "完整表名", "字段数", "说明"],
                # 文本格式schema（供nl_to_sql使用）
                "schema_info": "\n".join(schema_text),
                # 表格配置
                "chart_config": {
                    "type": "table",
                    "title": f"数据库表列表 - {database}" if database else "所有数据库表列表",
                    "data": tables_data
                },
                "message": f"成功获取数据库 {database} 的表列表，共 {len(tables_data)} 个表" if database else f"成功获取所有数据库的表列表，共 {len(tables_data)} 个表"
            }

        logger.info(f"{log_prefix} 成功获取schema: database={database}, table={table}")
        return json.dumps(result, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    except Exception as e:
        logger.error(f"{log_prefix} 获取schema失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "database": database,
            "table": table
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 原子工具 2: nl_to_sql - 自然语言转SQL（唯一业务理解点，有LLM）
# ============================================================================

@tool
def nl_to_sql(question: str, schema_info: str, context: str = None) -> str:
    """
    将自然语言问题转换为SQL查询

    ⭐️ 这是唯一包含业务逻辑理解的工具 ⭐️
    所有关于同比、环比、同期等业务知识都在这里处理

    Args:
        question: 用户的原始自然语言问题（不要修改）
        schema_info: 表结构信息（来自get_schema_info工具）
        context: 可选的上下文信息（JSON字符串，包含current_time等）

    Returns:
        JSON字符串，包含生成的SQL和解释

    Examples:
        nl_to_sql(
            question="2025年销售额同期同比增长最多的产品前五",
            schema_info="...",
            context='{"current_time": {"date": "2025-11-28"}}'
        )
    """
    log_prefix = "[chatbi_tools_atomic.py::nl_to_sql]"

    try:
        # 解析上下文
        ctx = json.loads(context) if context else {}
        current_date = datetime.now().date()
        current_date_format = current_date.strftime("%Y年%m月%d日")
        current_year = current_date.year
        current_month = current_date.month
        current_day = current_date.day

        # 判断是否需要时间对比分析知识
        needs_time_analysis = any(keyword in question for keyword in ["同比", "环比", "同期"])
        time_knowledge = TIME_PERIOD_ANALYSIS_KNOWLEDGE if needs_time_analysis else ""

        # 构建prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的SQL专家。根据用户的自然语言问题和表结构信息，生成对应的SQL查询语句。

重要要求：
1. **只返回SQL语句，不要有任何其他说明文字**
2. **必须使用完整的表名**（格式：数据库名.表名，例如：sales_db.orders）
3. 使用标准的MySQL语法（Starrocks兼容MySQL协议）
4. 如果需要限制返回行数，默认使用 LIMIT 100
5. 确保SQL语句的安全性，防止SQL注入
6. 优先使用schema中明确提供的字段名，不要臆测
7. **对于时间对比分析需求（同比、环比、同期），必须准确理解时间范围并查询对应数据**

{time_knowledge}

当前时间信息：
- 当前日期：{current_date_format}
- 年份：{current_year}
- 月份：{current_month}
- 日：{current_day}

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
- 如果用户的问题中包含时间对比分析需求（如同比、环比、同期），请务必在SQL中体现相应的时间计算逻辑

请根据以上表结构信息生成SQL查询。"""),
            ("human", "{question}")
        ])

        # 调用LLM
        llm = get_llm()
        chain = prompt | llm

        formatted_messages = prompt.format_messages(
            question=question,
            schema_info=schema_info,
            current_date_format=current_date_format,
            current_year=current_year,
            current_month=current_month,
            current_day=current_day,
            time_knowledge=time_knowledge
        )

        llm_logcontent = {}
        for i, msg in enumerate(formatted_messages, 1):
            llm_logcontent[f"message_{i}"] = msg.content

        response = chain.invoke({
            "question": question,
            "schema_info": schema_info,
            "current_date_format": current_date_format,
            "current_year": current_year,
            "current_month": current_month,
            "current_day": current_day,
            "time_knowledge": time_knowledge
        })
        logger.debug(f"{log_prefix} 【LLM请求】:{llm_logcontent}，【LLM响应】:{response.content}")
        logger.info(f"{log_prefix} 【LLM请求】:{question}，【LLM响应】:{
            json.dumps(response.content, ensure_ascii=False, indent=2)
            }")

        # 清理SQL
        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        result = {
            "success": True,
            "sql": sql,
            "explanation": f"基于问题「{question}」生成的SQL查询",
            "has_time_analysis": needs_time_analysis
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"{log_prefix} SQL生成失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "question": question
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 原子工具 3: execute_sql - 执行SQL（无LLM）
# ============================================================================

@tool
def execute_sql(sql: str, database: str) -> str:
    """
    执行SQL查询并返回结果

    这是一个纯数据库操作工具，不涉及LLM调用。

    Args:
        sql: 要执行的SQL语句
        database: 数据库名称（用于连接，实际查询使用SQL中的完整表名）

    Returns:
        JSON字符串，包含查询结果和元数据

    Examples:
        execute_sql(
            sql="SELECT * FROM sales_db.products LIMIT 10",
            database="sales_db"
        )
    """
    log_prefix = "[chatbi_tools_atomic.py::execute_sql]"

    try:
        db = StarrocksConnection()
        db.connect()

        # 执行查询
        result_data = db.execute_query(sql)

        db.close()

        result = {
            "success": True,
            "sql": sql,
            "row_count": len(result_data),
            "data": result_data[:100],  # 限制返回数据量
            "columns": list(result_data[0].keys()) if result_data else []
        }

        logger.info(f"{log_prefix} SQL执行成功: 返回{len(result_data)}行数据")
        return json.dumps(result, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    except Exception as e:
        logger.error(f"{log_prefix} SQL执行失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "sql": sql
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 原子工具 4: analyze_data - 分析查询结果（有LLM）
# ============================================================================

@tool
def analyze_data(data: str, question: str) -> str:
    """
    分析查询结果数据，提供洞察和见解

    Args:
        data: 查询结果数据（JSON字符串）
        question: 用户的原始问题

    Returns:
        JSON字符串，包含数据分析结果

    Examples:
        analyze_data(
            data='[{"product": "A", "sales": 1000}, ...]',
            question="哪些产品销售额最高"
        )
    """
    log_prefix = "[chatbi_tools_atomic.py::analyze_data]"

    try:
        # 解析数据
        data_list = json.loads(data) if isinstance(data, str) else data

        if not data_list:
            return json.dumps({
                "success": True,
                "insights": "查询结果为空，没有数据可供分析",
                "summary": "无数据",
                "characteristics": {}
            }, ensure_ascii=False, indent=2)

        # 转换为DataFrame进行分析
        df = pd.DataFrame(data_list)

        # 准备数据信息
        columns = list(df.columns)
        row_count = len(df)
        sample_data = df.head(5).to_string()

        # 生成统计信息
        stats_info = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                stats_info.append(f"{col}: 数值型, 范围 {df[col].min()} - {df[col].max()}, 平均值 {df[col].mean():.2f}")
            else:
                unique_count = df[col].nunique()
                stats_info.append(f"{col}: 分类型, {unique_count} 个不同值")

        data_stats = "\n".join(stats_info)

        # 构建prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个数据分析专家。根据查询结果和用户问题，提供有价值的数据洞察。

请分析数据并提供：
1. 关键发现和洞察（2-3条）
2. 数据摘要
3. 数据特征

以JSON格式返回：
{{
    "insights": ["洞察1", "洞察2", "洞察3"],
    "summary": "数据摘要（1-2句话）",
    "characteristics": {{
        "total_records": 数量,
        "key_metrics": {{"指标名": 值}}
    }}
}}

只返回JSON，不要有其他文字。"""),
            ("human", """用户问题: {question}

数据列名: {columns}
数据行数: {row_count}
数据示例（前5行）:
{sample_data}

数据统计信息:
{data_stats}

请分析这些数据并提供洞察。""")
        ])

        # 调用LLM
        llm = get_llm()
        chain = prompt | llm

        formatted_messages = prompt.format_messages(
            question=question,
            columns=", ".join(columns),
            row_count=row_count,
            sample_data=sample_data,
            data_stats=data_stats
        )

        llm_logcontent = {}
        for i, msg in enumerate(formatted_messages, 1):
            llm_logcontent[f"message_{i}"] = msg.content

        response = chain.invoke({
            "question": question,
            "columns": ", ".join(columns),
            "row_count": row_count,
            "sample_data": sample_data,
            "data_stats": data_stats
        })

        logger.debug(f"{log_prefix} 【LLM请求】:{llm_logcontent}，【LLM响应】:{
            json.dumps(response.content, ensure_ascii=False, indent=2)
            }")
        logger.info(f"{log_prefix} 【LLM请求】:{question}，【LLM响应】:{
            json.dumps(response.content, ensure_ascii=False, indent=2)
            }")

        # 解析响应
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        analysis = json.loads(content.strip())
        analysis["success"] = True

        return json.dumps(analysis, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"{log_prefix} 数据分析失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "insights": ["分析失败"],
            "summary": f"分析出错: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 原子工具 5: suggest_chart - 推荐图表类型（有LLM）
# ============================================================================

@tool
def suggest_chart(data: str, question: str, analysis: str = None) -> str:
    """
    根据数据和问题推荐最合适的图表类型

    Args:
        data: 查询结果数据（JSON字符串）
        question: 用户的原始问题
        analysis: 可选的数据分析结果（JSON字符串）

    Returns:
        JSON字符串，包含图表类型推荐

    Examples:
        suggest_chart(
            data='[{"month": "Jan", "sales": 1000}, ...]',
            question="显示月度销售趋势",
            analysis='{"insights": [...]}'
        )
    """
    log_prefix = "[chatbi_tools_atomic.py::suggest_chart]"

    try:
        # 解析数据
        data_list = json.loads(data) if isinstance(data, str) else data

        if not data_list:
            return json.dumps({
                "success": True,
                "chart_type": "none",
                "reason": "查询结果为空，无法生成图表",
                "title": "无数据"
            }, ensure_ascii=False, indent=2)

        # 转换为DataFrame
        df = pd.DataFrame(data_list)
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

        # 构建prompt
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

只返回JSON，不要有其他文字。"""),
            ("human", """用户问题: {question}

数据列名: {columns}
数据行数: {row_count}
数据示例（前3行）:
{sample_data}

数据统计信息:
{data_stats}

{analysis_info}

请推荐最合适的图表类型。""")
        ])

        # 准备分析信息
        analysis_info = ""
        if analysis:
            try:
                analysis_data = json.loads(analysis) if isinstance(analysis, str) else analysis
                if "insights" in analysis_data:
                    analysis_info = f"数据洞察: {', '.join(analysis_data['insights'])}"
            except:
                pass

        # 调用LLM
        llm = get_llm()
        chain = prompt | llm

        formatted_messages = prompt.format_messages(
            question=question,
            columns=", ".join(columns),
            row_count=row_count,
            sample_data=sample_data,
            data_stats=data_stats,
            analysis_info=analysis_info
        )

        llm_logcontent = {}
        for i, msg in enumerate(formatted_messages, 1):
            llm_logcontent[f"message_{i}"] = msg.content

        response = chain.invoke({
            "question": question,
            "columns": ", ".join(columns),
            "row_count": row_count,
            "sample_data": sample_data,
            "data_stats": data_stats,
            "analysis_info": analysis_info
        })

        logger.debug(f"{log_prefix} 【LLM请求】:{llm_logcontent}，【LLM响应】:{
            json.dumps(response.content, ensure_ascii=False, indent=2)
            }")
        logger.info(f"{log_prefix} 【LLM请求】:{question}，【LLM响应】:{response.content}")

        # 解析响应
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        suggestion = json.loads(content.strip())
        suggestion["success"] = True

        return json.dumps(suggestion, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"{log_prefix} 图表推荐失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "chart_type": "table",
            "reason": f"推荐失败，默认使用表格: {str(e)}",
            "title": "查询结果"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 原子工具 6: generate_chart_config - 生成图表配置（无LLM）
# ============================================================================

@tool
def generate_chart_config(data: str, chart_suggestion: str) -> str:
    """
    根据数据和图表推荐生成前端图表配置

    这是一个纯配置生成工具，不涉及LLM调用。

    Args:
        data: 查询结果数据（JSON字符串）
        chart_suggestion: 图表推荐结果（JSON字符串）

    Returns:
        JSON字符串，包含完整的图表配置

    Examples:
        generate_chart_config(
            data='[{"month": "Jan", "sales": 1000}, ...]',
            chart_suggestion='{"chart_type": "bar", "x_axis": "month", "y_axis": "sales"}'
        )
    """
    log_prefix = "[chatbi_tools_atomic.py::generate_chart_config]"

    try:
        # 解析输入
        data_list = json.loads(data) if isinstance(data, str) else data
        suggestion = json.loads(chart_suggestion) if isinstance(chart_suggestion, str) else chart_suggestion

        if not data_list:
            return json.dumps({
                "success": True,
                "config": {}
            }, ensure_ascii=False, indent=2)

        df = pd.DataFrame(data_list)
        chart_type = suggestion.get("chart_type", "table")

        # 基础配置
        config = {
            "type": chart_type,
            "title": suggestion.get("title", "数据分析结果"),
            "data": data_list[:100]  # 限制数据量
        }

        # 根据图表类型添加特定配置
        if chart_type in ["bar", "line", "area"]:
            config["x_axis"] = suggestion.get("x_axis", df.columns[0])
            config["y_axis"] = suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        elif chart_type == "pie":
            config["label_field"] = suggestion.get("x_axis", df.columns[0])
            config["value_field"] = suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        elif chart_type == "scatter":
            config["x_axis"] = suggestion.get("x_axis", df.columns[0])
            config["y_axis"] = suggestion.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])

        result = {
            "success": True,
            "config": config
        }

        logger.info(f"{log_prefix} 图表配置生成成功: type={chart_type}")
        return json.dumps(result, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    except Exception as e:
        logger.error(f"{log_prefix} 图表配置生成失败: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "config": {}
        }, ensure_ascii=False, indent=2)
