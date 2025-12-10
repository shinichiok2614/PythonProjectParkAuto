import tkinter as tk
from tkinter import ttk, messagebox
from models import xe, nguoi

class XeGUI:
    def __init__(self, parent):
        self.root = parent
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.create_widgets()
        self.load_nguoi()
        self.load_xe()

    def create_widgets(self):
        frm_form = tk.Frame(self.frame)
        frm_form.pack(padx=10, pady=10, fill="x")

        # --- Biển số ---
        tk.Label(frm_form, text="Biển số:").grid(row=0, column=0, sticky="w")
        self.entry_bien_so = tk.Entry(frm_form)
        self.entry_bien_so.grid(row=0, column=1)

        # --- Người sở hữu ---
        tk.Label(frm_form, text="Người sở hữu:").grid(row=1, column=0, sticky="w")
        self.cb_nguoi = ttk.Combobox(frm_form, state="readonly", width=60)
        self.cb_nguoi.grid(row=1, column=1, columnspan=2)

        # --- Buttons Thêm/Sửa/Xóa ---
        frm_buttons = tk.Frame(self.frame)
        frm_buttons.pack(padx=10, pady=5)
        tk.Button(frm_buttons, text="Thêm Xe", command=self.add_xe).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Sửa Xe", command=self.update_xe).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Xóa Xe", command=self.delete_xe).pack(side="left", padx=5)

        # --- Treeview hiển thị xe ---
        self.tree = ttk.Treeview(self.frame,
                                 columns=("id", "bien_so", "nguoi_id", "nguoi_ten"),
                                 show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("bien_so", text="Biển số")
        self.tree.heading("nguoi_id", text="ID Người")
        self.tree.heading("nguoi_ten", text="Người sở hữu")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    # --- Load danh sách người vào Combobox ---
    def load_nguoi(self):
        all_nguoi = nguoi.Nguoi.get_all_full()  # dùng get_all_full để lấy tên đơn vị phân cấp đầy đủ
        self.nguoi_list = all_nguoi
        self.cb_nguoi['values'] = [f"{x[1]} ({x[3]})" for x in all_nguoi]

    # --- Load danh sách xe ---
    def load_xe(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in xe.Xe.get_all():
            self.tree.insert("", "end", values=row)

    # --- Khi chọn 1 xe trên Treeview ---
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            self.entry_bien_so.delete(0, tk.END)
            self.entry_bien_so.insert(0, item['values'][1])
            # Chọn người sở hữu trong Combobox
            for idx, n in enumerate(self.nguoi_list):
                if n[0] == item['values'][2]:
                    self.cb_nguoi.current(idx)
                    break

    # --- Thêm xe ---
    def add_xe(self):
        bien_so = self.entry_bien_so.get().strip()
        if not bien_so:
            messagebox.showwarning("Lỗi", "Nhập biển số")
            return
        idx = self.cb_nguoi.current()
        if idx < 0:
            messagebox.showwarning("Lỗi", "Chọn người sở hữu")
            return
        nguoi_id = self.nguoi_list[idx][0]
        xe.Xe.add(bien_so, nguoi_id)
        self.load_xe()

    # --- Sửa xe ---
    def update_xe(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn xe để sửa")
            return
        xe_id = self.tree.item(selected[0])['values'][0]
        bien_so = self.entry_bien_so.get().strip()
        if not bien_so:
            messagebox.showwarning("Lỗi", "Nhập biển số")
            return
        idx = self.cb_nguoi.current()
        if idx < 0:
            messagebox.showwarning("Lỗi", "Chọn người sở hữu")
            return
        nguoi_id = self.nguoi_list[idx][0]
        xe.Xe.update(xe_id, bien_so, nguoi_id)
        self.load_xe()

    # --- Xóa xe ---
    def delete_xe(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn xe để xóa")
            return
        xe_id = self.tree.item(selected[0])['values'][0]
        xe.Xe.delete(xe_id)
        self.load_xe()
