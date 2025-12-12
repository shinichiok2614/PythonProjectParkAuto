import os
import cv2
import queue
import threading
import sqlite3
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from fast_plate_ocr import LicensePlateRecognizer
from PIL import Image, ImageTk
import time

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

# Load models
vehicle_model = YOLO(VEHICLE_MODEL_PATH)
plate_model = YOLO(PLATE_MODEL_PATH)
ocr = LicensePlateRecognizer(OCR_MODEL_NAME)
tracker = DeepSort(max_age=30, n_init=3, nn_budget=100)

# Thread-safe queue
result_queue = queue.Queue()

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

# ---------------------------
# GUI
# ---------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.detect_db = sqlite3.connect(DB_PATH)
        self.init_detected_logs_table()

        self.paused = False

        root.title("Vehicle + Plate OCR")
        root.geometry("1400x700")

        # ---------------- Left frame ----------------
        left_frame = tk.Frame(root, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Thêm vào __init__() ngay dưới phần left_frame
        db_frame = tk.Frame(left_frame)
        db_frame.pack(fill=tk.X, pady=6)
        self.db_entry = tk.Entry(db_frame)
        self.db_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.btn_choose_db = tk.Button(db_frame, text="Chọn DB xe", command=self.choose_db)
        self.btn_choose_db.pack(side=tk.LEFT, padx=2)

        # ---------------- Internal DB state ----------------
        self.vehicle_db_conn = None

        # Buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(pady=6)
        self.btn_open = tk.Button(btn_frame, text="Chọn video / camera", command=self.select_and_start)
        self.btn_open.pack(side=tk.LEFT, padx=6)
        self.btn_stop = tk.Button(btn_frame, text="Dừng", command=self.stop_video, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=6)
        self.btn_pause = tk.Button(btn_frame, text="Pause", command=self.toggle_pause, state=tk.NORMAL)
        self.btn_pause.pack(side=tk.LEFT, padx=6)

        self.btn_save = tk.Button(btn_frame, text="Lưu dữ liệu", command=self.save_paused_data)
        self.btn_save.pack(side=tk.LEFT, padx=6)
        self.btn_save.pack_forget()

        # Treeview
        columns = ("car_id", "plate", "time")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=40)
        self.tree.heading("car_id", text="Car ID")
        self.tree.heading("plate", text="Plate")
        self.tree.heading("time", text="Time")
        self.tree.column("car_id", width=70)
        self.tree.column("plate", width=120)
        self.tree.column("time", width=140)
        self.tree.pack(fill=tk.Y, expand=True, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)
        self.tree.tag_configure('new_car', background='lightgreen')
        self.tree.tag_configure('left_car', background='lightcoral')

        # ---------------- Right frame với PanedWindow ----------------
        right_pane = tk.PanedWindow(root, orient=tk.VERTICAL)
        right_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Video display trên, mặc định cao 400px
        self.video_frame = tk.Label(right_pane, text="Video")
        right_pane.add(self.video_frame, minsize=400)  # minsize = chiều cao ban đầu

        # Khung preview dưới (PanedWindow ngang)
        preview_pane = tk.PanedWindow(right_pane, orient=tk.HORIZONTAL)
        right_pane.add(preview_pane, minsize=200)  # chiều cao ban đầu của preview

        self.preview_car = tk.Label(preview_pane, text="Car image", relief=tk.SUNKEN)
        self.preview_plate = tk.Label(preview_pane, text="Plate image", relief=tk.SUNKEN)
        self.preview_face = tk.Label(preview_pane, text="Face image", relief=tk.SUNKEN)

        # Thêm các preview, đặt minsize = chiều rộng ban đầu
        preview_pane.add(self.preview_car, minsize=400)
        preview_pane.add(self.preview_plate, minsize=300)
        preview_pane.add(self.preview_face, minsize=200)

        # ---------------- Internal state ----------------
        self.video_thread = None
        self.running = False
        self.cap = None
        self.current_video_path = None
        self.latest_entries = []
        self.car_states = {}

        # Poll queue
        self.root.after(200, self.process_queue)

    def toggle_pause(self):
        if not self.running:
            return

        self.paused = not self.paused
        self.btn_pause.config(text="Play" if self.paused else "Pause")

        if self.paused:
            self.btn_save.pack(side=tk.LEFT, padx=6)
        else:
            self.btn_save.pack_forget()

    # ---------------- Hàm chọn DB ----------------
    def choose_db(self):
        file = filedialog.askopenfilename(title="Chọn database Xe-Nguoi-DonVi",
                                          filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")])
        if not file:
            return
        try:
            if self.vehicle_db_conn:
                self.vehicle_db_conn.close()
            self.vehicle_db_conn = sqlite3.connect(file)
            self.db_entry.delete(0, tk.END)
            self.db_entry.insert(0, file)
            messagebox.showinfo("Thông báo", f"Đã kết nối database: {file}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được DB:\n{e}")
            self.vehicle_db_conn = None

    def save_paused_data(self):
        if not self.paused:
            messagebox.showwarning("Thông báo", "Hãy Pause trước khi lưu.")
            return

        if not self.latest_entries:
            messagebox.showinfo("Thông báo", "Không có dữ liệu để lưu.")
            return

        try:
            c = self.detect_db.cursor()

            for item in self.latest_entries:
                c.execute("""
                          INSERT INTO detected_logs
                              (car_id, plate, car_path, plate_path, face_path, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?)
                          """, (
                              item.get("car_id"),
                              item.get("plate_text"),
                              item.get("car_path"),
                              item.get("plate_path"),
                              item.get("face_path"),
                              item.get("ts")
                          ))

            self.detect_db.commit()
            messagebox.showinfo("Thành công", "Đã lưu dữ liệu vào plates.db!")

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def init_detected_logs_table(self):
        try:
            c = self.detect_db.cursor()
            c.execute("""
                      CREATE TABLE IF NOT EXISTS detected_logs
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          car_id
                          INTEGER,
                          plate
                          TEXT,
                          car_path
                          TEXT,
                          plate_path
                          TEXT,
                          face_path
                          TEXT,
                          timestamp
                          TEXT
                      )
                      """)
            self.detect_db.commit()
        except Exception as e:
            print("Lỗi tạo bảng detected_logs:", e)

    # ---------------- Cập nhật on_row_selected ----------------
    def on_row_selected(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        if idx < 0 or idx >= len(self.latest_entries): return
        item = self.latest_entries[idx]

        # --- Hiển thị car, plate, face như trước ---
        # Car preview
        if item.get("car_path") and os.path.exists(item["car_path"]):
            im = Image.open(item["car_path"])
            im.thumbnail((400, 200))
            tkim = ImageTk.PhotoImage(im)
            self.preview_car.config(image=tkim, text="")
            self.preview_car.image = tkim
        else:
            self.preview_car.config(image="", text="Không có ảnh xe")
            self.preview_car.image = None

        # Plate preview
        if item.get("plate_path") and os.path.exists(item["plate_path"]):
            im = Image.open(item["plate_path"])
            im.thumbnail((400, 150))
            tkim = ImageTk.PhotoImage(im)
            self.preview_plate.config(image=tkim, text="")
            self.preview_plate.image = tkim
        else:
            self.preview_plate.config(image="", text="Không có ảnh biển số")
            self.preview_plate.image = None

        # Face preview (nếu OCR có)
        if item.get("face_path") and os.path.exists(item["face_path"]):
            im = Image.open(item["face_path"])
            im.thumbnail((400, 150))
            tkim = ImageTk.PhotoImage(im)
            self.preview_face.config(image=tkim, text="")
            self.preview_face.image = tkim
        else:
            self.preview_face.config(image="", text="Không có ảnh mặt")
            self.preview_face.image = None

        # --- Tra cứu DB Xe-Nguoi-DonVi nếu có ---
        if self.vehicle_db_conn and item.get("plate_text"):
            plate_text = item["plate_text"]
            c = self.vehicle_db_conn.cursor()
            try:
                c.execute("""
                          SELECT Nguoi.ten, DonVi.ten, Nguoi.anh_mat
                          FROM Xe
                                   JOIN Nguoi ON Xe.nguoi_id = Nguoi.id
                                   JOIN DonVi ON Nguoi.don_vi_id = DonVi.id
                          WHERE Xe.bien_so = ?
                          """, (plate_text,))
                result = c.fetchone()
                if result:
                    nguoi_ten, don_vi_ten, anh_mat = result
                    # Hiển thị tên và đơn vị lên Treeview hoặc label
                    messagebox.showinfo("Thông tin xe",
                                        f"Biển số: {plate_text}\nNgười sở hữu: {nguoi_ten}\nĐơn vị: {don_vi_ten}")
                    # Nếu có ảnh mặt, hiển thị lên preview_face
                    if anh_mat and os.path.exists(anh_mat):
                        im = Image.open(anh_mat)
                        im.thumbnail((200, 200))
                        tkim = ImageTk.PhotoImage(im)
                        self.preview_face.config(image=tkim, text="")
                        self.preview_face.image = tkim
                else:
                    print(f"Không tìm thấy thông tin cho biển số {plate_text}")
            except Exception as e:
                print("Lỗi tra cứu DB:", e)
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

    # ---------------- Treeview update ----------------
    def process_queue(self):
        if not result_queue.empty():
            self.latest_entries = result_queue.get()
            self.update_treeview(self.latest_entries)
        self.root.after(200, self.process_queue)

    def update_treeview(self, entries):
        for item in self.tree.get_children():
            self.tree.delete(item)
        current_ids = set([e['car_id'] for e in entries])
        previous_ids = set(self.car_states.keys())
        new_ids = current_ids - previous_ids
        for e in entries:
            tag = 'new_car' if e['car_id'] in new_ids else ''
            self.tree.insert('', tk.END, values=(e['car_id'], e['plate_text'] or '', e['ts']), tags=(tag,))
            self.car_states[e['car_id']] = 'present'
        left_ids = previous_ids - current_ids
        for car_id in left_ids:
            self.car_states[car_id] = 'left'
        self.root.after(3000, self.remove_left_cars)

    def remove_left_cars(self):
        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, 'values')
            car_id = int(vals[0])
            if self.car_states.get(car_id) == 'left':
                self.tree.delete(item_id)
                del self.car_states[car_id]

    # ---------------- Row selection preview ----------------
    # def on_row_selected(self, event=None):
    #     sel = self.tree.selection()
    #     if not sel: return
    #     idx = self.tree.index(sel[0])
    #     if idx < 0 or idx >= len(self.latest_entries): return
    #     item = self.latest_entries[idx]
    #
    #     # Car preview
    #     if item.get("car_path") and os.path.exists(item["car_path"]):
    #         im = Image.open(item["car_path"])
    #         im.thumbnail((400, 200))
    #         tkim = ImageTk.PhotoImage(im)
    #         self.preview_car.config(image=tkim, text="")
    #         self.preview_car.image = tkim
    #     else:
    #         self.preview_car.config(image="", text="Không có ảnh xe")
    #         self.preview_car.image = None
    #
    #     # Plate preview
    #     if item.get("plate_path") and os.path.exists(item["plate_path"]):
    #         im = Image.open(item["plate_path"])
    #         im.thumbnail((400, 150))
    #         tkim = ImageTk.PhotoImage(im)
    #         self.preview_plate.config(image=tkim, text="")
    #         self.preview_plate.image = tkim
    #     else:
    #         self.preview_plate.config(image="", text="Không có ảnh biển số")
    #         self.preview_plate.image = None
    #
    #     # Face preview (if exists)
    #     if item.get("face_path") and os.path.exists(item["face_path"]):
    #         im = Image.open(item["face_path"])
    #         im.thumbnail((400, 150))
    #         tkim = ImageTk.PhotoImage(im)
    #         self.preview_face.config(image=tkim, text="")
    #         self.preview_face.image = tkim
    #     else:
    #         self.preview_face.config(image="", text="Không có ảnh mặt")
    #         self.preview_face.image = None

    # ---------------- Video processing ----------------
    # ---------------- Video processing ----------------
    def video_loop(self):
        db = sqlite3.connect(DB_PATH)
        cur = db.cursor()
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS plate_logs
                    (
                        id
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        car_id
                        INTEGER,
                        plate
                        TEXT
                        UNIQUE,
                        car_path
                        TEXT,
                        plate_path
                        TEXT,
                        face_path
                        TEXT,
                        timestamp
                        TEXT
                    )
                    """)
        db.commit()

        cap = self.cap

        try:
            while self.running:
                if self.paused:
                    # Chỉ sleep một chút, giữ frame hiện tại
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()
                if not ret: break

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
                for car_id, (px1, py1, px2, py2) in matches:
                    vb = next((v for v in tracked_cars if v[0] == car_id), None)
                    if vb is None: continue
                    _, vx1, vy1, vx2, vy2 = vb
                    car_crop = frame[vy1:vy2, vx1:vx2].copy()
                    plate_crop = frame[py1:py2, px1:px2].copy() if px2 > px1 and py2 > py1 else None

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
                        except:
                            plate_text = None

                    # Face detection placeholder
                    face_path = None

                    # Save DB
                    try:
                        if plate_text:
                            cur.execute("SELECT plate FROM plate_logs WHERE plate=?", (plate_text,))
                            if not cur.fetchone():
                                cur.execute("""INSERT INTO plate_logs
                                                   (car_id, plate, car_path, plate_path, face_path, timestamp)
                                               VALUES (?, ?, ?, ?, ?, ?)""",
                                            (car_id, plate_text, car_path, plate_path, face_path, ts))
                                db.commit()
                    except:
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
                        "ts": ts
                    })

                result_queue.put(frame_entries)

                # ---------------- Tkinter display ----------------
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img = img.resize((800, 450))  # Resize nếu muốn
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_frame.config(image=imgtk)  # Dùng label car làm video
                self.video_frame.image = imgtk

                # Delay tương đương cv2.waitKey
                self.root.update_idletasks()
                self.root.update()

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
            self.btn_open.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)


# ---------------------------
if __name__=="__main__":
    root=tk.Tk()
    app=App(root)
    root.mainloop()
