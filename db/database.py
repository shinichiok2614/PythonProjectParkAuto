import sqlite3
import os

DB_FILE = "baigiuxe.db"

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Bảng Đơn vị
    c.execute("""
    CREATE TABLE IF NOT EXISTS DonVi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ten TEXT NOT NULL,
        cap INTEGER NOT NULL,
        parent_id INTEGER,
        FOREIGN KEY(parent_id) REFERENCES DonVi(id)
    )
    """)

    # Bảng Người
    c.execute("""
    CREATE TABLE IF NOT EXISTS Nguoi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ten TEXT NOT NULL,
        anh_mat TEXT,
        don_vi_id INTEGER NOT NULL,
        FOREIGN KEY(don_vi_id) REFERENCES DonVi(id)
    )
    """)

    # Bảng Xe
    c.execute("""
    CREATE TABLE IF NOT EXISTS Xe (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bien_so TEXT NOT NULL,
        nguoi_id INTEGER NOT NULL,
        FOREIGN KEY(nguoi_id) REFERENCES Nguoi(id)
    )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
