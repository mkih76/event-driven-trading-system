"""
简化测试 - 只测试 SiliconFlow API
"""
import asyncio
import sys
import os

# 测试 SiliconFlow API
async def test_siliconflow():
    try:
        from openai import AsyncOpenAI

        # 读取环境变量
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("SILICONFLOW_API_KEY")
        model = os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3")

        print(f"API Key: {api_key[:20]}..." if api_key else "❌ 未配置 API Key")
        print(f"Model: {model}")

        if not api_key:
            print("❌ 错误: 未找到 SILICONFLOW_API_KEY")
            return False

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"
        )

        print("\n🔄 正在调用 SiliconFlow API...")

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "请回复: 测试成功"}],
            max_tokens=50
        )

        result = response.choices[0].message.content
        print(f"✅ API 调用成功!")
        print(f"响应: {result}")
        return True

    except Exception as e:
        print(f"❌ API 调用失败:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")

        # 提供具体建议
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("\n💡 建议: API Key 无效，请检查是否正确")
        elif "404" in error_msg or "not found" in error_msg:
            print("\n💡 建议: 模型名称错误，请检查模型是否可用")
        elif "timeout" in error_msg.lower():
            print("\n💡 建议: 网络超时，请检查网络连接")
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            print("\n💡 建议: API 配额用尽，请充值或等待")

        return False


if __name__ == "__main__":
    asyncio.run(test_siliconflow())