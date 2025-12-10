import tkinter as tk
from db.database import init_db
from gui.main_gui import MainGUI

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.geometry("800x600")
    app = MainGUI(root)
    root.mainloop()
