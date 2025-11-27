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

# 时间对比分析说明
# 用于指导LLM正确理解和处理同比、环比、同期等时间对比分析需求
# 放在这里以便后续扩展和维护
# 可以在生成SQL的prompt中引用
time_period_analysis_instructions = """

### 1. 同比(Year-over-Year, YoY) - 重点!!!
- **定义**: 与去年同一时期相比的变化情况
- **识别关键词**: \"同比\"、\"去年同期\"、\"上年同期\"、\"与去年相比\"、\"YoY\"
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
- **识别关键词**: \"环比\"、\"上月\"、\"上季度\"、\"上周\"、\"较上期\"、\"MoM\"、\"QoQ\"
- **必须查询的数据**:
  - 当前期间的数据
  - 上一个相邻期间的数据
- **SQL实现要点**:
  - 月环比: DATE_SUB(date_field, INTERVAL 1 MONTH)
  - 季度环比: DATE_SUB(date_field, INTERVAL 1 QUARTER)
  - 周环比: DATE_SUB(date_field, INTERVAL 1 WEEK)

### 3. 同期 - **重点理解!!!**
- **定义**: 截止到某个时间点的累计时间段,强调\"到目前为止\"的概念
- **识别关键词**: \"同期\"、\"年初至今\"、\"累计\"、\"截至目前\"
- **与\"同比\"的区别**:
  - \"同比\": 强调对比维度(与去年对比)
  - \"同期\": 强调时间范围(截止到当前时点的累计)
  - \"同期同比\": 两者结合,指截止当前时点的累计数据与去年同一时点的累计数据对比

- **时间范围计算**:
  
  **场景A: \"2025年同期\"(最常见)**
  - 含义: 2025年年初至当前日期(2025-11-27)的累计数据
  - 本年同期: 2025-01-01 至 2025-11-27
  - 去年同期: 2024-01-01 至 2024-11-27
  - SQL条件: `filing_time >= '2025-01-01' AND filing_time <= '2025-11-27'`
  
  **场景B: \"2025年Q3同期\"**
  - 含义: 2025年Q3期间与2024年Q3期间对比
  - 本年同期: 2025-07-01 至 2025-09-30
  - 去年同期: 2024-07-01 至 2024-09-30
  
  **场景C: \"本月同期\"**
  - 含义: 本月1日至今天的累计数据
  - 本月同期: 2025-11-01 至 2025-11-27
  - 上月同期: 2024-11-01 至 2024-11-27

- **关键判断逻辑**:
  ```
  如果用户问题包含\"同期\":
    1. 识别时间基准(年/季度/月)
    2. 计算\"截止到当前\"的日期范围
    3. 计算去年对应的日期范围
    4. 使用精确的日期条件而非YEAR()函数
  ```
## 典型场景SQL模板:
### 场景1: 年度同比(如\"2025年XX同比增长前五\"，不含\"同期\"关键词)
**分析步骤**:
1. 识别: \"2025年\" + \"同比\" → 需要对比2025年和2024年
2. 识别: \"增长前五\" → 需要计算增长值/增长率并排序取前5
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

### 场景2: 月度同比(如\"3月销售额同比\",不含\"同期\"关键词) 
```sql
SELECT 
  t1.sales_amount_current,
  t2.sales_amount_last_year,
  (t1.sales_amount_current - t2.sales_amount_last_year) as yoy_growth
FROM (
  SELECT SUM(sales_amount) as sales_amount_current
  FROM table_name
  WHERE YEAR(date_field) = 2025 AND MONTH(date_field) = 3
) t1
CROSS JOIN (
  SELECT SUM(sales_amount) as sales_amount_last_year
  FROM table_name
  WHERE YEAR(date_field) = 2024 AND MONTH(date_field) = 3
) t2;
```

### 场景3: 年度同期同比(含\"同期\"关键词) - **重点!!!**
**用户问题**: \"2025年XX同期同比增长最多\"
**时间范围**: 2025-01-01至2025-11-27 vs 2024-01-01至2024-11-27(相对当前时间范围)
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

### 场景4: 月度同期同比
**用户问题**: \"本月XX同期同比\"
**时间范围**: 2025-11-01至2025-11-27 vs 2024-11-01至2024-11-27
```sql
SELECT 
  t1.metric_current,
  t2.metric_last_year,
  (t1.metric_current - t2.metric_last_year) as growth
FROM (
  SELECT COUNT(*) as metric_current
  FROM table_name
  WHERE date_field >= '2025-11-01' AND date_field <= '2025-11-27'
) t1
CROSS JOIN (
  SELECT COUNT(*) as metric_last_year
  FROM table_name
  WHERE date_field >= '2024-11-01' AND date_field <= '2024-11-27'
) t2;
```
### 场景5: 月度环比(如\"本月销售额环比上月\")
```sql
SELECT 
  t1.sales_current_month,
  t2.sales_last_month,
  (t1.sales_current_month - t2.sales_last_month) / t2.sales_last_month * 100 as mom_rate
FROM (
  SELECT SUM(sales_amount) as sales_current_month
  FROM table_name
  WHERE YEAR(date_field) = 2025 AND MONTH(date_field) = 11
) t1
CROSS JOIN (
  SELECT SUM(sales_amount) as sales_last_month
  FROM table_name
  WHERE YEAR(date_field) = 2025 AND MONTH(date_field) = 10
) t2;
```

"""

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
            max_retries=1,
        )
        self.db = StarrocksConnection()

    def natural_language_to_sql(self, question: str, schema_info: str) -> str:
        """将自然语言问题转换为SQL查询"""

        log_prefix = "[chatbi_tool.py::ChatBIAnalyzer::natural_language_to_sql]"
    
        current_date = datetime.now().date()
        current_date_format = current_date.strftime("%Y年%m月%d日")
        current_year = current_date.year
        current_month = current_date.month
        current_day = current_date.day_of_year
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的SQL专家。根据用户的自然语言问题和表结构信息,生成对应的SQL查询语句。

