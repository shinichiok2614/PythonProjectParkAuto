from db.database import get_conn
from models import donvi

def get_donvi_fullname_static(id, ten, cap, parent_id):
    names = [f"{ten} (C{cap})"]
    pid = parent_id

    while pid:
        conn = donvi.get_conn()
        c = conn.cursor()
        c.execute("SELECT id, ten, cap, parent_id FROM DonVi WHERE id=?", (pid,))
        parent = c.fetchone()
        conn.close()
        if parent:
            names.insert(0, f"{parent[1]} (C{parent[2]})")
            pid = parent[3]
        else:
            break
    return " - ".join(names)


class Nguoi:
    @staticmethod
    def add(ten, anh_mat, don_vi_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO Nguoi (ten, anh_mat, don_vi_id) VALUES (?, ?, ?)", (ten, anh_mat, don_vi_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update(id, ten, anh_mat, don_vi_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE Nguoi SET ten=?, anh_mat=?, don_vi_id=? WHERE id=?", (ten, anh_mat, don_vi_id, id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM Xe WHERE nguoi_id=?", (id,))
        c.execute("DELETE FROM Nguoi WHERE id=?", (id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_all():
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT Nguoi.id, Nguoi.ten, Nguoi.anh_mat, DonVi.ten
            FROM Nguoi
            JOIN DonVi ON Nguoi.don_vi_id = DonVi.id
        """)
        result = c.fetchall()
        conn.close()
        return result

    @staticmethod
    def get_all_full():
        """
        Trả về danh sách (id, ten, anh, donvi_fullname, cap)
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
                  SELECT N.id, N.ten, N.anh_mat, D.id, D.ten, D.cap, D.parent_id
                  FROM Nguoi N
                           JOIN DonVi D ON N.don_vi_id = D.id
                  """)
        rows = c.fetchall()
        conn.close()

        result = []
        for r in rows:
            donvi_fullname = get_donvi_fullname_static(r[3], r[4], r[5], r[6])
            result.append((r[0], r[1], r[2], donvi_fullname, r[5]))
        return result

