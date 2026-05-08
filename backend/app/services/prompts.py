"""
LLM Prompt 模板定义
"""

# ========== 事件分析 Prompt ==========
EVENT_ANALYSIS_PROMPT = """# 角色
你是一个专业的金融事件分析专家，擅长分析国际事件对金融市场的影响。

# 输入事件
标题: {title}
内容: {content}

# 分析任务
请仔细分析上述事件，输出JSON格式的分析结果：

{{
    "event_type": "地缘政治/政策/灾难/经济数据/财报/技术突破/其他",
    "core_entities": ["涉及的主要商品", "国家/地区", "行业"],
    "sentiment": -1.0到1.0的情绪值，-1极度利空，+1极度利好,
    "event_intensity": "高/中/低",
    "summary": "30字以内的核心事件摘要",
    "direct_impacts": [
        {{
            "industry": "直接受益/受损行业名称",
            "impact_direction": "利好/利空",
            "impact_magnitude": "高/中/低",
            "impact_score": -10到+10的影响分数
        }}
    ]
}}

# 输出要求
1. 只输出JSON，不要任何解释或前言
2. core_entities 至少列出3个相关实体
3. direct_impacts 列出2-5个直接受影响的行业
4. 考虑对大宗商品（原油、黄金、粮食等）、汇率、主要工业品的影响
"""

# ========== 产业链传导 Prompt ==========
CHAIN_TRANSMISSION_PROMPT = """# 角色
你是一个顶级的产业经济学家，精通全球供应链、产业链传导机制和金融市场。

# 事件信息
事件摘要: {event_summary}
事件类型: {event_type}
情绪: {sentiment} (负数=利空，正数=利好)

直接受影响行业:
{direct_impacts}

# 知识图谱约束（确定性骨架）
{kg_constraints}

# 传导推理任务
请参考上述知识图谱中的已知传导路径，结合你的产业经济学知识，推理完整的产业链传导路径。
1. **优先遵循图谱约束**: 如果图谱中已有明确的传导路径，应以此为基础
2. **补充跨行业联系**: 图谱未覆盖的跨行业联系（如风险偏好传导、金融属性）
3. **调整传导参数**: 根据具体事件调整传导系数和时滞

考虑以下传导类型：
1. **成本传导**: 原材料/能源涨价→中游制造→下游消费
2. **需求传导**: 终端需求变化→中游补库/去库→上游开工率
3. **替代效应**: A商品涨价→B替代品需求增加
4. **竞争格局**: 区域事件→市场份额重分配
5. **金融属性**: 避险情绪→资金流向→资产价格

# 传导系数说明
- 传导系数 0.3-0.5: 弱传导，影响较小
- 传导系数 0.5-0.7: 中等传导，关联明显
- 传导系数 0.7-1.0: 强传导，影响显著

# 滞后时间说明
- 即时: 1-3天
- 短期: 4-14天
- 中期: 15-30天
- 长期: 30天以上

# 输出JSON格式
{{
    "transmission_chain": [
        {{
            "step": 1,
            "from_industry": "上游行业",
            "to_industry": "下游行业",
            "relation_type": "成本传导/成本下降/需求增加/需求减少/供给增加/供给减少/替代效应",
            "transmission_rate": 0.0到1.0,
            "time_lag_days": 预估天数,
            "impact_magnitude": "高/中/低",
            "impact_score": -10到+10,
            "description": "用一句话描述这个传导是如何发生的"
        }}
    ],
    "affected_industries": ["所有直接或间接受影响的行业列表"],
    "investment_signals": [
        {{
            "industry": "行业名称",
            "signal": "BUY/SELL/HOLD",
            "confidence": 0到100,
            "reasoning": "给出做多或做空的理由"
        }}
    ]
}}

# 输出要求
1. 只输出JSON，不要任何解释
2. 传导链至少3步，最多8步
3. 每一步都要有清晰的传导机制描述
4. 投资信号要给出置信度和理由
5. 尽量保持与图谱约束一致，如有调整请说明原因
"""

# ========== 信号生成 Prompt ==========
SIGNAL_GENERATION_PROMPT = """# 角色
你是一个量化交易信号专家，专注于从宏观事件推导个股投资机会。

# 传导分析结果
{transmission_results}

受影响行业及信号:
{investment_signals}

# A股/港股/美股 股票池参考
{stock_pool}

# 信号生成任务
请根据传导分析结果，生成具体的个股交易信号。

# 输出JSON格式
{{
    "signals": [
        {{
            "stock_code": "股票代码（如 601857.SH 表示中国石油）",
            "stock_name": "股票名称",
            "signal_type": "BUY/SELL",
            "confidence": 0到100,
            "impact_score": -100到100,
            "chain_depth": 1到5,
            "entry_rationale": "为什么现在买入/卖出这个股票",
            "risk_factors": ["风险因素1", "风险因素2"],
            "related_stocks": ["同一产业链的其他相关股票"]
        }}
    ]
}}

# 输出要求
1. 只输出JSON，不要任何解释
2. 优先选择直接受益/受损的龙头股票
3. 考虑股票与事件的关联强度
4. 每个信号的置信度要合理（不要全是100）
5. 列出风险因素，不要盲目乐观
"""

