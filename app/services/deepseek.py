from __future__ import annotations

import httpx

from app.config import get_settings


async def explain(summary: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return {
            "source": "本地演示解释器",
            "answer": f"已根据实时聚合指标完成分析：{summary}。建议先核验异常事件的成交量、历史均值和持续时间，再决定是否升级风险等级。配置 DEEPSEEK_API_KEY 后可获得 DeepSeek 的定制解读。",
        }
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": "你是金融和电商风控分析师。只基于给定摘要，用中文给出简洁、审慎的解释和建议。"},
            {"role": "user", "content": summary},
        ],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{settings.deepseek_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
    return {"source": "DeepSeek", "answer": response.json()["choices"][0]["message"]["content"]}

