"""
基于LLM的事件抽取模块
从新闻文本中提取结构化事件信息
"""
import json
import re
import logging
from typing import Optional

from pydantic import BaseModel, Field

from ..llm_client import get_llm, LLMError

logger = logging.getLogger(__name__)


# Few-shot prompt for event extraction
EVENT_EXTRACTION_PROMPT = """你是一个专业的事件抽取系统。请从以下新闻文本中提取结构化事件信息。

要求：
1. 严格输出JSON格式，不要包含任何其他文字
2. 所有字段都必须填写，如果信息不明确使用"未知"或空列表
3. event_type可选值：地缘政治、大宗商品、宏观经济、金融市场、行业动态、公司事件

输出格式：
{
    "subject": "事件主体（如国家、组织、公司）",
    "predicate": "事件谓词/动作（如制裁、减产、加息）",
    "object": "事件客体（如被制裁国家、产品）",
    "event_type": "事件类型",
    "intensity": "事件强度（高/中/低）",
    "region": "涉及地区",
    "key_entities": ["关键实体列表"]
}

示例1：
输入：美国对伊朗实施新制裁
输出：{"subject": "美国", "predicate": "制裁", "object": "伊朗", "event_type": "地缘政治", "intensity": "高", "region": "中东/波斯湾", "key_entities": ["美国", "伊朗", "霍尔木兹海峡"]}

示例2：
输入：OPEC宣布每日减产200万桶
输出：{"subject": "OPEC", "predicate": "减产", "object": "原油", "event_type": "大宗商品", "intensity": "高", "region": "全球", "key_entities": ["OPEC", "原油", "沙特阿拉伯", "俄罗斯"]}

示例3：
输入：中国人民银行宣布降息25个基点
输出：{"subject": "中国人民银行", "predicate": "降息", "object": "基准利率", "event_type": "宏观经济", "intensity": "中", "region": "中国", "key_entities": ["中国人民银行", "降息", "货币政策"]}

现在请分析以下新闻：

标题：{title}
内容：{content}

输出："""


class ExtractedEvent(BaseModel):
    """结构化事件模型"""
    subject: str = Field(description="事件主体（如国家、组织、公司）")
    predicate: str = Field(description="事件谓词/动作")
    object: str = Field(description="事件客体")
    event_type: str = Field(description="事件类型：地缘政治/大宗商品/宏观经济/金融市场/行业动态/公司事件")
    intensity: str = Field(description="事件强度：高/中/低")
    region: str = Field(description="涉及地区")
    key_entities: list[str] = Field(default_factory=list, description="关键实体列表")


