import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Image
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm


# =============================
# PDF REPORT
# =============================
def create_pdf_report(entries, output_path):
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []

    # Title
    elements.append(Paragraph("<b>BÁO CÁO XE TRONG BÃI</b>", styles["Title"]))
    elements.append(Paragraph(
        f"Ngày giờ lập báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        styles["Normal"]
    ))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Table
    table_data = [["STT", "Car ID", "Biển số", "Thời gian"]]
    for i, e in enumerate(entries, start=1):
        table_data.append([
            i,
            e["car_id"],
            e["plate"],
            e["timestamp"]
        ])

    table = Table(table_data, colWidths=[2*cm, 3*cm, 4*cm, 5*cm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
    ]))

    elements.append(table)
    elements.append(Paragraph("<br/>", styles["Normal"]))
    elements.append(Paragraph(
        f"Tổng số xe: <b>{len(entries)}</b>",
        styles["Normal"]
    ))

    # Images
    elements.append(Paragraph("<br/><b>Hình ảnh xe</b>", styles["Heading2"]))

    for e in entries:
        if e["car_path"] and os.path.exists(e["car_path"]):
            try:
                img = Image(e["car_path"], width=6*cm, height=4*cm)
                elements.append(img)
                elements.append(Paragraph(
                    f"Car ID: {e['car_id']} - Biển số: {e['plate']}",
                    styles["Normal"]
                ))
                elements.append(Paragraph("<br/>", styles["Normal"]))
            except:
                pass

    doc.build(elements)


# =============================
# TKINTER APP
# =============================
class ReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Báo cáo xe trong bãi (PDF)")
        self.root.geometry("750x500")

        self.db_path = None
        self.entries = []

        # --- DB selection ---
        top = tk.Frame(root)
        top.pack(fill=tk.X, pady=6)

        self.db_entry = tk.Entry(top)
        self.db_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        tk.Button(top, text="Chọn DB", command=self.choose_db).pack(side=tk.LEFT, padx=6)
        tk.Button(top, text="Xuất PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=6)

        # --- Treeview ---
        columns = ("car_id", "plate", "time")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        self.tree.heading("car_id", text="Car ID")
        self.tree.heading("plate", text="Biển số")
        self.tree.heading("time", text="Thời gian")

        self.tree.column("car_id", width=80)
        self.tree.column("plate", width=140)
        self.tree.column("time", width=180)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    # ---------------------
    def choose_db(self):
        path = filedialog.askopenfilename(
            title="Chọn plates.db",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")]
        )
        if not path:
            return

        self.db_path = path
        self.db_entry.delete(0, tk.END)
        self.db_entry.insert(0, path)
        self.load_data()

    # ---------------------
    def load_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT car_id, plate, car_path, plate_path, timestamp
                FROM detected_logs
                ORDER BY timestamp ASC
            """)
            rows = cur.fetchall()
            conn.close()

            self.entries.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

            for r in rows:
                entry = {
                    "car_id": r[0],
                    "plate": r[1],
                    "car_path": r[2],
                    "plate_path": r[3],
                    "timestamp": r[4]
                }
                self.entries.append(entry)
                self.tree.insert("", tk.END, values=(r[0], r[1], r[4]))

            messagebox.showinfo("OK", f"Đã tải {len(self.entries)} bản ghi")

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    # ---------------------
    def export_pdf(self):
        if not self.entries:
            messagebox.showwarning("Thông báo", "Không có dữ liệu để xuất")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"bao_cao_xe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not save_path:
            return

        try:
            create_pdf_report(self.entries, save_path)
            messagebox.showinfo("Thành công", f"Đã tạo báo cáo:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))


# =============================
if __name__ == "__main__":
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()
