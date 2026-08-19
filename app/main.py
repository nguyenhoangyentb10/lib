import asyncio
import os
import threading
from contextlib import asynccontextmanager

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
        return raw  # RTSP URL hoặc file path


camera      = CameraReader(source=_parse_source(os.getenv("CAMERA_SOURCE", "0")))
detector    = Detector(model_path=os.getenv("MODEL_PATH", "models/yolov8n.pt"))
tracker     = Tracker(detector)
zone_counter = ZoneCounter()

_stop_event = threading.Event()


# ---------------------------------------------------------------------------
# B2–B5: vòng lặp xử lý chạy trong thread nền
# ---------------------------------------------------------------------------

def processing_loop():
    import cv2

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
        print(f"\rPeople inside: {state.get()}   ", end="", flush=True)

        # Tuỳ chọn: hiển thị frame debug
        if os.getenv("SHOW_WINDOW", "0") == "1":
            zone_counter.draw_zones(frame)
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
