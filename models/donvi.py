from db.database import get_conn

class DonVi:
    @staticmethod
    def add(ten, cap, parent_id=None):
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO DonVi (ten, cap, parent_id) VALUES (?, ?, ?)", (ten, cap, parent_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update(id, ten):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE DonVi SET ten=? WHERE id=?", (ten, id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM DonVi WHERE id=?", (id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_cap(cap, parent_id=None):
        conn = get_conn()
        c = conn.cursor()
        if parent_id:
            c.execute("SELECT id, ten FROM DonVi WHERE cap=? AND parent_id=?", (cap, parent_id))
        else:
            c.execute("SELECT id, ten FROM DonVi WHERE cap=?", (cap,))
        result = c.fetchall()
        conn.close()
        return result

    @staticmethod
    def get_all():
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, ten, cap, parent_id FROM DonVi ORDER BY cap, id")
        result = c.fetchall()
        conn.close()
        return result
