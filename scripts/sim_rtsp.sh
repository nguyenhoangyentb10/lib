#!/usr/bin/env bash
# Giả lập RTSP stream dùng MediaMTX + FFmpeg
#
# Cách dùng:
#   ./scripts/sim_rtsp.sh                    # test pattern (không cần video)
#   ./scripts/sim_rtsp.sh /path/to/video.mp4 # stream video file (lặp vô hạn)
#
# Sau khi chạy script này:
#   CAMERA_SOURCE=rtsp://localhost:8554/live trong .env
#   rồi chạy: uvicorn app.main:app

set -e

MEDIAMTX_BIN="${MEDIAMTX_BIN:-./mediamtx}"
VIDEO_FILE="${1:-}"
RTSP_URL="rtsp://localhost:8554/live"

# ---------- kiểm tra mediamtx ----------
if [ ! -f "$MEDIAMTX_BIN" ]; then
    echo "❌  Chưa có mediamtx binary."
    echo ""
    echo "    Tải tại: https://github.com/bluenviron/mediamtx/releases"
    echo "    Chọn file: mediamtx_vX.X.X_linux_amd64.tar.gz"
    echo "    Giải nén rồi đặt binary vào thư mục gốc project (cạnh file này)"
    echo ""
    echo "    Hoặc chỉ định đường dẫn:"
    echo "    MEDIAMTX_BIN=/usr/local/bin/mediamtx ./scripts/sim_rtsp.sh"
    exit 1
fi

# ---------- kiểm tra ffmpeg ----------
if ! command -v ffmpeg &>/dev/null; then
    echo "❌  ffmpeg không tìm thấy. Cài: sudo apt install ffmpeg"
    exit 1
fi

# ---------- start MediaMTX ----------
echo "▶  Khởi động MediaMTX RTSP server tại :8554 ..."
"$MEDIAMTX_BIN" mediamtx.yml &
MEDIAMTX_PID=$!
trap "echo; echo '⏹  Dừng MediaMTX'; kill $MEDIAMTX_PID 2>/dev/null" EXIT INT TERM
sleep 1

# ---------- FFmpeg push ----------
if [ -n "$VIDEO_FILE" ] && [ -f "$VIDEO_FILE" ]; then
    echo "▶  Streaming file: $VIDEO_FILE  →  $RTSP_URL  (lặp vô hạn)"
    ffmpeg \
        -re \
        -stream_loop -1 \
        -i "$VIDEO_FILE" \
        -an \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -b:v 2M \
        -f rtsp "$RTSP_URL"
else
    echo "⚠️   Không có video file — dùng test pattern (YOLO sẽ không detect người)"
    echo "    Để stream video thật: ./scripts/sim_rtsp.sh /path/to/people.mp4"
    echo ""
    echo "▶  Streaming test pattern  →  $RTSP_URL"
    ffmpeg \
        -re \
        -f lavfi \
        -i "testsrc2=size=1280x720:rate=25" \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -f rtsp "$RTSP_URL"
fi