# ========== RAG 增强分析 Prompt (含实时数据) ==========
RAG_EVENT_ANALYSIS_PROMPT = """# 角色
你是一个专业的金融事件分析专家，擅长分析国际事件对金融市场的影响。

# 输入事件
标题: {title}
内容: {content}

# 实时数据上下文 (来自 RAG 检索)
{real_time_context}

# 分析任务
请仔细分析上述事件，结合实时数据给出更准确的分析。

# 输出JSON格式:
{{
    "event_type": "地缘政治/政策/灾难/经济数据/财报/技术突破/其他",
    "core_entities": ["涉及的主要商品", "国家/地区", "行业"],
    "sentiment": -1.0到1.0的情绪值,
    "event_intensity": "高/中/低",
    "summary": "30字以内的核心事件摘要",
    "data_references": ["实时数据中与事件相关的关键信息"],
    "direct_impacts": [
        {{
            "industry": "直接受影响行业名称",
            "impact_direction": "利好/利空",
            "impact_magnitude": "高/中/低",
            "impact_score": -10到+10,
            "data_evidence": "如果有实时数据支持，引用相关数据"
        }}
    ]
}}

# 准确性要求
1. 如果实时数据与事件相关，结合数据给出更精确的分析
2. 如果新闻提及具体价格/涨幅，将这些数据纳入评估
3. 核实行业判断是否与当前市场表现一致
4. 只输出JSON，不要解释
"""

# ========== 快速分析 Prompt (简化版) ==========
QUICK_ANALYSIS_PROMPT = """# 任务
你是一个金融分析师。请分析以下事件并给出简洁的投资建议。

事件: {event}

请用JSON格式回答:
{{
    "summary": "一句话总结事件",
    "affected_sectors": ["受益行业1", "受损行业2"],
    "investment_advice": "做多X，做空Y",
    "confidence": 70,
    "reasoning": "简要理由"
}}

只输出JSON。
"""


def format_event_analysis_prompt(title: str, content: str) -> str:
    """格式化事件分析 Prompt"""
    return EVENT_ANALYSIS_PROMPT.format(title=title, content=content)


def format_rag_event_analysis_prompt(title: str, content: str, real_time_context: str) -> str:
    """格式化 RAG 增强的事件分析 Prompt"""
    return RAG_EVENT_ANALYSIS_PROMPT.format(
        title=title,
        content=content,
        real_time_context=real_time_context or "（暂无实时数据）"
    )


def format_chain_transmission_prompt(
    event_summary: str,
    event_type: str,
    sentiment: float,
    direct_impacts: str,
    kg_constraints: str = ""
) -> str:
    """格式化传导分析 Prompt"""
    if not kg_constraints:
        kg_constraints = "（暂无知识图谱约束，请基于产业经济学知识自行推理）"
    return CHAIN_TRANSMISSION_PROMPT.format(
        event_summary=event_summary,
        event_type=event_type,
        sentiment=sentiment,
        direct_impacts=direct_impacts,
        kg_constraints=kg_constraints
    )


def format_signal_generation_prompt(
    transmission_results: str,
    investment_signals: str,
    stock_pool: str = ""
) -> str:
    """格式化信号生成 Prompt"""
    if not stock_pool:
        stock_pool = """
股票池参考:
- 石油: 中国石油(601857.SH)、中国石化(600028.SH)、中海油(0883.HK)
- 化工: 万华化学(600309.SH)、巴斯夫(BASFY)
- 半导体: 台积电(TSM)、英伟达(NVDA)、中芯国际(0981.HK)
- 航运: 中远海控(601919.SH)、马士基(MAERSK)
- 航空: 中国国航(601111.SH)、美国航空(AAL)
- 能源: 隆基绿能(601012.SH)、特斯拉(TSLA)
- 黄金: 山东黄金(600547.SH)、巴里克黄金(GOLD)
"""
    return SIGNAL_GENERATION_PROMPT.format(
        transmission_results=transmission_results,
        investment_signals=investment_signals,
        stock_pool=stock_pool
    )
