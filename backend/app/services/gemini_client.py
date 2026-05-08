import os
import json
from typing import Optional, Type, TypeVar, Any
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class GeminiClient:
    """Google Gemini API 客户端"""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def is_available(self) -> bool:
        return True

    def _make_request(self, endpoint: str, data: dict) -> dict:
        import urllib.request
        import urllib.error

        url = f"{self.base_url}/{endpoint}?key={self.api_key}"
        json_data = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Gemini API error: {e.code} - {error_body}")

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        max_tokens: int = 8192,
        **kwargs
    ) -> Any:
        """调用 Gemini 生成回复"""

        contents = []
        if system:
            contents.append({
                "role": "model",
                "parts": [{"text": system}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        data = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.9),
            }
        }

        response = self._make_request(
            f"models/{self.model}:generateContent",
            data
        )

        text = response["candidates"][0]["content"]["parts"][0]["text"]

        if response_model:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")
            return response_model(**data)

        return text

    async def batch_complete(self, prompts: list[str], **kwargs) -> list[str]:
        """批量调用 Gemini"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(result)
        return results
