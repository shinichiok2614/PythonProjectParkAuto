import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from models import nguoi, donvi

class NguoiGUI:
    def __init__(self, parent):
        self.root = parent
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.create_widgets()
        self.load_donvi()
        self.load_nguoi()

    def create_widgets(self):
        frm_form = tk.Frame(self.frame)
        frm_form.pack(padx=10, pady=10, fill="x")

        # --- Tên Người ---
        tk.Label(frm_form, text="Tên Người:").grid(row=0, column=0, sticky="w")
        self.entry_ten = tk.Entry(frm_form)
        self.entry_ten.grid(row=0, column=1)

        # --- Ảnh mặt ---
        tk.Label(frm_form, text="Ảnh Mặt:").grid(row=1, column=0, sticky="w")
        self.entry_anh = tk.Entry(frm_form)
        self.entry_anh.grid(row=1, column=1)
        tk.Button(frm_form, text="Chọn file", command=self.choose_file).grid(row=1, column=2)

        # --- Đơn vị (bất kỳ cấp nào) ---
        tk.Label(frm_form, text="Đơn vị:").grid(row=2, column=0, sticky="w")
        self.cb_donvi = ttk.Combobox(frm_form, state="readonly")
        self.cb_donvi.grid(row=2, column=1)

        # --- Buttons Thêm/Sửa/Xóa ---
        frm_buttons = tk.Frame(self.frame)
        frm_buttons.pack(padx=10, pady=5)
        tk.Button(frm_buttons, text="Thêm Người", command=self.add_nguoi).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Sửa Người", command=self.update_nguoi).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Xóa Người", command=self.delete_nguoi).pack(side="left", padx=5)

        # --- Treeview hiển thị danh sách ---
        self.tree = ttk.Treeview(self.frame, columns=("id", "ten", "anh", "donvi", "cap"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("ten", text="Tên")
        self.tree.heading("anh", text="Ảnh")
        self.tree.heading("donvi", text="Đơn vị")
        self.tree.heading("cap", text="Cấp")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # --- Chọn ảnh từ file ---
    def choose_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png")])
        if filename:
            self.entry_anh.delete(0, tk.END)
            self.entry_anh.insert(0, filename)

    # --- Load tất cả đơn vị (bất kỳ cấp) ---
    def load_donvi(self):
        all_units = donvi.DonVi.get_all()
        self.donvi_list = all_units
        self.cb_donvi['values'] = [self.get_donvi_fullname(x) for x in all_units]
        self.adjust_combobox_width()  # Chỉnh width dựa trên dữ liệu

    # --- Load danh sách người ---
    def load_nguoi(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in nguoi.Nguoi.get_all():  # row = (id, ten, anh_mat, donvi_ten, donvi_cap)
            self.tree.insert("", "end", values=row)

    # --- Khi chọn 1 người trên treeview ---
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            self.entry_ten.delete(0, tk.END)
            self.entry_ten.insert(0, item['values'][1])
            self.entry_anh.delete(0, tk.END)
            self.entry_anh.insert(0, item['values'][2])
            # Chọn đơn vị trong Combobox
            for idx, dv in enumerate(self.donvi_list):
                fullname = self.get_donvi_fullname(dv)
                if fullname == item['values'][3]:  # so sánh tên đầy đủ
                    self.cb_donvi.current(idx)
                    break

    # --- Thêm người ---
    def add_nguoi(self):
        ten = self.entry_ten.get()
        anh = self.entry_anh.get()
        idx = self.cb_donvi.current()
        if idx < 0:
            messagebox.showwarning("Lỗi", "Chọn đơn vị")
            return
        donvi_id = self.donvi_list[idx][0]
        nguoi.Nguoi.add(ten, anh, donvi_id)
        self.load_nguoi()

    # --- Sửa người ---
    def update_nguoi(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn người để sửa")
            return
        nguoi_id = self.tree.item(selected[0])['values'][0]
        ten = self.entry_ten.get()
        anh = self.entry_anh.get()
        idx = self.cb_donvi.current()
        if idx < 0:
            messagebox.showwarning("Lỗi", "Chọn đơn vị")
            return
        donvi_id = self.donvi_list[idx][0]
        nguoi.Nguoi.update(nguoi_id, ten, anh, donvi_id)
        self.load_nguoi()

    # --- Xóa người ---
    def delete_nguoi(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn người để xóa")
            return
        nguoi_id = self.tree.item(selected[0])['values'][0]
        nguoi.Nguoi.delete(nguoi_id)
        self.load_nguoi()

    # Lấy tên đầy đủ phân cấp của 1 DonVi
    def get_donvi_fullname(self, donvi_row):
        """
        donvi_row = (id, ten, cap, parent_id)
        Trả về chuỗi: Cấp 1 - Cấp 2 - Cấp 3 - Cấp 4
        """
        names = [f"{donvi_row[1]} (C{donvi_row[2]})"]
        parent_id = donvi_row[3]
        while parent_id:
            conn = donvi.get_conn()
            c = conn.cursor()
            c.execute("SELECT id, ten, cap, parent_id FROM DonVi WHERE id=?", (parent_id,))
            parent = c.fetchone()
            conn.close()
            if parent:
                names.insert(0, f"{parent[1]} (C{parent[2]})")
                parent_id = parent[3]
            else:
                break
        return " - ".join(names)

    def adjust_combobox_width(self):
        # Tính độ dài tối đa của các giá trị
        if hasattr(self, 'cb_donvi') and self.donvi_list:
            max_len = max(len(self.get_donvi_fullname(x)) for x in self.donvi_list)
            # Set width của Combobox (khoảng 1 ký tự = 1 đơn vị width)
            self.cb_donvi.config(width=max_len + 2)  # +2 cho dư
