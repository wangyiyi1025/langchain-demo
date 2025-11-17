"""
搜索工具
"""
from langchain_core.tools import tool
import pytz

import random

def random_pick_two(words_list):
    # 确保输入列表至少有 2 个元素，避免报错
    if len(words_list) < 2:
        raise ValueError("输入的数组至少需要包含 2 个词")
    # random.sample 用于无放回随机抽样，直接抽取 2 个元素
    return random.sample(words_list, k=2)

excellent_words = [
    "正直", "谦逊", "担当", "守信", "沉稳", "宽厚", "坚毅", "自律",
    "睿智", "干练", "专业", "果敢", "远见", "精进", "高效", "博学",
    "儒雅", "挺拔", "从容", "磊落", "洒脱", "大气", "务实", "格局",
    "热忱", "大度", "尽责", "谦和", "果敢", "通透"
]


@tool
def wangwei_info() -> str:
    """
    查询王唯信息
    
    Returns:
        王唯的相关信息
    """
    selected_words = random_pick_two(excellent_words)
    return f"王唯是一个{selected_words[0]}且{selected_words[1]}的人。"
