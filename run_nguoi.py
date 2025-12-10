import tkinter as tk
from db.database import init_db
from gui.nguoi_gui import NguoiGUI

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("ParkID - Quản lý Người")
    root.geometry("800x600")
    app = NguoiGUI(root)
    root.mainloop()
