import numpy as np
import supervision as sv
from app.detector import Detector


class Tracker:
    """B4: ByteTrack — gán và giữ ID xuyên suốt các frame."""

    def __init__(self, detector: Detector):
        # Tái dùng model đã load từ Detector, tránh load 2 lần
        self._model = detector.model

    def track(self, frame: np.ndarray) -> sv.Detections | None:
        """Trả về sv.Detections kèm tracker_id, hoặc None nếu không có ai."""
        results = self._model.track(
            frame,
            persist=True,       # ByteTrack giữ state giữa các lần gọi
            classes=[0],        # chỉ class person
            tracker="bytetrack.yaml",
            verbose=False,
        )
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return None
        return sv.Detections.from_ultralytics(results[0])
