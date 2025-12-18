import tkinter as tk
from PIL import Image, ImageTk
import cv2

class BBoxEditor(tk.Toplevel):
    def __init__(self, parent, car_entries, start_car_id):
        super().__init__(parent)
        self.title("Xác nhận Plate → Car")
        self.result = []
        self.next_car_id = start_car_id
        self.entries = car_entries

        self.canvas = tk.Canvas(self, width=800, height=450, bg="black")
        self.canvas.pack()

        self.current = 0
        self.load_entry()

        btn = tk.Button(self, text="Xác nhận & Tiếp", command=self.confirm)
        btn.pack(pady=5)

    def load_entry(self):
        e = self.entries[self.current]
        img = cv2.imread(e["car_path"])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (800, 450))
        self.photo = ImageTk.PhotoImage(Image.fromarray(img))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        # bbox mặc định (toàn xe)
        self.bbox = [50, 50, 750, 400]
        self.rect = self.canvas.create_rectangle(*self.bbox, outline="red", width=2)

        self.drag = None
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def on_click(self, e):
        self.drag = (e.x, e.y)

    def on_drag(self, e):
        dx = e.x - self.drag[0]
        dy = e.y - self.drag[1]
        self.canvas.move(self.rect, dx, dy)
        self.drag = (e.x, e.y)

    def confirm(self):
        e = self.entries[self.current].copy()
        e["car_id"] = self.next_car_id
        self.next_car_id += 1
        self.result.append(e)

        self.current += 1
        if self.current >= len(self.entries):
            self.destroy()
        else:
            self.load_entry()


def resolve_multi_plate(parent, car_entries, start_car_id):
    dlg = BBoxEditor(parent, car_entries, start_car_id)
    parent.wait_window(dlg)
    return dlg.result, dlg.next_car_id
