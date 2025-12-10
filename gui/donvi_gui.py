import tkinter as tk
from tkinter import ttk, messagebox
from models import donvi

class DonViGUI:
    def __init__(self, parent):
        self.root = parent
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.create_widgets()
        self.load_donvi1()

    def create_widgets(self):
        frm_form = tk.Frame(self.frame)
        frm_form.pack(padx=10, pady=10, fill="x")

        # Tên đơn vị
        tk.Label(frm_form, text="Tên Đơn vị:").grid(row=0, column=0, sticky="w")
        self.entry_ten = tk.Entry(frm_form)
        self.entry_ten.grid(row=0, column=1)

        # Cấp đơn vị
        tk.Label(frm_form, text="Cấp:").grid(row=1, column=0, sticky="w")
        self.cb_cap = ttk.Combobox(frm_form, state="readonly", values=[1, 2, 3])
        self.cb_cap.grid(row=1, column=1)
        self.cb_cap.current(0)
        self.cb_cap.bind("<<ComboboxSelected>>", self.on_cap_selected)

        # Dropdown cấp trên
        tk.Label(frm_form, text="Đơn vị cấp trên:").grid(row=2, column=0, sticky="w")
        self.cb_parent = ttk.Combobox(frm_form, state="readonly")
        self.cb_parent.grid(row=2, column=1)

        # Buttons
        frm_buttons = tk.Frame(self.frame)
        frm_buttons.pack(padx=10, pady=5)
        tk.Button(frm_buttons, text="Thêm", command=self.add_donvi).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Sửa", command=self.update_donvi).pack(side="left", padx=5)
        tk.Button(frm_buttons, text="Xóa", command=self.delete_donvi).pack(side="left", padx=5)

        # Treeview
        self.tree = ttk.Treeview(self.frame, columns=("id", "ten", "cap", "parent"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("ten", text="Tên")
        self.tree.heading("cap", text="Cấp")
        self.tree.heading("parent", text="Cấp Trên")
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def on_cap_selected(self, event):
        cap = int(self.cb_cap.get())
        if cap == 1:
            self.cb_parent['values'] = []
            self.cb_parent.set("")
        else:
            parent_cap = cap - 1
            parents = donvi.DonVi.get_by_cap(parent_cap)
            self.parent_list = parents
            self.cb_parent['values'] = [x[1] for x in parents]
            if parents:
                self.cb_parent.current(0)
            else:
                self.cb_parent.set("")

    def load_donvi1(self):
        self.load_tree()

    def load_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Lấy tất cả đơn vị
        units = []
        for cap in [1, 2, 3]:
            units.extend(donvi.DonVi.get_by_cap(cap))
        for u in units:
            # Lấy tên parent nếu có
            parent_name = ""
            if u[0]:
                parent_id = self.get_parent_id(u[0])
                if parent_id:
                    parent_name = self.get_donvi_name(parent_id)
            self.tree.insert("", "end", values=(u[0], u[1], self.get_cap(u[0]), parent_name))

    def get_cap(self, id):
        for cap in [1,2,3]:
            lst = donvi.DonVi.get_by_cap(cap)
            if any(x[0]==id for x in lst):
                return cap
        return None

    def get_parent_id(self, id):
        conn = donvi.get_conn()
        c = conn.cursor()
        c.execute("SELECT parent_id FROM DonVi WHERE id=?", (id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def get_donvi_name(self, id):
        conn = donvi.get_conn()
        c = conn.cursor()
        c.execute("SELECT ten FROM DonVi WHERE id=?", (id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else ""

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            self.entry_ten.delete(0, tk.END)
            self.entry_ten.insert(0, item['values'][1])
            self.cb_cap.set(item['values'][2])
            # Chọn parent nếu có
            parent_name = item['values'][3]
            if parent_name:
                self.cb_parent.set(parent_name)
            else:
                self.cb_parent.set("")

    def add_donvi(self):
        ten = self.entry_ten.get()
        cap = int(self.cb_cap.get())
        parent_id = None
        if cap > 1:
            idx = self.cb_parent.current()
            if idx >= 0:
                parent_id = self.parent_list[idx][0]
            else:
                messagebox.showwarning("Lỗi", "Chọn đơn vị cấp trên")
                return
        donvi.DonVi.add(ten, cap, parent_id)
        self.load_tree()

    def update_donvi(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn đơn vị để sửa")
            return
        id = self.tree.item(selected[0])['values'][0]
        ten = self.entry_ten.get()
        donvi.DonVi.update(id, ten)
        self.load_tree()

    def delete_donvi(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Lỗi", "Chọn đơn vị để xóa")
            return
        id = self.tree.item(selected[0])['values'][0]
        donvi.DonVi.delete(id)
        self.load_tree()
