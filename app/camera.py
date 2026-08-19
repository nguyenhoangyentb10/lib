import cv2
import threading
from typing import Optional
import numpy as np


class CameraReader:
    """B1+B2: mở camera, liên tục đọc frame mới nhất trong thread nền."""

    def __init__(self, source):
        self.source = source
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="camera-reader")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def _read_loop(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {self.source}")

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                with self._lock:
                    self._frame = frame
        finally:
            cap.release()
