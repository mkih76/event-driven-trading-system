"""
Pydantic 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """事件类型"""
    GEOPOLITICAL = "地缘政治"      # 战争、制裁、封锁
    POLICY = "政策"               # 法规、监管、财政
    DISASTER = "灾难"             # 自然灾害、疫情、事故
    ECONOMIC = "经济数据"         # GDP、CPI、利率
    EARNINGS = "财报"             # 业绩公告
    TECHNOLOGY = "技术突破"       # 创新、突破
    OTHER = "其他"


class ImpactDirection(str, Enum):
    """影响方向"""
    POSITIVE = "利好"
    NEGATIVE = "利空"
    NEUTRAL = "中性"


class ImpactMagnitude(str, Enum):
    """影响程度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class SignalType(str, Enum):
    """交易信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TransmissionRelationType(str, Enum):
    """传导关系类型"""
    COST_UP = "成本传导"          # 原材料/成本上涨
    COST_DOWN = "成本下降"        # 原材料/成本下降
    COST_INCREASE = "成本增加"    # 成本增加（成本传导的变体）
    DEMAND_UP = "需求增加"
    DEMAND_DOWN = "需求减少"
    SUPPLY_UP = "供给增加"
    SUPPLY_DOWN = "供给减少"
    SUBSTITUTE = "替代效应"
    RATE_CHANGE = "利率变动"
    RISK_APPETITE = "风险偏好"
    CAPITAL_FLOW = "资金流动"
    SAFE_HAVEN = "避险需求"       # 替代品需求变化


class DirectImpact(BaseModel):
    """直接受影响行业"""
    industry: str = Field(..., description="行业名称")
    impact_direction: ImpactDirection
    impact_magnitude: ImpactMagnitude
    impact_score: float = Field(..., description="影响分数 -10 到 +10")


class TransmissionStep(BaseModel):
    """传导步骤"""
    step: int = Field(..., description="传导步骤序号")
    from_industry: str = Field(..., description="上游行业")
    to_industry: str = Field(..., description="下游行业")
    relation_type: TransmissionRelationType
    transmission_rate: float = Field(..., description="传导系数 0.0-1.0")
    time_lag_days: int = Field(..., description="传导滞后天数")
    impact_magnitude: ImpactMagnitude
    impact_score: float = Field(..., description="影响分数 -10 到 +10")
    description: str = Field(..., description="传导机制描述")


class InvestmentSignal(BaseModel):
    """投资信号"""
    industry: str = Field(..., description="行业名称")
    signal: SignalType
    confidence: float = Field(..., ge=0, le=100, description="置信度 0-100")
    reasoning: str = Field(..., description="信号理由")


class EventAnalysisResult(BaseModel):
    """事件分析结果"""
    event_type: EventType
    core_entities: List[str] = Field(..., description="核心实体列表")
    sentiment: float = Field(..., ge=-1.0, le=1.0, description="情绪值 -1.0 到 1.0")
    event_intensity: ImpactMagnitude
    summary: str = Field(..., description="50字事件摘要")
    direct_impacts: List[DirectImpact] = Field(default_factory=list)


class TransmissionChainResult(BaseModel):
    """产业链传导分析结果"""
    transmission_chain: List[TransmissionStep] = Field(default_factory=list)
    affected_industries: List[str] = Field(default_factory=list)
    investment_signals: List[InvestmentSignal] = Field(default_factory=list)


class StockSignal(BaseModel):
    """个股交易信号"""
    industry: str = Field(default="", description="所属行业")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    signal_type: SignalType
    confidence: float = Field(..., ge=0, le=100)
    impact_score: float = Field(..., ge=-100, le=100)
    chain_depth: int = Field(..., description="传导深度")
    entry_rationale: str = Field(..., description="入场理由")
    risk_factors: List[str] = Field(default_factory=list)
    related_stocks: List[str] = Field(default_factory=list)
    backtest_reference: Optional[Dict[str, Any]] = Field(default=None, description="历史回测参考")


class FullAnalysisResult(BaseModel):
    """完整分析结果"""
    # 原始输入
    input_title: str
    input_content: str

    # 事件分析
    event_analysis: EventAnalysisResult

    # 传导分析
    transmission: TransmissionChainResult

    # 信号
    signals: List[StockSignal] = Field(default_factory=list)

    # 元数据
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[int] = None


# API 请求/响应模型
class AnalyzeRequest(BaseModel):
    """分析请求"""
    title: str = Field(..., description="事件标题")
    content: str = Field(..., description="事件内容（可选）")
    use_cache: bool = Field(default=True, description="是否使用缓存")


class AnalyzeResponse(BaseModel):
    """分析响应"""
    success: bool
    data: Optional[FullAnalysisResult] = None
    error: Optional[str] = None


# 多事件分析模型
class EventInput(BaseModel):
    """单个事件输入"""
    title: str = Field(..., description="事件标题")
    content: str = Field(default="", description="事件内容（可选）")
    date: Optional[str] = Field(default=None, description="事件日期（可选）")


class MultiEventAnalyzeRequest(BaseModel):
    """多事件组合分析请求"""
    events: List[EventInput] = Field(..., description="事件列表", min_length=2, max_length=10)
    strategy: str = Field(default="combined", description="分析策略: combined(综合分析) / comparative(对比分析) / chain(链式分析)")
    use_cache: bool = Field(default=True, description="是否使用缓存")


class EventCombinationAnalysis(BaseModel):
    """事件组合分析结果"""
    combined_summary: str = Field(..., description="组合事件综合摘要")
    event_interactions: List[Dict[str, Any]] = Field(default_factory=list, description="事件间交互分析")
    net_effect: Dict[str, Any] = Field(default_factory=dict, description="净效应分析")
    affected_industries: List[str] = Field(default_factory=list, description="受影响行业汇总")
    combined_signals: List[Dict[str, Any]] = Field(default_factory=list, description="组合信号")
    risk_opportunities: List[Dict[str, Any]] = Field(default_factory=list, description="风险与机会识别")


class ComparativeAnalysis(BaseModel):
    """对比分析结果"""
    event_a_summary: str = Field(..., description="事件A摘要")
    event_b_summary: str = Field(..., description="事件B摘要")
    conflicting_industries: List[Dict[str, Any]] = Field(default_factory=list, description="冲突行业")
    synergistic_industries: List[Dict[str, Any]] = Field(default_factory=list, description="协同行业")
    neutral_industries: List[str] = Field(default_factory=list, description="中性行业")
    recommendation: str = Field(..., description="投资建议")


class MultiEventAnalyzeResponse(BaseModel):
    """多事件组合分析响应"""
    success: bool
    event_count: int = Field(..., description="分析的事件数量")
    strategy: str = Field(..., description="使用的分析策略")
    combined_analysis: Optional[EventCombinationAnalysis] = None
    comparative_analysis: Optional[ComparativeAnalysis] = None
    individual_results: List[FullAnalysisResult] = Field(default_factory=list, description="各事件单独分析结果")
    error: Optional[str] = None
    cached: bool = False
