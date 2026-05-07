"""
诊断脚本 - 检查后端服务和 LLM API 连接
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.services.llm_client import get_llm


async def test_backend_health():
    """测试后端健康状态"""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health", timeout=5.0)
            if response.status_code == 200:
                print("✅ 后端服务运行正常")
                return True
            else:
                print(f"❌ 后端服务异常: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ 无法连接后端服务: {e}")
        return False


async def test_llm_connection():
    """测试 LLM API 连接"""
    print(f"\n📋 当前配置:")
    print(f"  Provider: {settings.LLM_PROVIDER}")
    print(f"  Model: {getattr(settings, f'{settings.LLM_PROVIDER.upper()}_MODEL', 'N/A')}")

    try:
        llm = get_llm()
        print(f"\n🔄 测试 LLM API 连接...")

        # 简单的测试请求
        result = await llm.complete(
            prompt="请回复: API连接成功",
            max_tokens=50
        )

        print(f"✅ LLM API 连接成功")
        print(f"   响应: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ LLM API 连接失败: {e}")
        print(f"\n💡 可能的原因:")
        print(f"   1. API Key 无效或过期")
        print(f"   2. 模型名称错误")
        print(f"   3. 网络连接问题")
        print(f"   4. API 配额用尽")
        return False


def check_env_file():
    """检查环境变量文件"""
    print("\n📁 检查环境变量...")

    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        print(f"✅ 找到 .env 文件: {env_path}")
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 不打印敏感信息
            lines = content.strip().split('\n')
            for line in lines:
                if '=' in line:
                    key = line.split('=')[0]
                    if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
                        print(f"   {key}=***已配置***")
                    else:
                        print(f"   {line}")
    else:
        print(f"⚠️  未找到 .env 文件")


async def main():
    print("=" * 60)
    print("事件驱动交易分析系统 - 诊断工具")
    print("=" * 60)

    # 1. 检查环境变量
    check_env_file()

    # 2. 测试后端服务
    print("\n" + "=" * 60)
    backend_ok = await test_backend_health()

    # 3. 测试 LLM 连接
    print("\n" + "=" * 60)
    llm_ok = await test_llm_connection()

    # 总结
    print("\n" + "=" * 60)
    print("诊断结果:")
    print(f"  后端服务: {'✅ 正常' if backend_ok else '❌ 异常'}")
    print(f"  LLM API:  {'✅ 正常' if llm_ok else '❌ 异常'}")

    if backend_ok and llm_ok:
        print("\n✅ 系统状态良好，应该可以正常使用")
    else:
        print("\n⚠️  发现问题，请根据上述提示修复")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())