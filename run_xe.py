import tkinter as tk
from db.database import init_db
from gui.xe_gui import XeGUI

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("ParkID - Quản lý Xe")
    root.geometry("700x500")
    app = XeGUI(root)
    root.mainloop()
