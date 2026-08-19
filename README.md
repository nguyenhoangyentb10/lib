# People Counter

Đếm người ra/vào realtime qua camera, sử dụng YOLOv8 + ByteTrack + FastAPI.

---

## Cách hoạt động

```
Camera → đọc frame → YOLOv8 detect → ByteTrack gán ID → kiểm tra zone → đếm in/out
```

Mỗi người được theo dõi qua **3 vùng** (cấu hình bằng tọa độ rect):

```
┌─────────────────────┐
│      OUTSIDE        │
├─────────────────────┤  ← ranh giới
│      BUFFER         │  ← bước đệm (tránh đếm nhầm)
├─────────────────────┤  ← ranh giới
│      INSIDE         │
└─────────────────────┘
```

| Hướng đi                          | Kết quả     |
|-----------------------------------|-------------|
| outside → buffer → inside         | `count + 1` |
| inside  → buffer → outside        | `count - 1` |
| Nhảy thẳng (không qua buffer)     | Bỏ qua      |

---

## Cấu trúc project

```
people-counter/
├── app/
│   ├── main.py       # FastAPI: startup, GET /count, WebSocket /ws/count
│   ├── camera.py     # Đọc frame từ camera trong thread nền
│   ├── detector.py   # YOLOv8 load model, detect người
│   ├── tracker.py    # ByteTrack, giữ ID xuyên suốt frame
│   ├── zone.py       # PolygonZone + state machine đếm in/out
│   └── state.py      # Biến đếm dùng chung (thread-safe)
├── models/
│   └── yolov8n.pt    # Đặt model weights vào đây
├── tests/
│   └── test_zone.py  # Unit test state machine (không cần GPU)
├── requirements.txt
└── .env.example
```

---

## Cài đặt

**Yêu cầu:** Python 3.10+, pip

```bash
cd people-counter

# Tạo môi trường ảo
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Cài thư viện
pip install -r requirements.txt
```

Model weights `yolov8n.pt` sẽ tự tải về lần đầu chạy (cần internet).  
Hoặc tải thủ công và đặt vào `models/yolov8n.pt`.

---

## Cấu hình

```bash
cp .env.example .env
```

Chỉnh `.env` theo thực tế:

| Biến            | Mô tả                                           | Mặc định          |
|-----------------|-------------------------------------------------|-------------------|
| `CAMERA_SOURCE` | Index webcam (`0`), RTSP URL, hoặc path video   | `0`               |
| `MODEL_PATH`    | Đường dẫn model YOLOv8                          | `models/yolov8n.pt` |
| `INSIDE_ZONE`   | Tọa độ vùng TRONG — `x1,y1,x2,y2`              | `200,300,600,500` |
| `BUFFER_ZONE`   | Tọa độ bước đệm — `x1,y1,x2,y2`               | `200,220,600,300` |
| `OUTSIDE_ZONE`  | Tọa độ vùng NGOÀI — `x1,y1,x2,y2`             | `200,100,600,220` |
| `SHOW_WINDOW`   | `1` để bật cửa sổ OpenCV debug                 | `0`               |
| `HOST`          | Bind host FastAPI                               | `0.0.0.0`         |
| `PORT`          | Port FastAPI                                    | `8000`            |

> **Tip:** Dùng `SHOW_WINDOW=1` lần đầu để xem vị trí zone trên frame thật, rồi chỉnh tọa độ cho khớp.

---

## Chạy

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminal sẽ in realtime:

```
People inside: 3
```

---

## API

### `GET /count`

Snapshot số người hiện tại.

```bash
curl http://localhost:8000/count
# {"count": 3}
```

### `WebSocket /ws/count`

Push số người mỗi giây.

```js
const ws = new WebSocket("ws://localhost:8000/ws/count");
ws.onmessage = (e) => console.log(JSON.parse(e.data)); // {count: 3}
```

---

## Test

Unit test state machine — không cần camera, không cần GPU:

```bash
pytest tests/ -v
```

Các test case:

| Test                          | Kiểm tra                                  |
|-------------------------------|-------------------------------------------|
| `test_enter_increments_count` | outside→buffer→inside tăng count          |
| `test_exit_decrements_count`  | inside→buffer→outside giảm count          |
| `test_skip_buffer_no_count`   | Nhảy thẳng không qua buffer → không đếm  |
| `test_two_people_enter`       | 2 người vào → count = 2                   |
| `test_same_zone_no_double_count` | Gọi lại cùng zone không đếm thêm      |
| `test_enter_then_exit`        | Vào rồi ra → net count = 0               |

---

## Stack

| Thư viện       | Vai trò                        |
|----------------|--------------------------------|
| `ultralytics`  | YOLOv8 detect + ByteTrack      |
| `supervision`  | PolygonZone, annotation frame  |
| `opencv-python`| Đọc camera, xử lý ảnh         |
| `fastapi`      | REST API + WebSocket           |
| `uvicorn`      | ASGI server                    |
| `python-dotenv`| Đọc biến môi trường từ `.env`  |
