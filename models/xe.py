from db.database import get_conn

class Xe:
    @staticmethod
    def add(bien_so, nguoi_id):
        """
        Thêm xe mới
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO Xe (bien_so, nguoi_id) VALUES (?, ?)", (bien_so, nguoi_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update(xe_id, bien_so, nguoi_id):
        """
        Cập nhật thông tin xe
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE Xe SET bien_so=?, nguoi_id=? WHERE id=?", (bien_so, nguoi_id, xe_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(xe_id):
        """
        Xóa xe theo ID
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM Xe WHERE id=?", (xe_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_all():
        """
        Lấy danh sách xe kèm tên người sở hữu
        Trả về: (id, bien_so, nguoi_id, nguoi_ten)
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT X.id, X.bien_so, N.id, N.ten
            FROM Xe X
            JOIN Nguoi N ON X.nguoi_id = N.id
            ORDER BY X.id
        """)
        result = c.fetchall()
        conn.close()
        return result

    @staticmethod
    def get_by_nguoi(nguoi_id):
        """
        Lấy danh sách xe của 1 người cụ thể
        """
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, bien_so FROM Xe WHERE nguoi_id=? ORDER BY id", (nguoi_id,))
        result = c.fetchall()
        conn.close()
        return result
