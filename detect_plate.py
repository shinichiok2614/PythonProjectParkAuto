from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer
from utils import bbox_to_ints
from config import CONF_THRESHOLD
import cv2


class PlateDetector:
    def __init__(self, model_path, ocr_model):
        self.model = YOLO(model_path)
        self.ocr = LicensePlateRecognizer(ocr_model)

    def detect(self, frame):
        plates = []
        results = self.model(frame)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = bbox_to_ints(box.xyxy)
            conf = float(box.conf[0])
            if conf < CONF_THRESHOLD:
                continue
            plates.append((x1, y1, x2, y2))

        return plates

    def recognize(self, plate_crop):
        try:
            rgb = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2RGB)
            text = self.ocr.run(rgb)
            return "".join(text) if isinstance(text, list) else text
        except Exception:
            return None
