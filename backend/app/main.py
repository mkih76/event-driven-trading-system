"""
FastAPI 应用入口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import json

from .config import settings
from .schemas.models import AnalyzeRequest, AnalyzeResponse, FullAnalysisResult
from .services.analysis import get_analysis_service, AnalysisDegradation


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="事件驱动交易分析系统 - 通过大语言模型分析国际事件对产业链的影响"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
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
async def analyze_event(request: AnalyzeRequest):
    """
    分析事件并生成投资信号

    输入事件标题和内容，系统会：
    1. 理解事件类型和情绪
    2. 推理产业链传导路径
    3. 生成个股交易信号
    """
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
async def analyze_event_stream(request: AnalyzeRequest):
    """
    流式分析事件 - 逐步返回分析过程

    适合前端展示 LLM 推理过程
    """
    async def event_generator():
        service = get_analysis_service()

        # Step 1: 事件理解
        yield f"data: {json.dumps({'step': 1, 'status': 'analyzing', 'message': '理解事件...'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            event_analysis = await service._analyze_event(request.title, request.content)
            yield f"data: {json.dumps({'step': 1, 'status': 'done', 'data': event_analysis.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'step': 1, 'status': 'error', 'message': str(e)})}\n\n"
            return

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
