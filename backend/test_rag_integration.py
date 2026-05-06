import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

async def test():
    try:
        from app.services.rag_service import get_rag_service
        rag = get_rag_service()
        context = await rag.get_context_for_event(
            title="美伊冲突升级，油价飙升",
            content="美国对伊朗实施新制裁，布伦特原油突破90美元。",
            affected_industries=["石油", "黄金", "航运"]
        )
        print("=== 获取到的上下文 ===")
        print(context[:2000])  # 只打印前2000字符
        print("\n=== 上下文长度 ===", len(context))
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