**当前时间上下文**: 
- 当前完整日期: {current_date_format}
- 当前年份: {current_year}年
- 当前月份: {current_month}月
- 当前日期在年内: 第{current_day}天 ({current_year}-01-01 到 {current_date_format})

重要要求:
1. **只返回SQL语句,不要有任何其他说明文字**
2. **必须使用完整的表名**(格式:数据库名.表名,例如:sales_db.orders)
3. 使用标准的MySQL语法(Starrocks兼容MySQL协议)
4. 如果需要限制返回行数,默认使用 LIMIT 100
5. 确保SQL语句的安全性,防止SQL注入
6. 优先使用schema中明确提供的字段名,不要臆测
7. **对于时间对比分析需求(同比、环比、同期),必须准确理解时间范围并查询对应数据**

{time_period_analysis_infomation}

## 关键检查清单:
遇到同比/环比问题时,请自检:
- [ ] 是否识别出了\"同比\"或\"环比\"关键词?
- [ ] 是否查询了**两个时间段**的数据?
- [ ] 是否正确计算了对比期间的日期范围?
- [ ] 是否在SELECT中包含了对比数据或增长率?
- [ ] 对于\"增长前N\",是否按增长值/增长率排序?

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
- 如果用户的问题中包含时间对比分析需求（如同比、环比、同期)，请务必在SQL中体现相应的时间计算逻辑

请根据以上表结构信息生成SQL查询。
"""),
            ("human", "{question}")
        ])
        
        # 节约点token
        time_period_analysis_infomation ="" 
        if question.find("同比") != -1 or question.find("环比") != -1 or question.find("同期") != -1 :
            time_period_analysis_infomation = time_period_analysis_instructions
        
        # 渲染prompt并记录
        formatted_messages = prompt.format_messages(question=question, 
                                                    schema_info=schema_info, 
                                                    current_month=current_month, 
                                                    current_year=current_year, 
                                                    current_date_format=current_date_format,
                                                    time_period_analysis_infomation=time_period_analysis_infomation)
        llm_logcontent = {}
        for i, msg in enumerate(formatted_messages, 1):
            llm_logcontent[f"message_{i}"] = msg.content

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "schema_info": schema_info,
            "current_month": current_month,
            "current_year": current_year,
            "current_date_format": current_date_format,
            "time_period_analysis_infomation": time_period_analysis_infomation
        })
        logger.info(f"{log_prefix} 【LLM请求】:{llm_logcontent}，【LLM响应】:{response.content}")

        # 提取SQL语句（清理可能的markdown代码块格式）
        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        sql = sql.strip()
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

        # 渲染prompt并记录
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

        chain = prompt | self.llm
        response = chain.invoke({
            "question": question,
            "columns": ", ".join(columns),
            "row_count": row_count,
            "sample_data": sample_data,
            "data_stats": data_stats
        })
        logger.info(f"{log_prefix} 【LLM请求】:{llm_logcontent}，【LLM响应】:{response.content}")

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
            logger.error(f"【错误】解析失败: {str(e)}")
            default_suggestion = {
                "chart_type": "table",
                "reason": f"无法解析建议: {str(e)}",
                "title": "查询结果"
            }
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
