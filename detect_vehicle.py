from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from utils import bbox_to_ints
from config import CONF_THRESHOLD


class VehicleDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.tracker = DeepSort(max_age=30, n_init=3, nn_budget=100)

    def detect_and_track(self, frame):
        detections = []

        results = self.model(frame)[0]
        for box in results.boxes:
            x1, y1, x2, y2 = bbox_to_ints(box.xyxy)
            conf = float(box.conf[0])
            if conf < CONF_THRESHOLD:
                continue
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, None))

        tracks = self.tracker.update_tracks(detections, frame=frame)

        tracked_cars = []
        for t in tracks:
            if not t.is_confirmed():
                continue
            x1, y1, x2, y2 = map(int, t.to_ltrb())
            tracked_cars.append((t.track_id, x1, y1, x2, y2))

        return tracked_cars
