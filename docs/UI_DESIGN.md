# Giao diện FIT Club Day

Hướng thiết kế theo phản hồi ngày 16/10/2026: giao diện phục vụ đăng ký và điểm danh, cần rõ thao tác và thoáng trên điện thoại.

- Nền sáng, chữ tối, navy dùng cho thao tác và trạng thái được chọn. Giữ nguyên file logo gốc.
- Bỏ banner gradient, hình trang trí, slogan và các khối hướng dẫn lặp lại trong dashboard.
- Danh sách CLB hiển thị theo hàng: logo, tên, mô tả, trạng thái điểm danh và nút tham gia / xem vé.
- Sinh viên có một sự kiện không cần chọn lại sự kiện trên Tổng quan. Màn Vé vẫn có bộ chọn CLB; nhiều sự kiện vẫn có bộ chọn sự kiện.
- Tổng quan quản trị dùng một dải số liệu, tiến độ và các lượt điểm danh gần đây. Tên CLB đang quản lý hiển thị rõ ở đầu nội dung.
- Hướng dẫn thu gọn bằng disclosure; người dùng mở khi cần. Form, bảng và scanner dùng chung hệ thống nút và khoảng cách.
- Mobile dùng thanh điều hướng dưới, có khoảng trống cho safe area. Danh sách người tham gia chuyển thành từng hàng thông tin, giữ tên, email, MSSV và trạng thái dễ đọc; không kéo ngang toàn trang. Điều hướng sang màn khác đưa nội dung về đầu trang.

CSS được tổ chức lại theo thành phần và màn hình, không chồng thêm lớp sửa lên các breakpoint cũ. Bằng chứng giao diện nằm trong `docs/previews/`; dữ liệu trên ảnh là dữ liệu kiểm thử.
