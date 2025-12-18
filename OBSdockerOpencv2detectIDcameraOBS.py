import cv2

for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        print("Camera ID:", i)
        cap.release()

# Camera ID: 0
# Camera ID: 1