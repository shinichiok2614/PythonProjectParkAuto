Để dự án quản lý bãi giữ xe của bạn gọn gàng, dễ bảo trì và mở rộng (như các phần nhận diện xe/người, quản lý cơ sở dữ liệu, báo cáo), bạn nên chia thành nhiều file/module theo chức năng. Dưới đây là gợi ý cấu trúc:

1️⃣ Cấu trúc thư mục đề xuất
ParkID/                  # Thư mục gốc project
│
├─ main.py               # File chính để chạy ứng dụng GUI
├─ db/
│   ├─ __init__.py
│   └─ database.py       # Khởi tạo DB, kết nối, các hàm CRUD chung
│
├─ models/
│   ├─ __init__.py
│   ├─ nguoi.py           # Model Nguoi + CRUD
│   ├─ xe.py              # Model Xe + CRUD
│   └─ donvi.py           # Model DonVi + CRUD
│
├─ gui/
│   ├─ __init__.py
│   ├─ nguoi_gui.py       # GUI thêm/sửa/xóa người
│   ├─ xe_gui.py          # GUI quản lý xe theo người
│   ├─ donvi_gui.py       # GUI quản lý đơn vị (cấp 1,2,3)
│   └─ main_gui.py        # GUI chính kết hợp các phần
│
├─ recognition/
│   ├─ __init__.py
│   ├─ face_recog.py      # Nhận diện khuôn mặt người
│   └─ plate_recog.py     # Nhận diện biển số xe
│
├─ reports/
│   ├─ __init__.py
│   └─ export_report.py   # Xuất báo cáo ngày/tháng
│
└─ resources/
    └─ images/            # Lưu ảnh mặt người, logo, icon

2️⃣ Vai trò từng file
File	Chức năng
main.py	Entry point: chạy GUI chính main_gui.py
database.py	Kết nối SQLite, khởi tạo DB, các hàm helper chung
nguoi.py	CRUD: thêm, sửa, xoá người, lấy danh sách người
xe.py	CRUD: thêm, sửa, xoá xe, lấy xe theo người
donvi.py	CRUD: thêm, sửa, xoá đơn vị, load cấp 1→2→3
nguoi_gui.py	GUI quản lý người, dropdown chọn đơn vị, chọn ảnh mặt
xe_gui.py	GUI quản lý xe: danh sách xe theo người
donvi_gui.py	GUI quản lý đơn vị (thêm/xóa/sửa cấp 1,2,3)
main_gui.py	Kết hợp tất cả GUI, tab người/xe/đơn vị
face_recog.py	Nhận diện khuôn mặt vào ra cổng
plate_recog.py	Nhận diện biển số xe vào ra cổng hoặc trong bãi
export_report.py	Xuất báo cáo theo ngày, tháng, theo người/xe
3️⃣ Ưu điểm của cấu trúc này

Tách bạch chức năng: GUI riêng, model riêng, nhận diện riêng → dễ debug và test.

Dễ mở rộng: Sau này thêm module AI hoặc quản lý thẻ từ, camera, báo cáo nâng cao.

Tái sử dụng: Model CRUD và database có thể dùng lại cho GUI hoặc nhận diện.

pip install pillow
pip install opencv-python==4.12.0.88
pip install ultralytics
pip install onnxruntime
pip install deep-sort-realtime
pip install fast-plate-ocr[onnx]

Bạn đang gặp xung đột phụ thuộc giữa:

❌ fast-plate-ocr → yêu cầu opencv-python-headless
❌ opencv-python (GUI) → mới cài → cần numpy >= 2
❌ môi trường bạn đang dùng → numpy 1.26.4

==> Đây là lý do gây lỗi imshow / waitKey

✅ Giải pháp đúng: TÁCH 2 MÔI TRƯỜNG

Không thể vừa dùng fast-plate-ocr (headless) vừa dùng OpenCV GUI trong cùng 1 venv → luôn xung đột.

👉 Bạn chọn 1 trong 2 cách:
🟩 CÁCH 1 – Dùng OpenCV GUI + Tự OCR biển số (không dùng fast-plate-ocr)

→ làm bãi xe thì tốt nhất dùng YOLO + PaddleOCR hoặc EasyOCR
→ KHÔNG phụ thuộc opencv-headless

Fix như sau:

1. Gỡ hết OpenCV & fast-plate-ocr
pip uninstall -y opencv-python-headless
pip uninstall -y fast-plate-ocr
pip uninstall -y opencv-python
pip uninstall -y opencv-contrib-python

2. Cài lại OpenCV GUI đúng phiên bản
pip install opencv-python==4.8.0.76
pip install opencv-contrib-python==4.8.0.76

3. Cài OCR thay thế:
pip install paddleocr


hoặc:

pip install easyocr


➡️ Đây là cách tốt nhất cho ứng dụng bãi xe real-time.

🟦 CÁCH 2 – Giữ fast-plate-ocr nhưng KHÔNG dùng imshow()

fast-plate-ocr bắt buộc phải dùng opencv-headless → bạn không thể dùng GUI của OpenCV.

Nên phải bỏ cv2.imshow() và dùng GUI loại khác:
✔ Tkinter Canvas
✔ PyQt5 QLabel
✔ Pygame
✔ Custom window (fastest)

Fix đơn giản nhất: dùng Tkinter hiển thị:

from PIL import Image, ImageTk

img = ImageTk.PhotoImage(Image.fromarray(frame))
label.configure(image=img)
label.image = img


