import cv2
import subprocess
import sys

CAMERA_INDEX = 0
RTSP_URL = "rtsp://127.0.0.1:8554/cam"

# Mở camera
cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    print("❌ Không mở được camera")
    sys.exit(1)

# Lấy thông số camera
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25

# FFmpeg phát RTSP
ffmpeg_cmd = [
    "ffmpeg",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{width}x{height}",
    "-r", str(fps),
    "-i", "-",
    "-an",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-f", "rtsp",
    RTSP_URL
]

process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

print("✅ Đang phát RTSP:", RTSP_URL)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    process.stdin.write(frame.tobytes())

cap.release()
process.stdin.close()
process.wait()
