"""Small in-process admission limits for expensive shared-workspace actions."""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    """Thread-safe fixed-key sliding window with no dependency on a proxy/cache."""

    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = Lock()

    def allowed(self, scope, client, limit, window_seconds):
        """Return whether this client may perform one action in the named scope."""
        if limit <= 0:
            return True
        now = monotonic()
        key = (scope, client)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def reset(self):
        """Test/support hook; production callers should let windows expire naturally."""
        with self._lock:
            self._events.clear()


limiter = SlidingWindowLimiter()
