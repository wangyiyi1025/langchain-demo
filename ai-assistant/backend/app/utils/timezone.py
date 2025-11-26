"""
时区工具函数
"""
from datetime import datetime
import pytz
from app.config import settings


def get_beijing_time() -> datetime:
    """
    获取当前北京时间

    Returns:
        datetime: 带时区信息的北京时间
    """
    beijing_tz = pytz.timezone(settings.TIMEZONE)
    return datetime.now(beijing_tz)


def utc_to_beijing(utc_dt: datetime) -> datetime:
    """
    将UTC时间转换为北京时间

    Args:
        utc_dt: UTC时间（naive或aware）

    Returns:
        datetime: 北京时间
    """
    beijing_tz = pytz.timezone(settings.TIMEZONE)

    # 如果是naive datetime，假设它是UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)

    # 转换到北京时间
    return utc_dt.astimezone(beijing_tz)


def beijing_to_utc(beijing_dt: datetime) -> datetime:
    """
    将北京时间转换为UTC时间

    Args:
        beijing_dt: 北京时间（naive或aware）

    Returns:
        datetime: UTC时间
    """
    beijing_tz = pytz.timezone(settings.TIMEZONE)

    # 如果是naive datetime，假设它是北京时间
    if beijing_dt.tzinfo is None:
        beijing_dt = beijing_tz.localize(beijing_dt)

    # 转换到UTC
    return beijing_dt.astimezone(pytz.utc)


def format_beijing_time(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化北京时间为字符串

    Args:
        dt: 时间对象，如果为None则使用当前时间
        fmt: 时间格式，默认为 "YYYY-MM-DD HH:MM:SS"

    Returns:
        str: 格式化后的时间字符串
    """
    if dt is None:
        dt = get_beijing_time()
    elif dt.tzinfo is None:
        # 如果是naive datetime，转换为北京时间
        dt = utc_to_beijing(dt)

    return dt.strftime(fmt)
