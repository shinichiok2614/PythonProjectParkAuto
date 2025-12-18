import cv2
import pyvirtualcam

cap = cv2.VideoCapture(0)

with pyvirtualcam.Camera(
    width=640,
    height=480,
    fps=30
) as cam:
    print("Using backend:", cam.backend)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # OpenCV là BGR → pyvirtualcam Windows tự hiểu
        cam.send(frame)
        cam.sleep_until_next_frame()
