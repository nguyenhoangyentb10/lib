import threading


class AppState:
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.count += 1

    def decrement(self):
        with self._lock:
            self.count -= 1

    def get(self) -> int:
        with self._lock:
            return self.count

    def reset(self):
        with self._lock:
            self.count = 0


state = AppState()
