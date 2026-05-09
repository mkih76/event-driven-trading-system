"""
FastAPI 应用入口
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import json

from .config import settings
from .schemas.models import AnalyzeRequest, AnalyzeResponse, FullAnalysisResult, MultiEventAnalyzeRequest, MultiEventAnalyzeResponse
from .services.analysis import get_analysis_service, AnalysisDegradation, verify_api_key
from fastapi import Depends
import os
import pathlib

# 确保数据库目录存在
db_path = pathlib.Path(settings.DATABASE_URL.replace("sqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="事件驱动交易分析系统 - 通过大语言模型分析国际事件对产业链的影响"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_event(
    request: AnalyzeRequest,
    _auth: str = Depends(verify_api_key)
):
    """
    分析事件并生成投资信号

    输入事件标题和内容，系统会：
    1. 理解事件类型和情绪
    2. 推理产业链传导路径
    3. 生成个股交易信号

    如启用 API 认证，请在请求头中添加 X-API-Key
    """
    # API Key 验证会在路由层面完成，这里验证标记
    try:
        service = get_analysis_service()

        result, degradation = await service.analyze(
            title=request.title,
            content=request.content,
            use_cache=request.use_cache
        )

        return AnalyzeResponse(
            success=True,
            data=result,
            cached=degradation.is_degraded,
            degradation_message=degradation.message if degradation.is_degraded else None
        )

    except Exception as e:
        return AnalyzeResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/v1/analyze/stream")
async def analyze_event_stream(
    request: AnalyzeRequest,
    _auth: str = Depends(verify_api_key)
):
    """
    流式分析事件 - 逐步返回分析过程

    适合前端展示 LLM 推理过程

    如启用 API 认证，请在请求头中添加 X-API-Key
    """
    async def event_generator():
        service = get_analysis_service()

        # 临时增加 LLM 超时时间以适应流式请求
        original_timeout = service.llm.timeout
        service.llm.timeout = 150  # 150秒足够流式请求

        # Step 1: 事件理解
        yield f"data: {json.dumps({'step': 1, 'status': 'analyzing', 'message': '理解事件...'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            event_analysis = await service._analyze_event(request.title, request.content)
            yield f"data: {json.dumps({'step': 1, 'status': 'done', 'data': event_analysis.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 1, 'status': 'error', 'message': str(e)})}\n\n"
            return
        finally:
            service.llm.timeout = original_timeout

        # Step 2: 传导分析
        yield f"data: {json.dumps({'step': 2, 'status': 'analyzing', 'message': '分析产业链传导...'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            transmission = await service._analyze_transmission(event_analysis)
            yield f"data: {json.dumps({'step': 2, 'status': 'done', 'data': transmission.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 2, 'status': 'error', 'message': str(e)})}\n\n"
            return

        # Step 3: 信号生成
        yield f"data: {json.dumps({'step': 3, 'status': 'analyzing', 'message': '生成交易信号...'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            signals = await service._generate_signals(event_analysis, transmission)
            yield f"data: {json.dumps({'step': 3, 'status': 'done', 'data': [s.model_dump() for s in signals]})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 3, 'status': 'error', 'message': str(e)})}\n\n"
            return

        # 完成
        yield f"data: {json.dumps({'step': 99, 'status': 'done', 'message': '分析完成'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.get("/api/v1/examples")
async def get_example_events():
    """获取示例事件列表"""
    return [
        {
            "title": "美国与伊朗爆发军事冲突，伊朗封锁霍尔木兹海峡",
            "content": "据报道，美国和伊朗在波斯湾地区发生军事冲突，伊朗宣布封锁霍尔木兹海峡，禁止所有油轮通行。",
            "category": "地缘政治"
        },
        {
            "title": "OPEC+宣布大幅减产原油，每天减少500万桶",
            "content": "石油输出国组织及其盟国(OPEC+)召开紧急会议，决定从下月开始大幅减产原油，日产量减少500万桶。",
            "category": "大宗商品"
        },
        {
            "title": "荷兰宣布禁止光刻机出口到中国",
            "content": "荷兰政府宣布扩大光刻机出口管制范围，禁止ASML向中国出口更先进的DUV光刻机设备。",
            "category": "科技制裁"
        },
        {
            "title": "苏伊士运河因货轮搁浅再次堵塞",
            "content": "一艘大型集装箱货轮在苏伊士运河搁浅，导致运河双向交通堵塞，数十艘货船滞留。",
            "category": "航运"
        },
        {
            "title": "欧盟通过碳中和法案，大幅提高碳排放成本",
            "content": "欧洲议会通过新的碳中和法案，大幅提高碳排放配额价格，并扩大碳市场覆盖范围。",
            "category": "政策"
        }
    ]


@app.get("/api/v1/stats")
async def get_stats():
    """获取系统统计"""
    service = get_analysis_service()
    return {
        "cache_size": len(service._cache),
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER == "claude" else settings.OPENAI_MODEL
    }


@app.get("/api/v1/knowledge-graph/stats")
async def get_knowledge_graph_stats():
    """获取知识图谱统计（包含动态学习结果）"""
    from .services.causal_reasoning import get_industry_graph, get_dynamic_learner

    kg = get_industry_graph()
    learner = get_dynamic_learner()

    return {
        "base_graph": kg.get_statistics(),
        "dynamic_learning": learner.get_statistics(),
        "potential_nodes": learner.get_potential_nodes()
    }


@app.get("/api/v1/knowledge-graph/relationships")
async def get_dynamic_relationships(min_confidence: float = 0.5):
    """获取动态学习的关系"""
    from .services.causal_reasoning import get_dynamic_learner

    learner = get_dynamic_learner()
    return {
        "relationships": learner.get_dynamic_relationships(min_confidence)
    }


@app.post("/api/v1/knowledge-graph/merge")
async def merge_knowledge_graph():
    """将动态学习结果合并到基础图谱"""
    from .services.causal_reasoning import get_dynamic_learner

    learner = get_dynamic_learner()
    merged_path = learner.merge_to_graph()

    return {
        "success": bool(merged_path),
        "merged_path": merged_path,
        "message": "图谱合并完成" if merged_path else "合并失败"
    }


@app.post("/api/v1/knowledge-graph/save")
async def save_knowledge_discoveries():
    """保存动态学习的发现"""
    from .services.causal_reasoning import get_dynamic_learner

    learner = get_dynamic_learner()
    await learner.save_discoveries()

    return {
        "success": True,
        "statistics": learner.get_statistics()
    }


@app.get("/api/v1/history/events")
async def get_learning_history():
    """获取历史事件学习统计"""
    from .services.impact_quant import EventBacktestEngine

    engine = EventBacktestEngine()
    return engine.get_statistics()


@app.get("/api/v1/network-graph")
async def get_network_graph():
    """获取网络图数据（供前端可视化使用）"""
    from .services.network_graph import get_network_graph_generator

    # 获取最近的传导分析结果来生成示例图
    service = get_analysis_service()
    if not service._cache:
        return {"nodes": [], "edges": [], "total_industries": 0, "total_edges": 0}

    # 获取最后一个分析结果
    last_result = list(service._cache.values())[-1]
    transmission = last_result.get("transmission")

    if not transmission or not transmission.get("transmission_chain"):
        return {"nodes": [], "edges": [], "total_industries": 0, "total_edges": 0}

    from .schemas.models import TransmissionChainResult
    transmission_obj = TransmissionChainResult(**transmission)

    generator = get_network_graph_generator()
    return generator.generate_json(transmission_obj)


@app.post("/admin/reload-graph")
async def reload_knowledge_graph(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    """
    管理端点：重载知识图谱配置

    通过修改 YAML 或 JSON 配置文件后，调用此端点可以热重载图谱数据。
    需要在请求头中提供 X-Admin-Key 进行鉴权。

    Headers:
        X-Admin-Key: 管理密钥（在 .env 中配置 ADMIN_KEY）

    Returns:
        重载结果统计信息
    """
    # 简单的密钥验证
    if settings.ADMIN_KEY and x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=401, detail="无效的管理密钥")

    from .services.causal_reasoning import get_industry_graph

    kg = get_industry_graph()
    success = kg.reload_graph()

    return {
        "success": success,
        "statistics": kg.get_statistics() if success else None,
        "message": "图谱重载成功" if success else "图谱重载失败"
    }


@app.get("/api/v1/vector-store/stats")
async def get_vector_store_stats():
    """
    获取向量库统计信息

    Returns:
        ChromaDB 存储统计
    """
    from .services.semantic_matcher import get_semantic_matcher

    matcher = get_semantic_matcher()
    return await matcher.get_collection_stats()


@app.post("/api/v1/vector-store/import-history")
async def import_historical_events_to_vector_store(
    force_reload: bool = False,
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """
    将历史事件批量导入向量库

    从 event_history.json 读取历史事件，计算向量后存入 ChromaDB。

    Headers:
        X-Admin-Key: 管理密钥

    Query:
        force_reload: 是否强制重新导入（默认 false，已有数据时跳过）
    """
    # 简单的密钥验证
    if settings.ADMIN_KEY and x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=401, detail="无效的管理密钥")

    from .services.semantic_matcher import get_semantic_matcher

    matcher = get_semantic_matcher()
    result = await matcher.import_historical_events(force_reload=force_reload)

    return result


@app.get("/api/v1/vector-store/search")
async def search_similar_events(
    q: str,
    event_type: str = None,
    top_k: int = 5
):
    """
    搜索相似历史事件

    Args:
        q: 搜索查询（事件标题或描述）
        event_type: 事件类型过滤（可选）
        top_k: 返回数量（默认 5）
    """
    from .services.semantic_matcher import get_semantic_matcher

    matcher = get_semantic_matcher()
    events = await matcher.search_historical_events(
        query=q,
        event_type=event_type,
        top_k=top_k
    )

    return {"results": events, "query": q, "count": len(events)}


@app.post("/api/v1/vector-store/clear")
async def clear_vector_store(
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """
    清空向量库

    Headers:
        X-Admin-Key: 管理密钥
    """
    if settings.ADMIN_KEY and x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=401, detail="无效的管理密钥")

    from .services.semantic_matcher import get_semantic_matcher

    matcher = get_semantic_matcher()
    success = await matcher.clear_all_events()

    return {"success": success, "message": "向量库已清空" if success else "清空失败"}


@app.post("/api/v1/analyze/multi-event", response_model=MultiEventAnalyzeResponse)
async def analyze_multi_events(
    request: MultiEventAnalyzeRequest,
    _auth: str = Depends(verify_api_key)
):
    """
    多事件组合分析

    支持分析多个事件的组合效应：
    - combined: 综合分析所有事件的协同效应
    - comparative: 对比分析事件的冲突与协同
    - chain: 链式分析事件的时序传导

    请求示例:
    ```json
    {
        "events": [
            {"title": "OPEC宣布减产", "content": "..."},
            {"title": "美联储加息", "content": "..."}
        ],
        "strategy": "combined"
    }
    ```
    """
    from .services.multi_event_analyzer import get_multi_event_analyzer

    try:
        analyzer = get_multi_event_analyzer()

        result = await analyzer.analyze(
            events=[e.model_dump() for e in request.events],
            strategy=request.strategy,
            use_cache=request.use_cache
        )

        return MultiEventAnalyzeResponse(
            success=True,
            event_count=len(request.events),
            strategy=request.strategy,
            combined_analysis=result.get("combined_analysis"),
            comparative_analysis=result.get("comparative_analysis"),
            individual_results=result.get("individual_results", [])
        )

    except Exception as e:
        return MultiEventAnalyzeResponse(
            success=False,
            event_count=len(request.events),
            strategy=request.strategy,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
