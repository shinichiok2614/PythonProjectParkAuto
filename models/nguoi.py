from db.database import get_conn

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
        c.execute("DELETE FROM Nguoi WHERE id=?", (id,))
        c.execute("DELETE FROM Xe WHERE nguoi_id=?", (id,))
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
