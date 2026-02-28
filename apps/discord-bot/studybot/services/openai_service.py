"""共有 OpenAI API クライアント（Redisキャッシュ付き）"""

import hashlib
import logging

from studybot.config.settings import settings

logger = logging.getLogger(__name__)

_client = None
_redis = None

# キャッシュTTL: 1時間
CACHE_TTL_SECONDS = 3600


def set_redis_client(redis_client) -> None:
    """RedisClientを設定（Bot初期化時に呼び出し）"""
    global _redis
    _redis = redis_client


def _get_client():
    """OpenAI AsyncClient をシングルトンで取得"""
    global _client
    if _client is None:
        import openai

        _client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _cache_key(prompt: str, model: str, system_prompt: str) -> str:
    """キャッシュキーを生成"""
    raw = f"{model}:{system_prompt}:{prompt}"
    return f"ai_cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


async def call_openai(
    prompt: str,
    *,
    system_prompt: str = "あなたは優秀な学習アシスタントです。",
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    use_cache: bool = True,
) -> str | None:
    """OpenAI API を呼び出し。model 未指定時は settings.OPENAI_MODEL (gpt-4o-mini) を使用"""
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY が設定されていません")
        return None

    resolved_model = model or settings.OPENAI_MODEL

    # Redisキャッシュチェック（temperature=0に近い場合のみキャッシュ有効）
    cache_enabled = use_cache and _redis is not None and temperature <= 0.5
    if cache_enabled:
        key = _cache_key(prompt, resolved_model, system_prompt)
        try:
            cached = await _redis.get(key)
            if cached is not None:
                logger.debug(f"OpenAI キャッシュヒット: {key[:20]}")
                return cached
        except Exception:
            logger.debug("Redisキャッシュ読込失敗", exc_info=True)

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        result = response.choices[0].message.content

        # Redisにキャッシュ保存
        if cache_enabled and result:
            try:
                await _redis.set(key, result, ex=CACHE_TTL_SECONDS)
            except Exception:
                logger.debug("Redisキャッシュ保存失敗", exc_info=True)

        return result
    except Exception as e:
        logger.error(f"OpenAI API エラー (model={resolved_model}): {e}")
        return None
