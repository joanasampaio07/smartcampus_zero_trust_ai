from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import Request, HTTPException

# Limitador local apenas para execução single-process de desenvolvimento.
_events = defaultdict(deque)
_lock = Lock()
async def rate_limit(request: Request, limit=60, window=60):
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    with _lock:
        q = _events[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Muitas requisições. Tente novamente.")
        q.append(now)
