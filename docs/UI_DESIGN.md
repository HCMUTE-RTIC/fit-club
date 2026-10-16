# Giao diện FIT Club Day

Hướng thiết kế theo phản hồi ngày 16/10/2026: giao diện phục vụ đăng ký và điểm danh, cần rõ thao tác và thoáng trên điện thoại.

- Nền sáng, chữ tối, navy dùng cho thao tác và trạng thái được chọn. Giữ nguyên file logo gốc.
- Bỏ banner gradient, hình trang trí, slogan và các khối hướng dẫn lặp lại trong dashboard.
- Danh sách CLB hiển thị theo hàng: logo, tên, mô tả và nút Đăng ký / Xem vé. Đang nhận đăng ký khác với đang mở điểm danh.
- Vé phân biệt Đã đăng ký, Chờ điểm danh, Sẵn sàng điểm danh và Đã điểm danh. Đăng ký không tự tạo lượt điểm danh; gian hàng đóng có hướng dẫn, không coi đăng ký thành công là cảnh báo lỗi.
- Nút mở QR đặt trước khung mã, không bắt người dùng cuộn qua một ô trống. Khi bấm trên mobile, đưa mã vào giữa vùng nhìn thấy; làm mới tự động không tự cuộn trang.
- Bộ chọn sự kiện / CLB được ẩn khi không có lựa chọn khác, nhưng giữ tên phạm vi đang quản lý trên màn hình. Mobile bỏ đoạn mô tả lặp ở đầu trang và dùng chữ nội dung dễ đọc hơn.
- Tổng quan CLB ưu tiên Mở điểm danh / Quét QR và Xem danh sách trước số liệu. Mở điểm danh chỉ tác động CLB đã chọn, yêu cầu thao tác chủ động; sự kiện đóng sẽ chặn nút và nêu lý do. Superadmin có đường dẫn sang quản trị để mở sự kiện.
- Số liệu, tiến độ và các lượt điểm danh đặt sau thao tác chính. Các panel không bị kéo cao theo nhau khi nội dung ít.
- Hướng dẫn thu gọn bằng disclosure; người dùng mở khi cần. Form, bảng và scanner dùng chung hệ thống nút và khoảng cách.
- Mobile dùng thanh điều hướng dưới, có khoảng trống cho safe area. Danh sách người tham gia chuyển thành từng hàng thông tin, giữ tên, email, MSSV và trạng thái dễ đọc; không kéo ngang toàn trang. Điều hướng sang màn khác đưa nội dung về đầu trang.

CSS được tổ chức lại theo thành phần và màn hình, không chồng thêm lớp sửa lên các breakpoint cũ. Bằng chứng giao diện nằm trong `docs/previews/`; dữ liệu trên ảnh là dữ liệu kiểm thử.
