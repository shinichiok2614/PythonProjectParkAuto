import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # thử 0,1,2

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("OBS Virtual Cam", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
