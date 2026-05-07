"""
事件抽取模块
提供从新闻文本中提取结构化事件的功能
"""

from .llm_extractor import ExtractedEvent, LLMEventExtractor

__all__ = ["ExtractedEvent", "LLMEventExtractor"]
