# FIT CLUB'S DAY 2026

Dự án quản lý và điểm danh tự động qua mã QR cho sự kiện **FIT CLUB'S DAY 2026** (Khoa Công nghệ Thông tin - Trường Đại học Sư phạm Kỹ thuật TP.HCM - HCMUTE).

## Production URL

- **Landing Page:** https://event.hcmutertic.com/landingpage
- **Backend API Base URL:** `https://event.hcmutertic.com`
- **Swagger API Docs:** https://event.hcmutertic.com/docs
- **ReDoc API Docs:** https://event.hcmutertic.com/redoc

## Cấu trúc dự án

- `landingpage.html`: Giao diện landing page chính thức của sự kiện (phục vụ tại `/landingpage`).
- `backend/`: FastAPI backend xác thực Google OAuth, quản lý sự kiện và gian hàng CLB, phân quyền admin theo CLB, QR cá nhân và xuất nhập Excel.
- `frontend/`: Dashboard sáng, xanh navy tại `/`: tổng quan sự kiện / CLB, người tham gia, camera / ảnh QR, vé cá nhân và quản trị. HTML/CSS/JavaScript thuần, không cần bước build.
- `assets/`: Bộ nhận diện, banner, logo các CLB học thuật và poster sự kiện.
- `content/`: Thông tin sự kiện và tài liệu giới thiệu.

## Mô hình nhiều câu lạc bộ

**Sự kiện → gian hàng CLB → admin / danh sách / điểm danh riêng.** Superadmin điều phối toàn sự kiện; admin chỉ quản lý CLB được gán. Một sinh viên có thể tham gia nhiều CLB và có kết quả độc lập tại mỗi gian hàng.

Superadmin tạo sự kiện, tạo các CLB và gán admin bằng email. Admin thêm hoặc nhập danh sách cho từng CLB. Khi cả sự kiện và gian hàng đã mở điểm danh, sinh viên mở vé của CLB đó và đưa QR cho admin quét. QR tự làm mới sau thời hạn hiệu lực.

Xem [hướng dẫn API và vận hành](backend/README.md) và [rà soát BA-Kit, tiêu chí nghiệm thu, backlog](docs/BA_REVIEW.md).

## Vận hành

Môi trường chính tại `event.hcmutertic.com` chạy trên máy ứng dụng `192.168.1.17`, qua Nginx tại `192.168.1.80`; triển khai trực tiếp bằng SSH. Xem [cài release, SSL, cấu hình Google và rollback](docs/DEPLOYMENT.md). `.env` thật được tạo riêng trên server và không nằm trong repository.
