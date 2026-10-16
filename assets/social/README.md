# Ảnh chia sẻ FIT Club Day

`fit-club-day-2026-v1.png` là ảnh Open Graph/Twitter Card 1200 × 630, phục vụ công khai qua `/assets/social/`. Hai trang `/` và `/landingpage` khai báo metadata trực tiếp trong HTML để trình đọc link không cần chạy JavaScript.

File `fit-club-day-2026.html` là bản bố cục dùng tạo ảnh: mở bằng Chromium ở viewport 1200 × 630, device scale factor 1, chờ toàn bộ ảnh tải xong rồi chụp viewport PNG. Không cần render lại ảnh ở runtime.

Các logo gốc từ `assets/brand/` và `assets/bo-logo/ban-cat-goc/` chỉ được đặt vào bố cục và co giãn đúng tỷ lệ; file nguồn không thay đổi. Khi đổi ảnh chia sẻ, tạo tên phiên bản mới và cập nhật URL tuyệt đối trong metadata của cả hai trang.
