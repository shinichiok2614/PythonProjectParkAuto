import tkinter as tk
from tkinter import ttk
from gui.nguoi_gui import NguoiGUI
from gui.donvi_gui import DonViGUI
# Sau này thêm gui.xe_gui import XeGUI

class MainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ParkID - Quản lý Bãi Giữ Xe")
        self.create_menu()
        self.frame_content = tk.Frame(self.root)
        self.frame_content.pack(fill="both", expand=True)
        self.current_frame = None

        # Mặc định mở tab Người
        self.show_nguoi_gui()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        manage_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Quản lý", menu=manage_menu)
        manage_menu.add_command(label="Người", command=self.show_nguoi_gui)
        manage_menu.add_command(label="Xe", command=self.show_xe_gui)
        manage_menu.add_command(label="Đơn vị", command=self.show_donvi_gui)

        menubar.add_command(label="Thoát", command=self.root.quit)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.frame.destroy()
            self.current_frame = None

    def show_nguoi_gui(self):
        self.clear_frame()
        self.current_frame = NguoiGUI(self.frame_content)

    def show_donvi_gui(self):
        self.clear_frame()
        self.current_frame = DonViGUI(self.frame_content)

    def show_xe_gui(self):
        # Tạm thời hiển thị thông báo, sẽ thay bằng XeGUI khi hoàn thiện
        self.clear_frame()
        temp_frame = tk.Frame(self.frame_content)
        temp_frame.pack(fill="both", expand=True)
        tk.Label(temp_frame, text="GUI quản lý Xe sẽ được tích hợp ở đây").pack(pady=50)
        self.current_frame = temp_frame
