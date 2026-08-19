import asyncio
import os
import threading
from contextlib import asynccontextmanager

import cv2
import supervision as sv
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

load_dotenv()

from app.camera import CameraReader
from app.detector import Detector
from app.tracker import Tracker
from app.zone import ZoneCounter
from app.state import state

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

def _parse_source(raw: str):
    try:
        return int(raw)
    except ValueError:
        return raw


camera       = CameraReader(source=_parse_source(os.getenv("CAMERA_SOURCE", "0")))
detector     = Detector(model_path=os.getenv("MODEL_PATH", "models/yolov8n.pt"))
tracker      = Tracker(detector)
zone_counter = ZoneCounter()

_stop_event  = threading.Event()
_show_window = os.getenv("SHOW_WINDOW", "0") == "1"

# Supervision annotators (khởi tạo 1 lần)
_box_annotator   = sv.BoxAnnotator(thickness=2)
_label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _annotate(frame, detections: sv.Detections) -> None:
    """Vẽ bbox + label ID:zone lên frame (in-place)."""
    labels = []
    for tid in detections.tracker_id:
        tid = int(tid)
        zone = zone_counter._id_zone.get(tid) or "?"
        labels.append(f"ID:{tid} {zone}")

    annotated = _box_annotator.annotate(scene=frame, detections=detections)
    annotated = _label_annotator.annotate(scene=annotated, detections=detections, labels=labels)
    frame[:] = annotated


def _draw_count(frame, count: int) -> None:
    """Vẽ số đếm góc trên-trái."""
    cv2.rectangle(frame, (0, 0), (220, 40), (0, 0, 0), -1)
    cv2.putText(frame, f"Inside: {count}", (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)


# ---------------------------------------------------------------------------
# B2–B5: vòng lặp xử lý chạy trong thread nền
# ---------------------------------------------------------------------------

def processing_loop():
    while not _stop_event.is_set():
        frame = camera.get_frame()
        if frame is None:
            continue

        # B3 + B4: detect + track
        detections = tracker.track(frame)

        # B5: cập nhật zone state
        if detections is not None:
            zone_counter.update(detections)

        # B6: terminal realtime
        count = state.get()
        print(f"\rPeople inside: {count}   ", end="", flush=True)

        # Hiển thị frame debug
        if _show_window:
            zone_counter.draw_zones(frame)
            if detections is not None:
                _annotate(frame, detections)
            _draw_count(frame, count)
            cv2.imshow("People Counter", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                _stop_event.set()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    camera.start()
    t = threading.Thread(target=processing_loop, daemon=True, name="processing-loop")
    t.start()

    yield

    # shutdown
    _stop_event.set()
    camera.stop()
    print("\nStopped.")


app = FastAPI(title="People Counter", lifespan=lifespan)


@app.get("/count")
def get_count():
    """Trả về số người đang trong vùng (snapshot)."""
    return {"count": state.get()}


@app.websocket("/ws/count")
async def websocket_count(websocket: WebSocket):
    """Push số người realtime mỗi giây."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"count": state.get()})
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
