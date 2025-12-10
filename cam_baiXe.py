import os
import cv2
import queue
import threading
import sqlite3
import numpy as np
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from fast_plate_ocr import LicensePlateRecognizer
from PIL import Image, ImageTk

# ---------------------------
# Config
# ---------------------------
VEHICLE_MODEL_PATH = "yolov8n-vehicle.pt"
PLATE_MODEL_PATH = "license_plate_detector.pt"
OCR_MODEL_NAME = "cct-xs-v1-global-model"

SAVED_CARS = "saved_cars"
SAVED_PLATES = "saved_plates"
SAVED_FACES = "saved_faces"
DB_PATH = "plates.db"

os.makedirs(SAVED_CARS, exist_ok=True)
os.makedirs(SAVED_PLATES, exist_ok=True)
os.makedirs(SAVED_FACES, exist_ok=True)

# Load models (may be slow)
vehicle_model = YOLO(VEHICLE_MODEL_PATH)
plate_model = YOLO(PLATE_MODEL_PATH)
ocr = LicensePlateRecognizer(OCR_MODEL_NAME)
tracker = DeepSort(max_age=30, n_init=3, nn_budget=100)

# Thread-safe queue
result_queue = queue.Queue()

# ---------------------------
# Preview sizes (fixed)
# ---------------------------
CAR_W, CAR_H = 500, 300
PLATE_W, PLATE_H = 250, 150
FACE_W, FACE_H = 200, 250

# ---------------------------
# Utils
# ---------------------------
def bbox_to_ints(xy):
    try:
        coords = xy[0] if hasattr(xy[0], "__getitem__") else xy
        a = coords.cpu().numpy() if hasattr(coords, "cpu") else np.array(coords)
        x1, y1, x2, y2 = map(int, a.tolist())
        return x1, y1, x2, y2
    except Exception:
        a = np.array(xy)
        if a.size >= 4:
            x1, y1, x2, y2 = map(int, a.flatten()[:4])
            return x1, y1, x2, y2
        raise

def centroid(box):
    x1, y1, x2, y2 = box
    return ((x1+x2)/2, (y1+y2)/2)

