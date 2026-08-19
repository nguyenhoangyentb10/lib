import os
import numpy as np
import supervision as sv
from app.state import state

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rect_to_polygon(env_key: str, default: str) -> np.ndarray:
    """Đọc "x1,y1,x2,y2" từ .env, chuyển thành polygon 4 đỉnh."""
    raw = os.getenv(env_key, default)
    x1, y1, x2, y2 = map(int, raw.split(","))
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])


# ---------------------------------------------------------------------------
# Zone definitions (load từ .env)
# ---------------------------------------------------------------------------

INSIDE_POLY  = _rect_to_polygon("INSIDE_ZONE",  "200,300,600,500")
BUFFER_POLY  = _rect_to_polygon("BUFFER_ZONE",  "200,220,600,300")
OUTSIDE_POLY = _rect_to_polygon("OUTSIDE_ZONE", "200,100,600,220")


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class ZoneCounter:
    """B5: Theo dõi zone của mỗi ID, đếm in/out khi qua bước đệm."""

    def __init__(self):
        self.inside_zone  = sv.PolygonZone(polygon=INSIDE_POLY)
        self.buffer_zone  = sv.PolygonZone(polygon=BUFFER_POLY)
        self.outside_zone = sv.PolygonZone(polygon=OUTSIDE_POLY)

        self._id_zone: dict[int, str | None] = {}
        self._id_buffer_from: dict[int, str | None] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: sv.Detections):
        """Gọi mỗi frame sau khi có detections với tracker_id."""
        if detections.tracker_id is None or len(detections) == 0:
            return

        inside_mask  = self.inside_zone.trigger(detections=detections)
        buffer_mask  = self.buffer_zone.trigger(detections=detections)
        outside_mask = self.outside_zone.trigger(detections=detections)

        active_ids: set[int] = set()
        for i, tid in enumerate(detections.tracker_id):
            tid = int(tid)
            active_ids.add(tid)

            if inside_mask[i]:
                zone = "inside"
            elif buffer_mask[i]:
                zone = "buffer"
            elif outside_mask[i]:
                zone = "outside"
            else:
                zone = None

            self._process(tid, zone)

        self._cleanup(active_ids)

    def process(self, tid: int, current_zone: str | None):
        """Xử lý chuyển zone cho một ID — dùng được trong unit test."""
        self._process(tid, current_zone)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _process(self, tid: int, current_zone: str | None):
        prev_zone = self._id_zone.get(tid)

        if current_zone == prev_zone:
            return

        if current_zone == "buffer":
            # Ghi nhớ từ đâu vào bước đệm
            self._id_buffer_from[tid] = prev_zone

        elif prev_zone == "buffer":
            # Rời bước đệm — kiểm tra chiều đi
            came_from = self._id_buffer_from.pop(tid, None)

            if came_from == "outside" and current_zone == "inside":
                state.increment()                          # vào trong: +1
            elif came_from == "inside" and current_zone == "outside":
                state.decrement()                          # ra ngoài: -1

        self._id_zone[tid] = current_zone

    def _cleanup(self, active_ids: set[int]):
        """Xoá state của ID không còn được track nữa.
        Nếu ID biến mất khi đang ở INSIDE → decrement (người ra ngoài không qua zone).
        """
        for tid in list(self._id_zone.keys()):
            if tid not in active_ids:
                if self._id_zone[tid] == "inside":
                    state.decrement()
                self._id_zone.pop(tid, None)
                self._id_buffer_from.pop(tid, None)

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """Vẽ 3 zone lên frame (BGR)."""
        annotators = [
            (self.inside_zone,  (0, 255, 0),   "INSIDE"),
            (self.buffer_zone,  (0, 255, 255),  "BUFFER"),
            (self.outside_zone, (0, 0, 255),    "OUTSIDE"),
        ]
        for zone, color, label in annotators:
            sv.draw_polygon(scene=frame, polygon=zone.polygon, color=sv.Color(*color[::-1]))
        return frame
