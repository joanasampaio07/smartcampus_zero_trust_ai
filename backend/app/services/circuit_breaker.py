import time
from app.core.config import settings


class CircuitBreaker:
    """Circuit breaker with optional Redis backing and in-memory fallback."""

    def __init__(self, name: str = "gemini", failure_threshold: int = 3, recovery_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._opened_at: float | None = None
        self._redis = None
        if settings.redis_url:
            try:
                import redis
                self._redis = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
            except Exception:
                self._redis = None

    def state(self) -> str:
        if self._redis:
            try:
                opened_at = self._redis.get(f"cb:{self.name}:opened_at")
                if not opened_at:
                    return "CLOSED"
                if time.time() - float(opened_at) >= self.recovery_timeout:
                    return "HALF_OPEN"
                return "OPEN"
            except Exception:
                pass
        if self._opened_at is None:
            return "CLOSED"
        if time.time() - self._opened_at >= self.recovery_timeout:
            return "HALF_OPEN"
        return "OPEN"

    def allow_request(self) -> bool:
        return self.state() != "OPEN"

    def record_success(self) -> None:
        if self._redis:
            try:
                self._redis.delete(f"cb:{self.name}:failures", f"cb:{self.name}:opened_at")
                return
            except Exception:
                pass
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        if self._redis:
            try:
                failures = self._redis.incr(f"cb:{self.name}:failures")
                if failures >= self.failure_threshold:
                    self._redis.set(f"cb:{self.name}:opened_at", str(time.time()), ex=self.recovery_timeout * 2)
                return
            except Exception:
                pass
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.time()


ai_circuit_breaker = CircuitBreaker()
