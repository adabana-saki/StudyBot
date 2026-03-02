"""レート制限ミドルウェア"""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# デフォルト: 1分あたり60リクエスト
DEFAULT_RATE_LIMIT = 60
DEFAULT_WINDOW = 60  # 秒


class RateLimitMiddleware(BaseHTTPMiddleware):
    """シンプルなインメモリレート制限"""

    # 信頼するプロキシIP（Docker内部ネットワーク等）
    TRUSTED_PROXIES = {"127.0.0.1", "::1", "172.16.0.0/12", "10.0.0.0/8"}

    def __init__(
        self,
        app,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self._requests: dict[str, list[float]] = defaultdict(list)
        from api.config import settings

        self._allowed_origins = {settings.WEB_BASE_URL}

    def _is_trusted_proxy(self, ip: str) -> bool:
        """信頼するプロキシかどうか判定"""
        import ipaddress

        try:
            addr = ipaddress.ip_address(ip)
            for network in self.TRUSTED_PROXIES:
                if "/" in network:
                    if addr in ipaddress.ip_network(network, strict=False):
                        return True
                elif ip == network:
                    return True
        except ValueError:
            return False
        return False

    def _get_client_key(self, request: Request) -> str:
        """クライアント識別キー（信頼プロキシ経由のみX-Forwarded-Forを使用）"""
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded and self._is_trusted_proxy(client_ip):
            return forwarded.split(",")[0].strip()
        return client_ip

    def _clean_old_requests(self, key: str, now: float) -> None:
        """古いリクエスト記録を削除"""
        cutoff = now - self.window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next) -> Response:
        # ヘルスチェック・OPTIONSプリフライトはスキップ
        if request.url.path in ("/health", "/") or request.method == "OPTIONS":
            return await call_next(request)

        key = self._get_client_key(request)
        now = time.time()

        self._clean_old_requests(key, now)

        if len(self._requests[key]) >= self.rate_limit:
            logger.warning(f"レート制限: {key}")
            response = Response(
                content='{"detail":"リクエストが多すぎます。しばらく待ってからお試しください。"}',
                status_code=429,
                media_type="application/json",
            )
            response.headers["Retry-After"] = str(self.window)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            # CORSヘッダーを付与（CORSMiddlewareがResponseオブジェクトを処理できない場合の保険）
            origin = request.headers.get("origin", "")
            if origin in self._allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Vary"] = "Origin"
            return response

        self._requests[key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(self.rate_limit - len(self._requests[key]))
        return response
