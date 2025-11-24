# ChatBI 数据分析工具使用说明

## 功能概述

ChatBI 是一个智能数据分析工具,可以通过自然语言查询 Starrocks 数据库,并自动生成可视化图表建议。

## 主要功能

1. **自然语言转SQL**: 使用千问大模型将用户的自然语言问题转换为标准SQL查询
2. **数据库查询**: 自动连接Starrocks数据库并执行SQL查询
3. **智能分析**: 分析查询结果并给出最合适的可视化图表建议
4. **可视化配置**: 自动生成图表配置,包括图表类型、坐标轴、标题等

## 配置要求

### 数据库连接信息
- **主机**: 127.0.0.1
- **端口**: 9030
- **用户名**: admin
- **密码**: 123456

### 依赖安装

```bash
pip install -r requirements.txt
```

新增的依赖包括:
- `pymysql`: MySQL数据库连接
- `pandas`: 数据分析
- `matplotlib`: 可视化(可选)

## 使用方法

### 1. 通过聊天界面使用

启动应用后,直接在聊天界面中提问:

```
"查询用户表中的总记录数"
"显示最近一周的订单金额趋势"
"分析各地区的销售额占比"
"获取销售额最高的前10个产品"
```

### 2. 查看数据库结构

```
"显示数据库有哪些表"
"查看订单表的结构"
```

### 3. 可用的工具

#### chatbi_query
使用自然语言查询数据库并获得分析结果

**参数:**
- `question` (str): 自然语言问题
- `database` (str, 可选): 指定数据库名称

**返回:** JSON格式的分析结果,包含:
- `success`: 是否成功
- `sql`: 生成的SQL语句
- `data`: 查询结果数据
- `chart_suggestion`: 图表建议
- `chart_config`: 图表配置

#### chatbi_get_schema
获取数据库表结构信息

**参数:**
- `database` (str, 可选): 指定数据库名称

**返回:** 数据库schema信息

## 工作流程

```
用户自然语言问题
    ↓
获取数据库Schema
    ↓
LLM生成SQL查询
    ↓
执行SQL查询
    ↓
分析查询结果
    ↓
LLM建议图表类型
    ↓
生成可视化配置
    ↓
返回结果+可视化建议
```

## 支持的图表类型

1. **柱状图 (bar)**: 适合比较不同类别的数值
2. **折线图 (line)**: 适合展示趋势变化
3. **饼图 (pie)**: 适合展示占比关系
4. **散点图 (scatter)**: 适合展示两个变量的关系
5. **表格 (table)**: 适合展示详细数据
6. **面积图 (area)**: 适合展示趋势和累积
7. **热力图 (heatmap)**: 适合展示矩阵数据

## 示例查询

### 基础查询
```
问题: "有多少个用户?"
生成SQL: SELECT COUNT(*) as user_count FROM users LIMIT 100;
图表建议: 表格
```

### 趋势分析
```
问题: "最近7天每天的订单数量"
生成SQL: SELECT DATE(order_date) as date, COUNT(*) as order_count
         FROM orders
         WHERE order_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
         GROUP BY DATE(order_date)
         ORDER BY date
         LIMIT 100;
图表建议: 折线图 (x轴: date, y轴: order_count)
```

### 占比分析
```
问题: "各个地区的销售额占比"
生成SQL: SELECT region, SUM(amount) as total_amount
         FROM sales
         GROUP BY region
         LIMIT 100;
图表建议: 饼图 (标签: region, 值: total_amount)
```

### 排名分析
```
问题: "销售额最高的前10个产品"
生成SQL: SELECT product_name, SUM(amount) as total_sales
         FROM sales
         GROUP BY product_name
         ORDER BY total_sales DESC
         LIMIT 10;
图表建议: 柱状图 (x轴: product_name, y轴: total_sales)
```

## 安全特性

1. **SQL注入防护**: 使用参数化查询和LLM生成安全的SQL
2. **连接池管理**: 每次查询独立连接,避免连接泄露
3. **数据量限制**: 默认限制返回100行数据,防止大数据集
4. **错误处理**: 完善的异常捕获和错误提示

## 注意事项

1. 确保Starrocks数据库服务正常运行
2. 确保网络连接到数据库服务器
3. 首次使用时,建议先使用 `chatbi_get_schema` 了解数据库结构
4. 复杂查询可能需要多次交互来优化SQL
5. 可视化建议基于数据特征自动生成,可根据需要调整

## 故障排查

### 无法连接数据库
- 检查Starrocks服务是否运行
- 验证连接参数(host, port, user, password)
- 检查防火墙设置

### SQL执行失败
- 使用 `chatbi_get_schema` 确认表名和字段名
- 检查生成的SQL语法
- 尝试重新表述问题

### 返回结果为空
- 确认数据表中有数据
- 检查查询条件是否过于严格
- 使用更宽泛的查询条件

## 技术架构

- **数据库**: Starrocks (兼容MySQL协议)
- **ORM**: PyMySQL
- **AI模型**: 千问 (ChatTongyi)
- **数据处理**: Pandas
- **框架**: LangChain

## 后续优化方向

1. 支持更多数据库类型(MySQL, PostgreSQL等)
2. 增加数据缓存机制
3. 支持复杂的多表关联查询
4. 实现图表的实际渲染和导出
5. 添加查询历史记录功能
6. 支持自定义SQL模板
