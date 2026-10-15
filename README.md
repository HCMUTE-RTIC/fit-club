# FIT CLUB'S DAY 2026

Dự án quản lý và điểm danh tự động qua mã QR cho sự kiện **FIT CLUB'S DAY 2026** (Khoa Công nghệ Thông tin - Trường Đại học Sư phạm Kỹ thuật TP.HCM - HCMUTE).

## Production URL

- **Backend API Base URL:** `https://fit.caohoangphuc.id.vn`
- **Swagger API Docs:** https://fit.caohoangphuc.id.vn/docs
- **ReDoc API Docs:** https://fit.caohoangphuc.id.vn/redoc

## Cấu trúc dự án

- `backend/`: FastAPI backend xác thực Google OAuth (email sinh viên `@student.hcmute.edu.vn`), tạo & xác thực mã QR cá nhân, quản lý sự kiện và xuất nhập Excel điểm danh.
- `frontend/`: Giao diện web hỗ trợ camera quét QR và các tính năng admin / sinh viên.
- `assets/`: Bộ nhận diện, banner, logo các CLB học thuật và poster sự kiện.
- `content/`: Thông tin sự kiện và tài liệu giới thiệu.