class LLMEventExtractor:
    """基于LLM的事件抽取器"""

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """懒加载LLM客户端"""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def extract_event(self, title: str, content: str) -> ExtractedEvent:
        """
        从新闻标题和内容中提取结构化事件

        Args:
            title: 新闻标题
            content: 新闻正文内容

        Returns:
            ExtractedEvent: 结构化事件对象
        """
        # 构建提示词
        prompt = EVENT_EXTRACTION_PROMPT.format(title=title, content=content)

        try:
            # 调用LLM进行事件抽取
            response = await self.llm.complete(
                prompt=prompt,
                response_model=None,  # 我们手动解析JSON
                max_tokens=1024
            )

            # 尝试解析JSON响应
            event = self._parse_llm_response(response)
            if event:
                logger.info(f"LLM成功抽取事件: {event.subject} - {event.predicate}")
                return event

        except LLMError as e:
            logger.warning(f"LLM事件抽取失败: {e}，启用关键词降级")
        except Exception as e:
            logger.warning(f"事件抽取异常: {e}，启用关键词降级")

        # 降级到关键词抽取
        return self._keyword_fallback(title + " " + content)

    def _parse_llm_response(self, response: str) -> Optional[ExtractedEvent]:
        """解析LLM返回的JSON响应"""
        try:
            # 尝试直接解析
            data = json.loads(response)
            return ExtractedEvent(**data)
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return ExtractedEvent(**data)
            except json.JSONDecodeError:
                pass

        # 尝试从文本中提取JSON对象
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            try:
                data = json.loads(response[start:end])
                return ExtractedEvent(**data)
            except json.JSONDecodeError:
                pass

        return None

    def _keyword_fallback(self, text: str) -> ExtractedEvent:
        """
        基于关键词的降级事件抽取

        Args:
            text: 原始文本（标题+内容）

        Returns:
            ExtractedEvent: 结构化事件对象
        """
        text_lower = text.lower()

        # 事件类型关键词映射
        event_type_keywords = {
            "地缘政治": ["制裁", "战争", "冲突", "军事", "外交", "条约", "谈判", "封锁", "禁运"],
            "大宗商品": ["原油", "石油", "黄金", "天然气", "煤炭", "粮食", "OPEC", "减产", "增产", "库存"],
            "宏观经济": ["加息", "降息", "gdp", "通胀", "cpi", "ppi", "非农", "失业率", "央行", "货币政策"],
            "金融市场": ["股市", "债市", "汇率", "指数", "期货", "期权", "熔断", "央行干预"],
            "行业动态": ["行业", "产能", "技术", "监管", "政策", "标准", "认证"],
            "公司事件": ["财报", "并购", "重组", "裁员", "上市", "退市", "业绩", "订单"],
        }

        # 地区关键词映射
        region_keywords = {
            "美国": ["美国", "美联储", "华盛顿", "美股", "美元"],
            "中国": ["中国", "中国人民银行", "A股", "人民币", "北京"],
            "欧洲": ["欧盟", "欧洲", "欧元区", "德国", "法国", "英国"],
            "中东": ["伊朗", "沙特", "以色列", " OPEC", "霍尔木兹", "中东"],
            "俄罗斯": ["俄罗斯", "俄乌", "普京", "莫斯科"],
            "亚太": ["日本", "韩国", "澳大利亚", "印度", "东南亚"],
        }

        # 强度关键词
        high_intensity = ["战争", "制裁", "封禁", "禁止", "大幅", "剧烈", "严重", "紧急", "声明"]
        medium_intensity = ["宣布", "计划", "预计", "可能", "考虑", "提议"]
        low_intensity = ["小幅", "轻微", "温和", "有限", "试探"]

        # 提取事件类型
        detected_type = "其他"
        max_matches = 0
        for event_type, keywords in event_type_keywords.items():
            matches = sum(1 for k in keywords if k in text)
            if matches > max_matches:
                max_matches = matches
                detected_type = event_type

        # 提取地区
        detected_region = "全球"
        for region, keywords in region_keywords.items():
            if any(k in text for k in keywords):
                detected_region = region
                break

        # 提取强度
        if any(k in text for k in high_intensity):
            intensity = "高"
        elif any(k in text for k in medium_intensity):
            intensity = "中"
        elif any(k in text for k in low_intensity):
            intensity = "低"
        else:
            intensity = "中"

        # 提取关键实体（简单分词 + 关键词匹配）
        entities = []
        known_entities = [
            "美国", "中国", "伊朗", "俄罗斯", "欧盟", "德国", "法国", "英国", "日本",
            "OPEC", "沙特", "以色列", "美联储", "中国人民银行", "加拿大", "澳大利亚",
            "原油", "黄金", "天然气", "石油", "美元", "人民币", "欧元", "日元",
            "股市", "债市", "期货", "指数"
        ]
        for entity in known_entities:
            if entity in text:
                entities.append(entity)

        # 提取主谓宾（简单规则）
        subject, predicate, obj = self._extract_svo_simple(text)

        return ExtractedEvent(
            subject=subject,
            predicate=predicate,
            object=obj,
            event_type=detected_type,
            intensity=intensity,
            region=detected_region,
            key_entities=list(set(entities))[:10]  # 去重并限制数量
        )

    def _extract_svo_simple(self, text: str) -> tuple[str, str, str]:
        """
        简单的主谓宾提取

        Returns:
            (subject, predicate, object)
        """
        # 常见动词模式
        verb_patterns = [
            (r'([\u4e00-\u9fa5]{2,})(制裁|禁运|封锁)', r'\1'),  # A制裁B
            (r'([\u4e00-\u9fa5]{2,})(宣布|表示|称)', r'\1'),  # A宣布
            (r'([\u4e00-\u9fa5]{2,})(减产|增产|供应)', r'\1'),  # A减产
            (r'([\u4e00-\u9fa5]{2,})(加息|降息|宽松|紧缩)', r'\1'),  # A加息
        ]

        subject = "未知"
        predicate = "未知"
        obj = "未知"

        # 简单模式匹配
        for pattern, sub_pattern in verb_patterns:
            match = re.search(pattern, text)
            if match:
                if sub_pattern == r'\1':
                    subject = match.group(1)
                    predicate = match.group(2)
                break

        # 如果没匹配到，尝试其他模式
        if subject == "未知":
            # 尝试 "XX对YY实施XX" 模式
            match = re.search(r'([\u4e00-\u9fa5]{2,})对([\u4e00-\u9fa5]{2,})实施([\u4e00-\u9fa5]{2,})', text)
            if match:
                return match.group(1), match.group(3), match.group(2)

            # 尝试 "XX宣布XX" 模式
            match = re.search(r'([\u4e00-\u9fa5]{2,})宣布([\u4e00-\u9fa5]{2,})', text)
            if match:
                return match.group(1), "宣布", match.group(2)

        return subject, predicate, obj
