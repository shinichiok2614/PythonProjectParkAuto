from db.database import get_conn

class Xe:
    @staticmethod
    def add(bien_so, nguoi_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO Xe (bien_so, nguoi_id) VALUES (?, ?)", (bien_so, nguoi_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update(id, bien_so):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE Xe SET bien_so=? WHERE id=?", (bien_so, id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM Xe WHERE id=?", (id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_nguoi(nguoi_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, bien_so FROM Xe WHERE nguoi_id=?", (nguoi_id,))
        result = c.fetchall()
        conn.close()
        return result
