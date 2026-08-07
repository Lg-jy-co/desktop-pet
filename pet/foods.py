"""食物目录：投喂时减少饥饿度、增加心情度。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class Food:
    key: str
    name: str
    satiety: float   # 0-100，减少的饥饿度数值
    mood: float      # 增加的心情度
    emoji: str = "🍎"


FOODS: list[Food] = [
    Food("apple", "红苹果", 35, 4, "🍎"),
    Food("cake", "小蛋糕", 50, 12, "🍰"),
    Food("fish", "小鱼干", 60, 6, "🐟"),
    Food("chicken", "大鸡腿", 70, 10, "🍗"),
    Food("cola", "可乐水", 20, 15, "🥤"),
    Food("snack", "薯片零食", 100, 20, "🍻"),
]

FOOD_BY_KEY = {food.key: food for food in FOODS}


# ==================== 本地文件投喂规则配置 ====================

# 扩展名倍率规则：扩展名(小写) -> 倍率
FILE_EXT_MULTIPLIERS: dict[str, float] = {
    ".txt": 5.0,
    ".md": 3.0,
    ".py": 10.0,
    ".json": 2.0,
    ".js": 2.0,
    ".ts": 2.0,
    ".html": 2.0,
    ".css": 2.0,
    ".pdf": 3.0,
    ".doc": 3.0,
    ".docx": 3.0,
    ".xls": 3.0,
    ".xlsx": 3.0,
    ".png": 2.0,
    ".jpg": 2.0,
    ".jpeg": 2.0,
    ".gif": 2.0,
    ".bmp": 2.0,
    ".webp": 2.0,
    ".mp3": 2.0,
    ".mp4": 2.0,
    ".zip": 2.0,
    ".rar": 2.0,
    ".7z": 2.0,
}

# 文件名关键词倍率规则：关键词(小写) -> 倍率
FILE_NAME_KEYWORD_MULTIPLIERS: dict[str, float] = {
    "水果": 2.0,
    "果": 2.0,
    "蔬菜": 1.5,
    "肉": 2.0,
    "零食": 3.0,
    "甜": 2.0,
    "好吃": 2.0,
    "美味": 2.0,
    "猫": 2.0,
    "狗": 2.0,
    "宠物": 2.0,
    "gift": 5.0,
    "present": 5.0,
    "treat": 3.0,
    "food": 2.0,
    "yummy": 2.0,
    "delicious": 2.0,
}

# 基础投喂值
BASE_FILE_FEED_VALUE: float = 1.0

# 最大投喂值上限（防止刷分）
MAX_FILE_FEED_VALUE: float = 200.0


def calculate_file_feed_value(file_path: str | Path) -> tuple[float, float, dict]:
    """
    计算本地文件的投喂值。

    规则：
    1. 基础值 = 1
    2. 扩展名匹配：在基础值上乘以对应倍率（如 .txt *5, .py *10）
    3. 文件名关键词匹配：在扩展名结果上再乘以对应倍率（如含"水果" *2）
    4. 最终值取整，并限制在最大值内

    返回: (satiety, mood, detail_dict)
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    name = path.stem.lower()

    # 1. 基础值
    value = BASE_FILE_FEED_VALUE
    detail = {
        "base": BASE_FILE_FEED_VALUE,
        "ext": ext,
        "ext_multiplier": 1.0,
        "name_keywords": [],
        "name_multiplier": 1.0,
        "final_value": 0.0,
    }

    # 2. 扩展名倍率
    ext_mult = FILE_EXT_MULTIPLIERS.get(ext, 1.0)
    if ext_mult != 1.0:
        value *= ext_mult
        detail["ext_multiplier"] = ext_mult

    # 3. 文件名关键词倍率（取最大匹配的倍率，不叠加）
    matched_keywords = []
    max_name_mult = 1.0
    for keyword, mult in FILE_NAME_KEYWORD_MULTIPLIERS.items():
        if keyword.lower() in name:
            matched_keywords.append(keyword)
            if mult > max_name_mult:
                max_name_mult = mult

    if matched_keywords:
        value *= max_name_mult
        detail["name_keywords"] = matched_keywords
        detail["name_multiplier"] = max_name_mult

    # 4. 限制最大值并取整
    final_value = min(round(value), MAX_FILE_FEED_VALUE)
    detail["final_value"] = final_value

    # 饱食度和心情度按比例分配（饱食度权重 0.7，心情度权重 0.3）
    satiety = final_value * 0.7
    mood = final_value * 0.3

    return satiety, mood, detail


def create_food_from_file(file_path: str | Path) -> Food:
    """根据文件创建一个临时的 Food 对象用于投喂。"""
    path = Path(file_path)
    satiety, mood, detail = calculate_file_feed_value(file_path)
    ext = path.suffix.lower()
    keywords_str = ", ".join(detail["name_keywords"]) if detail["name_keywords"] else "无"
    name = f"文件: {path.name} (饱:{int(satiety)} 心:{int(mood)}) [扩展名:{ext} 关键词:{keywords_str}]"
    return Food(
        key=f"file_{path.stem}_{path.suffix.lower().lstrip('.')}",
        name=name,
        satiety=satiety,
        mood=mood,
        emoji="📁",
    )