def ensure_db_tables(db_path=DB_PATH):
    db = sqlite3.connect(db_path)
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS plate_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            plate TEXT,
            car_path TEXT,
            plate_path TEXT,
            face_path TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS parking_status (
            car_id INTEGER PRIMARY KEY,
            plate TEXT,
            ts_in TEXT
        )
    """)
    db.commit()
    db.close()

def fit_image_to_canvas_bgr(img_bgr, canvas_w, canvas_h, background=(255,255,255)):
    """
    Resize img_bgr to fit into (canvas_w, canvas_h) keeping aspect ratio.
    Returns RGB numpy array shaped (canvas_h, canvas_w, 3).
    """
    if img_bgr is None:
        # return blank canvas
        canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8)
        canvas[:] = background
        return cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

    h, w = img_bgr.shape[:2]
    if h == 0 or w == 0:
        canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8)
        canvas[:] = background
        return cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

    scale = min(canvas_w / w, canvas_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = background
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2
    canvas[y:y+new_h, x:x+new_w] = resized
    # convert to RGB for PIL
    return cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

# ---------------------------
# GUI + App
# ---------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Vehicle + Plate OCR + Parking Tracking")
        root.geometry("1400x780")

        # ---------------- Left frame ----------------
        left_frame = tk.Frame(root, width=420)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(pady=6)
        self.btn_open = tk.Button(btn_frame, text="Chọn video / camera", command=self.select_and_start)
        self.btn_open.pack(side=tk.LEFT, padx=6)
        self.btn_stop = tk.Button(btn_frame, text="Dừng", command=self.stop_video, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        # --- History Treeview (plate_logs) ---
        tk.Label(left_frame, text="Lịch sử phát hiện (unique plates)").pack(anchor="w", padx=6)
        columns = ("car_id", "plate", "time")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=10)
        self.tree.heading("car_id", text="Car ID")
        self.tree.heading("plate", text="Plate")
        self.tree.heading("time", text="Time")
        self.tree.column("car_id", width=60)
        self.tree.column("plate", width=120)
        self.tree.column("time", width=140)
        self.tree.pack(fill=tk.X, expand=False, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)
        self.tree.tag_configure('new_car', background='lightgreen')
        self.tree.tag_configure('left_car', background='lightcoral')

        # --- Real-time Parking Treeview (current in parking) ---
        tk.Label(left_frame, text="Xe đang trong bãi (real-time)").pack(anchor="w", padx=6, pady=(10,0))
        bai_cols = ("car_id", "plate", "time_in")
        self.tree_bai = ttk.Treeview(left_frame, columns=bai_cols, show="headings", height=14)
        self.tree_bai.heading("car_id", text="Car ID")
        self.tree_bai.heading("plate", text="Plate")
        self.tree_bai.heading("time_in", text="Time In")
        self.tree_bai.column("car_id", width=60)
        self.tree_bai.column("plate", width=130)
        self.tree_bai.column("time_in", width=140)
        self.tree_bai.pack(fill=tk.Y, expand=True, pady=6)
        self.tree_bai.bind("<<TreeviewSelect>>", self.on_row_selected_bai)

        # ---------------- Right frame ----------------
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_frame = tk.Frame(right_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        # --- CAR PREVIEW ---
        car_frame = tk.Frame(preview_frame, width=CAR_W, height=CAR_H)
        car_frame.pack(side=tk.LEFT, padx=2, pady=2)
        car_frame.pack_propagate(False)

        self.preview_car = tk.Label(car_frame, text="Car image", relief=tk.SUNKEN)
        self.preview_car.pack(fill=tk.BOTH, expand=True)

        # --- PLATE PREVIEW ---
        plate_frame = tk.Frame(preview_frame, width=PLATE_W, height=PLATE_H)
        plate_frame.pack(side=tk.LEFT, padx=2, pady=2)
        plate_frame.pack_propagate(False)

        self.preview_plate = tk.Label(plate_frame, text="Plate image", relief=tk.SUNKEN)
        self.preview_plate.pack(fill=tk.BOTH, expand=True)

        # --- FACE PREVIEW ---
        face_frame = tk.Frame(preview_frame, width=FACE_W, height=FACE_H)
        face_frame.pack(side=tk.LEFT, padx=2, pady=2)
        face_frame.pack_propagate(False)

        self.preview_face = tk.Label(face_frame, text="Face image", relief=tk.SUNKEN)
        self.preview_face.pack(fill=tk.BOTH, expand=True)

        # ---------------- Internal state ----------------
        self.video_thread = None
        self.running = False
        self.cap = None
        self.current_video_path = None
        self.latest_entries = []   # last frame entries (from OCR)
        self.latest_tracked_ids = set()  # set of currently tracked ids (from last frame)
        self.car_states = {}       # for history Treeview (id->state)
        self.bai_states = {}       # real-time parking: car_id -> ts_in

        ensure_db_tables()  # create tables if not exist

        # Poll queue
        self.root.after(100, self.process_queue)

    # ---------------- Video controls ----------------
    def select_and_start(self):
        path = filedialog.askopenfilename(title="Chọn video (hoặc hủy để dùng camera)",
                                          filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")])
        self.current_video_path = path if path else None
        self.start_video()

    def start_video(self):
        if self.running:
            messagebox.showinfo("Thông báo", "Video đang chạy")
            return
        if self.current_video_path:
            cap = cv2.VideoCapture(self.current_video_path)
            if not cap.isOpened():
                messagebox.showerror("Lỗi", f"Không mở được file: {self.current_video_path}")
                return
        else:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                messagebox.showerror("Lỗi", "Không mở được camera")
                return

        self.cap = cap
        self.running = True
        self.btn_open.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()

    def stop_video(self):
        self.running = False
        self.btn_open.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    # ---------------- Queue processing & Treeview updates (main thread) ----------------
    def process_queue(self):
        """
        Called in main thread periodically. Retrieves payloads and updates UI.
        Payload can include:
          - entries: list of detection dicts (car_id, plate_text, car_path, plate_path, face_path, ts)
          - tracked_ids: list of currently tracked car ids
          - previews: dict with keys 'car_rgb', 'plate_rgb', 'face_rgb' (numpy RGB arrays)
        """
        updated_preview = False
        while not result_queue.empty():
            payload = result_queue.get()
            entries = payload.get("entries", [])
            tracked_ids = set(payload.get("tracked_ids", []))
            previews = payload.get("previews", {})

            self.latest_entries = entries
            self.latest_tracked_ids = tracked_ids

            # Update history tree (unique plates)
            self.update_treeview(entries)

            # Update parking states based on tracked_ids
            self.update_bai_states(tracked_ids, entries)

            # Refresh bai Treeview
            self.update_bai_tree()

            # If previews present, update them (they are RGB numpy arrays)
            if previews:
                car_rgb = previews.get("car_rgb")
                plate_rgb = previews.get("plate_rgb")
                face_rgb = previews.get("face_rgb")
                # schedule main-thread PhotoImage creation & widget update
                self.root.after(0, self._update_previews_from_arrays, car_rgb, plate_rgb, face_rgb)
                updated_preview = True

        # repeat polling
        self.root.after(80, self.process_queue)

    def _update_previews_from_arrays(self, car_rgb, plate_rgb, face_rgb):
        # create PhotoImage from numpy RGB arrays (main thread)
        if car_rgb is not None:
            im = Image.fromarray(car_rgb)
            photo = ImageTk.PhotoImage(im)
            self.preview_car.config(image=photo, text="")
            self.preview_car.image = photo
        # plate
        if plate_rgb is not None:
            im = Image.fromarray(plate_rgb)
            photo = ImageTk.PhotoImage(im)
            self.preview_plate.config(image=photo, text="")
            self.preview_plate.image = photo
        # face
        if face_rgb is not None:
            im = Image.fromarray(face_rgb)
            photo = ImageTk.PhotoImage(im)
            self.preview_face.config(image=photo, text="")
            self.preview_face.image = photo

    def update_treeview(self, entries):
        # Show unique plates in history (latest first)
        for item in self.tree.get_children():
            self.tree.delete(item)
        current_ids = set([e['car_id'] for e in entries])
        previous_ids = set(self.car_states.keys())
        new_ids = current_ids - previous_ids
        # Insert entries (we show order same as entries list)
        for e in entries:
            tag = 'new_car' if e['car_id'] in new_ids else ''
            self.tree.insert('', tk.END, values=(e['car_id'], e['plate_text'] or '', e['ts']), tags=(tag,))
            self.car_states[e['car_id']] = 'present'
        # mark lefts
        left_ids = previous_ids - current_ids
        for car_id in left_ids:
            self.car_states[car_id] = 'left'
        # schedule removal of left cars from history tree (visual housekeeping)
        self.root.after(3000, self.remove_left_cars)

    def remove_left_cars(self):
        # remove items that are marked 'left' in car_states
        for item_id in list(self.tree.get_children()):
            vals = self.tree.item(item_id, 'values')
            if not vals:
                continue
            try:
                car_id = int(vals[0])
            except:
                continue
            if self.car_states.get(car_id) == 'left':
                self.tree.delete(item_id)
                del self.car_states[car_id]

    def update_bai_states(self, tracked_ids, entries):
        """
        tracked_ids: set of car_id currently tracked in frame
        entries: list of dict with fields including car_id and plate_text and ts
        """
        # 1) New cars entering: tracked_ids - existing bai_states
        new_in = tracked_ids - set(self.bai_states.keys())
        plate_map = {e['car_id']: e for e in entries}
        for car_id in new_in:
            ts_in = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            plate_text = None
            if car_id in plate_map:
                plate_text = plate_map[car_id].get("plate_text")
                ts_in = plate_map[car_id].get("ts") or ts_in
            # add to in-memory state
            self.bai_states[car_id] = ts_in
            # persist to DB parking_status (insert or replace)
            try:
                db = sqlite3.connect(DB_PATH)
                c = db.cursor()
                c.execute("INSERT OR REPLACE INTO parking_status (car_id, plate, ts_in) VALUES (?, ?, ?)",
                          (car_id, plate_text, ts_in))
                db.commit()
                db.close()
            except Exception:
                pass

        # 2) Cars left: present in bai_states but not in tracked_ids
        left = set(self.bai_states.keys()) - tracked_ids
        for car_id in left:
            try:
                db = sqlite3.connect(DB_PATH)
                c = db.cursor()
                c.execute("DELETE FROM parking_status WHERE car_id=?", (car_id,))
                db.commit()
                db.close()
            except Exception:
                pass
            if car_id in self.bai_states:
                del self.bai_states[car_id]

    def update_bai_tree(self):
        # Refresh the tree_bai
        for it in self.tree_bai.get_children():
            self.tree_bai.delete(it)
        for car_id in sorted(self.bai_states.keys()):
            ts_in = self.bai_states[car_id]
            plate = ""
            for e in self.latest_entries:
                if e['car_id'] == car_id:
                    plate = e.get('plate_text') or ""
                    break
            self.tree_bai.insert('', tk.END, values=(car_id, plate, ts_in))

    # ---------------- Row selection preview ----------------
    def on_row_selected(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        if idx < 0 or idx >= len(self.latest_entries): return
        item = self.latest_entries[idx]
        self._show_previews_from_item(item)

    def on_row_selected_bai(self, event=None):
        sel = self.tree_bai.selection()
        if not sel: return
        vals = self.tree_bai.item(sel[0], 'values')
        if not vals: return
        car_id = int(vals[0])
        item = None
        for e in self.latest_entries:
            if e['car_id'] == car_id:
                item = e
                break
        if item:
            self._show_previews_from_item(item)
        else:
            self.preview_car.config(image="", text="Không có ảnh xe")
            self.preview_car.image = None
            self.preview_plate.config(image="", text="Không có ảnh biển số")
            self.preview_plate.image = None
            self.preview_face.config(image="", text="Không có ảnh mặt")
            self.preview_face.image = None

    def _show_previews_from_item(self, item):
        # Car preview
        if item.get("car_path") and os.path.exists(item["car_path"]):
            im = Image.open(item["car_path"])
            im.thumbnail((CAR_W, CAR_H))
            tkim = ImageTk.PhotoImage(im)
            self.preview_car.config(image=tkim, text="")
            self.preview_car.image = tkim
        else:
            self.preview_car.config(image="", text="Không có ảnh xe")
            self.preview_car.image = None

        # Plate preview
        if item.get("plate_path") and os.path.exists(item["plate_path"]):
            im = Image.open(item["plate_path"])
            im.thumbnail((PLATE_W, PLATE_H))
            tkim = ImageTk.PhotoImage(im)
            self.preview_plate.config(image=tkim, text="")
            self.preview_plate.image = tkim
        else:
            self.preview_plate.config(image="", text="Không có ảnh biển số")
            self.preview_plate.image = None

        # Face preview
        if item.get("face_path") and os.path.exists(item["face_path"]):
            im = Image.open(item["face_path"])
            im.thumbnail((FACE_W, FACE_H))
            tkim = ImageTk.PhotoImage(im)
            self.preview_face.config(image=tkim, text="")
            self.preview_face.image = tkim
        else:
            self.preview_face.config(image="", text="Không có ảnh mặt")
            self.preview_face.image = None

    # ---------------- Video processing (worker thread) ----------------
    def video_loop(self):
        # DB connection in worker thread for writes
        db = sqlite3.connect(DB_PATH)
        cur = db.cursor()
        db.commit()

        cap = self.cap

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                # ---- Vehicle detection ----
                veh_results = vehicle_model(frame)[0]
                detections = []
                for box in veh_results.boxes:
                    try:
                        x1, y1, x2, y2 = bbox_to_ints(box.xyxy)
                    except:
                        x1, y1, x2, y2 = bbox_to_ints(box.xyxy[0])
                    conf = float(box.conf[0]) if hasattr(box.conf, "__getitem__") else float(box.conf)
                    if conf < 0.25: continue
                    detections.append(([x1, y1, x2 - x1, y2 - y1], conf, None))

                # ---- Tracking ----
                tracks = tracker.update_tracks(detections, frame=frame)
                tracked_cars = [(t.track_id, *map(int, t.to_ltrb())) for t in tracks if t.is_confirmed()]
                tracked_ids = [t[0] for t in tracked_cars]

                # ---- Plate detection ----
                plate_results = plate_model(frame)[0]
                plate_bboxes = []
                for box in plate_results.boxes:
                    try:
                        px1, py1, px2, py2 = bbox_to_ints(box.xyxy)
                    except:
                        px1, py1, px2, py2 = bbox_to_ints(box.xyxy[0])
                    conf = float(box.conf[0]) if hasattr(box.conf, "__getitem__") else float(box.conf)
                    if conf < 0.25: continue
                    plate_bboxes.append((px1, py1, px2, py2))

                # ---- Match plates to cars ----
                matches = []
                for pb in plate_bboxes:
                    pcx, pcy = centroid(pb)
                    for car_id, x1, y1, x2, y2 in tracked_cars:
                        if x1 <= pcx <= x2 and y1 <= pcy <= y2:
                            matches.append((car_id, pb))
                            break

                matched_car_ids = set([c for c, _ in matches])

                # ---- Highlight cars without plates ----
                overlay = frame.copy()
                alpha = 0.3
                for car_id, x1, y1, x2, y2 in tracked_cars:
                    if car_id not in matched_car_ids:
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

                # ---- Draw boxes and IDs ----
                for car_id, x1, y1, x2, y2 in tracked_cars:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"ID:{car_id}", (x1, max(12, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 255, 0), 2)
                for px1, py1, px2, py2 in plate_bboxes:
                    cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 0, 0), 2)
                    cv2.putText(frame, "Plate", (px1, max(12, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # ---- Crop, OCR, save ----
                frame_entries = []
                # We'll also prepare a preview set: use the first matched car's car/plate/face crops for live preview
                preview_car_crop = None
                preview_plate_crop = None
                preview_face_crop = None

                for car_id, (px1, py1, px2, py2) in matches:
                    vb = next((v for v in tracked_cars if v[0] == car_id), None)
                    if vb is None: continue
                    _, vx1, vy1, vx2, vy2 = vb
                    # clip coords to frame bounds
                    h, w = frame.shape[:2]
                    vx1, vy1 = max(0, vx1), max(0, vy1)
                    vx2, vy2 = min(w - 1, vx2), min(h - 1, vy2)
                    px1, py1, px2, py2 = max(0, px1), max(0, py1), min(w - 1, px2), min(h - 1, py2)

                    if vx2 <= vx1 or vy2 <= vy1:
                        continue
                    car_crop = frame[vy1:vy2, vx1:vx2].copy()
                    plate_crop = frame[py1:py2, px1:px2].copy() if (px2 > px1 and py2 > py1) else None

                    # set previews to first available crops (so UI shows something)
                    if preview_car_crop is None:
                        preview_car_crop = car_crop
                    if preview_plate_crop is None and plate_crop is not None:
                        preview_plate_crop = plate_crop

                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    car_path = os.path.join(SAVED_CARS, f"car_{car_id}_{ts}.jpg")
                    cv2.imwrite(car_path, car_crop)

                    plate_path = None
                    plate_text = None
                    if plate_crop is not None and plate_crop.size > 0:
                        plate_path = os.path.join(SAVED_PLATES, f"plate_{car_id}_{ts}.jpg")
                        cv2.imwrite(plate_path, plate_crop)
                        try:
                            plate_text_raw = ocr.run(cv2.cvtColor(plate_crop, cv2.COLOR_BGR2RGB))
                            plate_text = "".join(plate_text_raw) if isinstance(plate_text_raw, list) else plate_text_raw
                            if plate_text:
                                plate_text = plate_text.strip()
                        except:
                            plate_text = None

                    # Face detection placeholder (not implemented)
                    face_path = None

                    # Save DB entry for unique plates (as before)
                    try:
                        if plate_text:
                            cur.execute("SELECT plate FROM plate_logs WHERE plate=?", (plate_text,))
                            if not cur.fetchone():
                                cur.execute("""INSERT INTO plate_logs
                                                   (car_id, plate, car_path, plate_path, face_path, timestamp)
                                               VALUES (?, ?, ?, ?, ?, ?)""",
                                            (car_id, plate_text, car_path, plate_path, face_path, ts))
                                db.commit()
                    except Exception:
                        pass

                    if plate_text:
                        cv2.putText(frame, str(plate_text), (px1, max(12, py1 - 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                    (0, 255, 255), 2)

                    frame_entries.append({
                        "car_id": car_id,
                        "plate_text": plate_text,
                        "car_path": car_path,
                        "plate_path": plate_path,
                        "face_path": face_path,
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # human-friendly ts for UI
                    })

                # Build preview rgb arrays (fit to canvases)
                try:
                    car_rgb = fit_image_to_canvas_bgr(preview_car_crop if preview_car_crop is not None else frame, CAR_W, CAR_H)
                except Exception:
                    car_rgb = fit_image_to_canvas_bgr(frame, CAR_W, CAR_H)
                plate_rgb = fit_image_to_canvas_bgr(preview_plate_crop, PLATE_W, PLATE_H) if preview_plate_crop is not None else None
                face_rgb = None  # placeholder if face crop available later

                # Put payload to main thread queue
                payload = {"entries": frame_entries, "tracked_ids": tracked_ids,
                           "previews": {"car_rgb": car_rgb, "plate_rgb": plate_rgb, "face_rgb": face_rgb}}
                try:
                    result_queue.put(payload)
                except:
                    pass

                # small sleep to yield (no cv2.waitKey in thread)
                time.sleep(0.001)

        finally:
            try:
                db.close()
            except:
                pass
            try:
                cap.release()
            except:
                pass
            self.running = False
            self.root.after(0, lambda: self.btn_open.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

# ---------------------------
if __name__=="__main__":
    root=tk.Tk()
    app=App(root)
    root.mainloop()
