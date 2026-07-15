from __future__ import annotations

import httpx

from app.config import get_settings


async def explain(summary: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return {
        "source": "本地规则引擎",
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


async def translate_review_to_chinese(text: str) -> str | None:
    """Translate a single public Olist review while retaining its original text in the UI."""
    settings = get_settings()
    if not settings.deepseek_api_key or "未留下文字" in text:
        return None
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": "将下面的电商商品评价翻译为自然、简洁的中文。只输出译文，不要补充解释。"},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{settings.deepseek_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


async def generate_operating_report(summary: str) -> dict[str, str]:
    """Generate a concise Chinese report from aggregated, non-sensitive platform metrics."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        return {
        "source": "本地报告引擎",
            "answer": f"# 实时运营与风控报告\n\n{summary}\n\n## 建议\n\n1. 优先复核高风险事件的原始订单或行情窗口。\n2. 持续观察订单金额、成交量和评论负面比例。\n3. 根据异常持续时间决定是否升级告警。",
        }
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": "你是严谨的商业运营和金融风控分析师。基于给定的聚合指标生成中文 Markdown 报告，必须包含：执行摘要、关键指标、风险事件、评论洞察、3 条可执行建议。不得编造未提供的数据；语气简洁专业。"},
            {"role": "user", "content": summary},
        ],
        "temperature": 0.25,
    }
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.post(f"{settings.deepseek_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
    return {"source": f"DeepSeek · {settings.deepseek_model}", "answer": response.json()["choices"][0]["message"]["content"]}
