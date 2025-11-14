"""
时间工具
"""
from langchain_core.tools import tool
from datetime import datetime
import pytz


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """
    获取当前时间
    
    Args:
        timezone: 时区，默认为 Asia/Shanghai (北京时间)
                 其他选项: America/New_York, Europe/London, UTC
    
    Returns:
        格式化的当前时间字符串
    """
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        return current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        return f"获取时间失败: {str(e)}"


@tool
def get_date_info() -> str:
    """
    获取详细的日期信息
    
    Returns:
        包含年、月、日、星期等信息的字符串
    """
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    
    return f"""今天是 {now.year}年{now.month}月{now.day}日，{weekday}
当前时间：{now.strftime("%H:%M:%S")}
这是今年的第 {now.timetuple().tm_yday} 天"""