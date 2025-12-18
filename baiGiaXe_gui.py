import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


class App:
    def __init__(self, root):
        self.root = root
        root.title("Vehicle + Plate OCR")
        root.geometry("1400x700")

        # =====================================================
        # =============== ROOT CONTAINER ======================
        # =====================================================
        main_container = tk.Frame(root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # ================= LEFT (400px) =====================
        left_frame = tk.Frame(main_container, width=400, relief=tk.GROOVE, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        # -------- DB chooser --------
        db_frame = tk.LabelFrame(left_frame, text="Database")
        db_frame.pack(fill=tk.X, padx=5, pady=5)

        self.db_entry = tk.Entry(db_frame)
        self.db_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        tk.Button(
            db_frame, text="Chọn DB xe", command=self.choose_db
        ).pack(side=tk.LEFT, padx=5)

        # -------- Treeview XE VÀO --------
        xe_vao_frame = tk.LabelFrame(left_frame, text="XE VÀO")
        xe_vao_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree_xe_vao = self.create_treeview(xe_vao_frame)

        # -------- Treeview XE RA --------
        xe_ra_frame = tk.LabelFrame(left_frame, text="XE RA")
        xe_ra_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree_xe_ra = self.create_treeview(xe_ra_frame)

        # ================= MIDDLE (expand) ===================
        middle_frame = tk.Frame(main_container, relief=tk.GROOVE, bd=2)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # -------- Video --------
        self.video_label = tk.Label(
            middle_frame, text="VIDEO", bg="black", fg="white", height=15
        )
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # -------- Buttons video --------
        btn_frame = tk.Frame(middle_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.btn_open = tk.Button(
            btn_frame, text="Chọn video / camera", command=self.select_and_start
        )
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(
            btn_frame, text="Dừng", state=tk.DISABLED, command=self.stop_video
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_pause = tk.Button(
            btn_frame, text="Pause", command=self.toggle_pause
        )
        self.btn_pause.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(
            btn_frame, text="Lưu dữ liệu", command=self.save_paused_data
        )
        self.btn_save.pack(side=tk.LEFT, padx=5)
        self.btn_save.pack_forget()

        # -------- Preview --------
        preview_frame = tk.LabelFrame(middle_frame, text="PREVIEW")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_car = tk.Label(preview_frame, text="Car", relief=tk.SUNKEN)
        self.preview_plate = tk.Label(preview_frame, text="Plate", relief=tk.SUNKEN)
        self.preview_face = tk.Label(preview_frame, text="Face", relief=tk.SUNKEN)

        self.preview_car.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_plate.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_face.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ================= RIGHT (400px) ====================
        right_frame = tk.Frame(main_container, width=400, relief=tk.GROOVE, bd=2)
        right_frame.pack(side=tk.LEFT, fill=tk.Y)
        right_frame.pack_propagate(False)

        # -------- Treeview XE TRONG BÃI --------
        trong_bai_frame = tk.LabelFrame(right_frame, text="XE TRONG BÃI")
        trong_bai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree_trong_bai = self.create_treeview(trong_bai_frame)

    # =====================================================
    # ================== TREEVIEW FACTORY =================
    # =====================================================
    def create_treeview(self, parent):
        columns = ("car_id", "plate", "time")
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        tree.heading("car_id", text="Car ID")
        tree.heading("plate", text="Plate")
        tree.heading("time", text="Time")

        tree.column("car_id", width=70, anchor=tk.CENTER)
        tree.column("plate", width=120, anchor=tk.CENTER)
        tree.column("time", width=140, anchor=tk.CENTER)

        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<<TreeviewSelect>>", self.on_row_selected)

        tree.tag_configure("new_car", background="lightgreen")
        tree.tag_configure("left_car", background="lightcoral")

        return tree

    # =====================================================
    # ================= PLACEHOLDER LOGIC =================
    # =====================================================
    def choose_db(self):
        path = filedialog.askopenfilename(
            title="Chọn database Xe",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")]
        )
        if path:
            self.db_entry.delete(0, tk.END)
            self.db_entry.insert(0, path)

    def select_and_start(self):
        filedialog.askopenfilename(
            title="Chọn video (hoặc hủy để dùng camera)",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
        )
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_open.config(state=tk.DISABLED)

    def stop_video(self):
        self.btn_open.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def toggle_pause(self):
        if self.btn_pause.cget("text") == "Pause":
            self.btn_pause.config(text="Play")
            self.btn_save.pack(side=tk.LEFT, padx=5)
        else:
            self.btn_pause.config(text="Pause")
            self.btn_save.pack_forget()

    def save_paused_data(self):
        messagebox.showinfo("Thông báo", "Chưa gắn logic lưu dữ liệu")

    def on_row_selected(self, event=None):
        self.preview_car.config(text="Car image")
        self.preview_plate.config(text="Plate image")
        self.preview_face.config(text="Face image")


# ================= MAIN =================
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
