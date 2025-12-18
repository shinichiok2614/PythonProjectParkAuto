import cv2
import pyvirtualcam

cap = cv2.VideoCapture(0)

with pyvirtualcam.Camera(width=640, height=480, fps=30) as cam:
    print("Backend:", cam.backend)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        cam.send(frame_rgb)
        cam.sleep_until_next_frame()
