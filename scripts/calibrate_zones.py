"""
Calibrate zone coordinates bằng cách kéo chuột trực tiếp trên frame.

Cách dùng:
    python scripts/calibrate_zones.py
    python scripts/calibrate_zones.py /path/to/video.mp4

Thứ tự vẽ:
    1. OUTSIDE  (đỏ)  — vùng ngoài
    2. BUFFER   (vàng) — bước đệm
    3. INSIDE   (xanh lá) — vùng trong

Sau khi vẽ xong 3 zone, nhấn:
    S → lưu vào .env và thoát
    R → vẽ lại từ đầu
    Q → thoát không lưu
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ZONE_ORDER = [
    ("OUTSIDE_ZONE", (0, 0, 255),   "OUTSIDE (do)"),
    ("BUFFER_ZONE",  (0, 255, 255), "BUFFER  (vang)"),
    ("INSIDE_ZONE",  (0, 255, 0),   "INSIDE  (xanh la)"),
]

ENV_FILE = Path(__file__).parent.parent / ".env"

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

drawing = False
ix, iy = -1, -1
current_rect = None          # (x1,y1,x2,y2) đang kéo
finished_zones: list[tuple[str, tuple, str, tuple]] = []   # (key, color, label, rect)
base_frame = None            # frame gốc không vẽ

# ---------------------------------------------------------------------------
# Mouse callback
# ---------------------------------------------------------------------------

def mouse_cb(event, x, y, flags, param):
    global drawing, ix, iy, current_rect

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
        current_rect = None

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        current_rect = (min(ix, x), min(iy, y), max(ix, x), max(iy, y))

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        current_rect = (min(ix, x), min(iy, y), max(ix, x), max(iy, y))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def draw_all(frame: np.ndarray) -> np.ndarray:
    """Vẽ tất cả zone đã hoàn thành + zone đang kéo lên frame."""
    out = frame.copy()
    for _, color, label, rect in finished_zones:
        x1, y1, x2, y2 = rect
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, label, (x1 + 4, y1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return out


def draw_active(frame: np.ndarray, color: tuple) -> np.ndarray:
    """Vẽ rect đang kéo."""
    out = frame.copy()
    if current_rect:
        x1, y1, x2, y2 = current_rect
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
    return out


def overlay_instructions(frame: np.ndarray, step: int) -> np.ndarray:
    key, color, label = ZONE_ORDER[step]
    lines = [
        f"Buoc {step + 1}/3: Ve {label}",
        "Keo chuot trai de ve zone",
        "R = ve lai  |  Q = thoat",
    ]
    out = frame.copy()
    for i, line in enumerate(lines):
        cv2.putText(out, line, (10, 28 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    return out


def update_env(zones: dict[str, tuple]):
    """Ghi tọa độ vào .env (tạo nếu chưa có)."""
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
    else:
        lines = []

    keys_to_update = set(zones.keys())
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in keys_to_update:
            x1, y1, x2, y2 = zones[key]
            new_lines.append(f"{key}={x1},{y1},{x2},{y2}")
            keys_to_update.discard(key)
        else:
            new_lines.append(line)

    # Thêm key chưa có
    for key in keys_to_update:
        x1, y1, x2, y2 = zones[key]
        new_lines.append(f"{key}={x1},{y1},{x2},{y2}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    print(f"\n✅ Đã lưu vào {ENV_FILE}")
    for key, rect in zones.items():
        print(f"   {key}={rect[0]},{rect[1]},{rect[2]},{rect[3]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global base_frame, finished_zones, current_rect, drawing

    # Mở nguồn video
    source = sys.argv[1] if len(sys.argv) > 1 else os.getenv("CAMERA_SOURCE", "0")
    try:
        source = int(source)
    except ValueError:
        pass

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"❌  Không mở được nguồn: {source}")
        sys.exit(1)

    ret, base_frame = cap.read()
    cap.release()
    if not ret:
        print("❌  Không đọc được frame đầu tiên")
        sys.exit(1)

    print("=== Calibrate Zones ===")
    print("Vẽ lần lượt: OUTSIDE → BUFFER → INSIDE")
    print("Nhấn S sau khi vẽ xong 3 zone để lưu\n")

    cv2.namedWindow("Calibrate Zones")
    cv2.setMouseCallback("Calibrate Zones", mouse_cb)

    step = 0
    finished_zones = []

    while True:
        done_frame = draw_all(base_frame)

        if step < len(ZONE_ORDER):
            key, color, label = ZONE_ORDER[step]
            display = overlay_instructions(done_frame, step)
            if current_rect and drawing:
                display = draw_active(display, color)
            elif current_rect and not drawing:
                # Hiển thị preview rect vừa kéo xong
                x1, y1, x2, y2 = current_rect
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        else:
            # Cả 3 zone xong
            display = done_frame.copy()
            cv2.putText(display, "Xong! S = luu  |  R = ve lai  |  Q = thoat",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Calibrate Zones", display)
        k = cv2.waitKey(20) & 0xFF

        # Xác nhận rect hiện tại khi nhả chuột
        if not drawing and current_rect and step < len(ZONE_ORDER):
            w = current_rect[2] - current_rect[0]
            h = current_rect[3] - current_rect[1]
            if w > 10 and h > 10:
                key_name, color, label = ZONE_ORDER[step]
                finished_zones.append((key_name, color, label, current_rect))
                print(f"  ✔ {label}: {current_rect}")
                current_rect = None
                step += 1

        if k == ord('s') or k == ord('S'):
            if len(finished_zones) == 3:
                zones = {z[0]: z[3] for z in finished_zones}
                update_env(zones)
                break
            else:
                print(f"⚠️  Mới vẽ {len(finished_zones)}/3 zone")

        elif k == ord('r') or k == ord('R'):
            finished_zones = []
            current_rect = None
            drawing = False
            step = 0
            print("↩  Vẽ lại từ đầu")

        elif k == ord('q') or k == ord('Q'):
            print("Thoát không lưu.")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
