import tkinter as tk
from db.database import init_db
from gui.donvi_gui import DonViGUI

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("ParkID - Quản lý Đơn vị 4 cấp")
    root.geometry("800x600")
    app = DonViGUI(root)
    root.mainloop()
