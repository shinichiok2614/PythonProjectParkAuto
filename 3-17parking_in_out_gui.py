import os
import shutil
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
from datetime import datetime
from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer

# =====================================================
# MODELS (GIỮ NGUYÊN)
# =====================================================
model = YOLO("license_plate_detector.pt")
face_model = YOLO("yolov8n_100e.pt")
ocr = LicensePlateRecognizer("cct-xs-v1-global-model")

# =====================================================
# DATABASE
# =====================================================
conn = sqlite3.connect("images.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS images(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    path TEXT,
    zoom_path TEXT,
    timestamp TEXT,
    face_path TEXT,
    plate TEXT,
    direction TEXT
)
""")
conn.commit()

# --- MIGRATION ---
cur.execute("PRAGMA table_info(images)")
cols = [c[1] for c in cur.fetchall()]
if "direction" not in cols:
    cur.execute("ALTER TABLE images ADD COLUMN direction TEXT")
    conn.commit()

# =====================================================
# TK ROOT
# =====================================================
root = tk.Tk()
root.title("Parking IN / OUT – License Plate & Face")
root.geometry("1500x750")
root.configure(bg="#1e1e1e")

# =====================================================
# LAYOUT
# =====================================================
left_frame = tk.Frame(root, bg="#2b2b2b", width=400)
left_frame.pack(side=tk.LEFT, fill=tk.Y)

center_frame = tk.Frame(root, bg="#1c1c1c")
center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

right_frame = tk.Frame(root, bg="#2b2b2b", width=400)
right_frame.pack(side=tk.LEFT, fill=tk.Y)

# =====================================================
# TREEVIEW
# =====================================================
def create_tree(parent, title):
    box = tk.LabelFrame(parent, text=title, fg="white", bg="#2b2b2b")
    box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    cols = ("name", "time", "plate", "zoom", "face")
    tree = ttk.Treeview(box, columns=cols, show="headings", height=8)

    tree.heading("name", text="Ảnh")
    tree.heading("time", text="Thời gian")
    tree.heading("plate", text="Biển số")
    tree.heading("zoom", text="Zoom")
    tree.heading("face", text="Face")

    tree.column("name", width=120)
    tree.column("time", width=130)
    tree.column("plate", width=120)
    tree.column("zoom", width=50)
    tree.column("face", width=50)

    tree.pack(fill=tk.BOTH, expand=True)
    return tree

tree_in = create_tree(left_frame, "🚗 XE VÀO")
tree_out = create_tree(left_frame, "🚙 XE RA")

# =====================================================
# CENTER / RIGHT VIEW
# =====================================================
label_zoom = tk.Label(center_frame, bg="#1c1c1c")
label_zoom.pack(expand=True)

label_face = tk.Label(right_frame, bg="#1c1c1c")
label_face.pack(expand=True)

def show_image(label, path, size):
    if not path or not os.path.exists(path):
        label.config(image="", text="Không có ảnh", fg="white")
        return
    img = Image.open(path)
    img.thumbnail(size)
    tk_img = ImageTk.PhotoImage(img)
    label.config(image=tk_img)
    label.image = tk_img

# =====================================================
# LOAD TREE
# =====================================================
def load_tree(tree, direction):
    tree.delete(*tree.get_children())
    cur.execute("""
        SELECT name, timestamp, plate, zoom_path, face_path
        FROM images WHERE direction=?
        ORDER BY id DESC
    """, (direction,))
    for n,t,p,z,f in cur.fetchall():
        tree.insert("", tk.END,
            values=(n, t, p, "OK" if z else "", "OK" if f else "")
        )

# =====================================================
# ADD IMAGE (GIỮ NGUYÊN)
# =====================================================
def add_image():
    path = filedialog.askopenfilename(filetypes=[("Image","*.jpg *.png *.jpeg")])
    if not path:
        return
    os.makedirs("images", exist_ok=True)
    name = os.path.basename(path)
    new_path = os.path.join("images", name)
    shutil.copy(path, new_path)

    cur.execute("""
        INSERT INTO images(name,path,direction)
        VALUES (?,?,?)
    """, (name, new_path, "IN"))
    conn.commit()
    load_tree(tree_in,"IN")

# =====================================================
# SAVE & CAPTURE FACE (GIỮ NGUYÊN)
# =====================================================
def save_face(face):
    os.makedirs("data_faces", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"data_faces/face_{ts}.jpg"
    cv2.imwrite(path, face)
    cur.execute("""
        UPDATE images SET face_path=?
        WHERE id=(SELECT MAX(id) FROM images)
    """,(path,))
    conn.commit()

def capture_face_window():
    cap = cv2.VideoCapture(0)
    face_crop = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = face_model(frame)
        for r in results:
            for b in r.boxes:
                x1,y1,x2,y2 = map(int,b.xyxy[0])
                face_crop = frame[y1:y2, x1:x2]
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

        cv2.imshow("Face Capture", frame)
        key = cv2.waitKey(1)

        if key == 32 and face_crop is not None:
            save_face(face_crop)
            messagebox.showinfo("OK","Đã lưu khuôn mặt")
            break
        elif key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# =====================================================
# CAMERA + VIDEO YOLO (GIỮ 100% LOGIC GỐC)
# =====================================================
def open_camera_yolo(direction, use_video=False):
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    max_w, max_h = int(screen_w*0.8), int(screen_h*0.8)

    if use_video:
        path = filedialog.askopenfilename(filetypes=[("Video","*.*")])
        if not path:
            return
        cap = cv2.VideoCapture(path)
    else:
        cap = cv2.VideoCapture(0)

    cv2.namedWindow(f"Camera {direction}", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Plate Zoom", cv2.WINDOW_AUTOSIZE)

    zoom_img = None
    zoom_resized = None
    plate_text = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)[0]
        zoom_img = None
        plate_text = None

        for r in results.boxes:
            x1,y1,x2,y2 = map(int,r.xyxy[0])
            conf = float(r.conf[0])
            if conf < 0.5:
                continue

            # ===== BOUNDING BOX + LABEL =====
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,"Plate",(x1,y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

            crop = frame[y1:y2, x1:x2]
            if crop.size > 0:
                zoom_img = cv2.resize(crop,None,fx=3.5,fy=3.5)
                try:
                    plate_text = ocr.run(crop)
                    if isinstance(plate_text,list):
                        plate_text="".join(plate_text)
                except:
                    plate_text=None
            break

        if zoom_img is not None:
            h,w = zoom_img.shape[:2]
            scale = min(max_w/w, max_h/h, 1.0)
            zoom_resized = cv2.resize(zoom_img,(int(w*scale),int(h*scale)))
            cv2.imshow("Plate Zoom", zoom_resized)

        cv2.imshow(f"Camera {direction}", frame)

        key = cv2.waitKey(1)

        if key == 32:  # SPACE
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("images/captured", exist_ok=True)

            frame_path = f"images/captured/{direction}_{ts}.jpg"
            cv2.imwrite(frame_path, frame)

            zoom_path = None
            if zoom_resized is not None:
                zoom_path = f"images/captured/{direction}_plate_{ts}.jpg"
                cv2.imwrite(zoom_path, zoom_resized)

            cur.execute("""
                INSERT INTO images
                (name,path,zoom_path,timestamp,plate,direction)
                VALUES (?,?,?,?,?,?)
            """,(
                os.path.basename(frame_path),
                frame_path,
                zoom_path,
                ts,
                plate_text,
                direction
            ))
            conn.commit()

            load_tree(tree_in,"IN")
            load_tree(tree_out,"OUT")

            messagebox.showinfo(
                "OK",
                f"Đã lưu XE {'VÀO' if direction=='IN' else 'RA'}"
            )

        elif key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# =====================================================
# BUTTONS (ĐẦY ĐỦ)
# =====================================================
btn_frame = tk.Frame(left_frame, bg="#2b2b2b")
btn_frame.pack(fill=tk.X, pady=5)

tk.Button(btn_frame,text="➕ Thêm ảnh",
          command=add_image).pack(fill=tk.X,pady=2)

tk.Button(btn_frame,text="📥 Camera YOLO – XE VÀO",
          command=lambda:open_camera_yolo("IN")).pack(fill=tk.X,pady=2)

tk.Button(btn_frame,text="📤 Camera YOLO – XE RA",
          command=lambda:open_camera_yolo("OUT")).pack(fill=tk.X,pady=2)

tk.Button(btn_frame,text="🎥 Video YOLO – XE VÀO (TEST)",
          command=lambda:open_camera_yolo("IN",True)).pack(fill=tk.X,pady=2)

tk.Button(btn_frame,text="🎥 Video YOLO – XE RA (TEST)",
          command=lambda:open_camera_yolo("OUT",True)).pack(fill=tk.X,pady=2)

tk.Button(btn_frame,text="🙂 Chụp khuôn mặt",
          command=capture_face_window).pack(fill=tk.X,pady=2)

# =====================================================
# TREE SELECT
# =====================================================
def on_select(tree):
    sel = tree.selection()
    if not sel:
        return
    name = tree.item(sel[0])["values"][0]
    cur.execute("SELECT zoom_path, face_path FROM images WHERE name=?", (name,))
    row = cur.fetchone()
    if row:
        show_image(label_zoom, row[0], (600,500))
        show_image(label_face, row[1], (350,350))

tree_in.bind("<<TreeviewSelect>>", lambda e:on_select(tree_in))
tree_out.bind("<<TreeviewSelect>>", lambda e:on_select(tree_out))

# =====================================================
# INIT
# =====================================================
load_tree(tree_in,"IN")
load_tree(tree_out,"OUT")
root.mainloop()
conn.close()
