import numpy as np
import supervision as sv
from ultralytics import YOLO


class Detector:
    """B3: Load YOLOv8, nhận diện người (class 0) trong một frame."""

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """Chạy inference thuần (không tracking) — dùng khi không cần ID."""
        results = self.model(frame, classes=[0], verbose=False)
        return sv.Detections.from_ultralytics(results[0])