➡️ Không cần OpenCV GUI → không lỗi waitKey

🟥 Nếu bạn muốn giữ cả 2 (GUI + fast-plate-ocr)?

Không được vì:

fast-plate-ocr requires opencv-python-headless
opencv-python GUI conflicts with opencv-python-headless


Hai thằng này không thể cùng tồn tại trong 1 môi trường.

📌 Tóm tắt hướng giải quyết
Mục đích	Cài gì	Không cài gì
Real-time camera + GUI	opencv-python + paddleocr	fast-plate-ocr, headless
Chạy headless server OCR	fast-plate-ocr + opencv-python-headless	imshow, waitKey
🔥 Tôi đề xuất cho ứng dụng bãi xe:
✔ YOLO + DeepSORT
✔ OCR = PaddleOCR
✔ OpenCV GUI = OK

→ Chạy mượt, không xung đột, chính xác cao.

Nếu bạn muốn tôi chỉnh lại code cam_baiXe.py theo hướng không dùng fast-plate-ocr, bạn chỉ cần gửi file, tôi sẽ sửa gọn – chạy ổn định 100%.

Giải thích 3 dòng này:

car_frame = tk.Frame(preview_frame, width=CAR_W, height=CAR_H)
car_frame.pack(side=tk.LEFT, padx=2, pady=2)
car_frame.pack_propagate(False)

✅ 1. car_frame = tk.Frame(preview_frame, width=CAR_W, height=CAR_H)

Tạo một frame con nằm trong preview_frame, đồng thời đặt kích thước cố định:

width = CAR_W → chiều rộng khung hiển thị xe

height = CAR_H → chiều cao khung hiển thị xe

Frame mặc định không cố định kích thước, nó sẽ co giãn theo widget con, nhưng bước 3 sẽ xử lý.

✅ 2. car_frame.pack(side=tk.LEFT, padx=2, pady=2)

Đặt frame nằm bên trái trong bố cục ngang

Chừa khoảng cách 2px ở trái/phải/trên/dưới

✅ 3. car_frame.pack_propagate(False)

Đây là dòng cực kỳ quan trọng.

Tkinter có cơ chế geometry propagation:

👉 Mặc định Frame sẽ tự co lại đúng bằng kích thước widget con của nó.
→ Tức là nếu bạn nhét ảnh 100×50 vào, frame cũng tự động thu về 100×50.

Điều này khiến việc cố định khung preview hoàn toàn thất bại.

🔥 pack_propagate(False) = KHÓA kích thước Frame

Khi bạn đặt:

car_frame.pack_propagate(False)


=> Tkinter không được phép thay đổi kích thước frame, dù ở trong có ảnh to hay nhỏ.

→ Frame sẽ giữ đúng kích thước CAR_W × CAR_H.

→ Đây là điều bắt buộc để video/ảnh scale đúng vào khung mà bạn muốn.

🎯 Kết quả sau 3 dòng lệnh:

Frame có kích thước cố định, không bị thay đổi

Ảnh/video bạn đưa vào sẽ được resize theo đúng khung

GUI preview luôn đẹp, bố cục luôn ổn định

✅ CẤU TRÚC MỚI (chuẩn và dễ bảo trì)
project/
│
├── cam/
│   ├── camera_manager.py        # vòng lặp camera + show video
│   ├── plate_detector.py        # YOLO detect biển số
│   ├── plate_ocr.py             # fast_plate_ocr xử lý OCR
│   ├── tracker.py               # deep sort (nếu đang dùng)
│   └── drawer.py                # vẽ bounding box, preview, overlay
│
├── services/
│   ├── parking_service.py       # logic xử lý vào/ra, lưu kết quả
│   └── image_service.py         # crop ảnh, resize, chuyển định dạng
│
├── gui/
│   └── display.py               # UI hiển thị frame (nếu dùng Tkinter)
│
├── models/
│   └── xe_model.py              # model Xe (nếu bạn có DB)
│
└── cam_baixe.py                 # file chính gọi các module

Trong Tkinter, thuộc tính relief dùng để xác định kiểu viền (border style) của một widget, giúp tạo hiệu ứng nổi, lõm hay phẳng cho widget đó.

Cụ thể, relief=tk.SUNKEN có nghĩa là widget sẽ có hiệu ứng "lõm vào", tức là trông như bị nhấn xuống so với bề mặt xung quanh.

Các giá trị thường dùng của relief:

Giá trị	Hiệu ứng
flat	Không có viền, phẳng
raised	Nổi lên, giống nút bấm
sunken	Lõm xuống, giống vùng hiển thị đã được nhấn
groove	Viền rãnh (groove)
ridge	Viền nổi (ridge)
solid	Viền đặc

Ví dụ:

import tkinter as tk

root = tk.Tk()
frame = tk.Frame(root, width=200, height=100, relief=tk.SUNKEN, borderwidth=2)
frame.pack(padx=10, pady=10)
root.mainloop()


Kết quả: bạn sẽ thấy frame lõm xuống so với cửa sổ, nhìn giống một khung hiển thị.

Trong code của bạn, relief=tk.SUNKEN được dùng cho Label preview xe, biển số, và mặt để tạo hiệu ứng khung hiển thị, giúp người dùng nhận biết vùng hiển thị nội dung.

Nếu bạn muốn, mình có thể giải thích sự khác nhau giữa SUNKEN, RAISED và GROOVE trực quan bằng hình minh họa


