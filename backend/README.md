# FIT Club Day — FastAPI backend

## Production Backend URL

- **API Base URL:** `https://fit.caohoangphuc.id.vn`
- **Swagger UI:** https://fit.caohoangphuc.id.vn/docs
- **ReDoc:** https://fit.caohoangphuc.id.vn/redoc

## Chạy local

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Thay JWT_SECRET (ít nhất 32 ký tự ngẫu nhiên), GOOGLE_CLIENT_ID và SUPERADMIN_EMAILS.
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger local: http://localhost:8000/docs. Đây là backend API; giao diện landing page và màn hình camera sẽ tích hợp sau.

Google Cloud: tạo OAuth client loại Web application; thêm Authorized JavaScript origins của frontend. Frontend dùng Google Identity Services lấy `credential` (ID token), gửi POST `/auth/google` với JSON `{"credential":"..."}`. Backend xác minh chữ ký, audience, issuer, hạn token bằng google-auth; yêu cầu `email_verified=true`, `hd=student.hcmute.edu.vn`, email khớp MSSV số 6–15 ký tự. Không có mật khẩu hay API đăng nhập giả trong ứng dụng. Họ tên lấy từ Google, MSSV lấy phần trước @. Thư viện xác minh cần truy cập chứng thư Google qua internet.

Token trả về dùng `Authorization: Bearer <access_token>`. Hết phiên sau 60 phút; đăng nhập Google lại. Không lưu token vào URL. Khi triển khai dùng HTTPS và cấu hình CORS đúng origin.

## Vai trò

- Superadmin: email nằm trong `SUPERADMIN_EMAILS` (ngăn cách dấu phẩy); cũng phải đăng nhập Google bằng email sinh viên. Cấu hình này không tự tạo người dùng, không bỏ qua xác thực.
- Admin: được superadmin gán theo sự kiện. Admin có thể là sinh viên ở sự kiện khác. Kiểm tra quyền đọc từ DB trong từng request.
- Sinh viên: chỉ thấy sự kiện đã được thêm vào; nhận QR của chính mình khi mở điểm danh.

## API chính

| Method | Path | Chức năng |
|---|---|---|
| POST | /auth/google | Xác minh Google ID token, tạo/cập nhật tên |
| GET | /auth/me | Danh tính, vai trò, sự kiện quản trị |
| POST | /events | Superadmin tạo sự kiện |
| PUT | /events/{id} | Superadmin cập nhật toàn bộ thông tin / mở đóng điểm danh |
| GET | /events | Danh sách sự kiện có quyền truy cập |
| POST / GET | /events/{id}/admins | Superadmin gán / xem admin |
| DELETE | /events/{id}/admins/{user_id} | Thu hồi admin |
| POST | /events/{id}/students | Thêm sinh viên vào sự kiện |
| GET | /events/{id}/students/template | Download mẫu XLSX trống |
| POST | /events/{id}/students/import | Upload multipart field `file` |
| GET | /events/{id}/students | Danh sách + kết quả điểm danh, tìm MSSV |
| GET | /events/{id}/qr | QR của sinh viên, PNG base64 + token |
| POST | /events/{id}/attendance/scan | Admin gửi `{"token":"nội dung QR"}` |
| GET | /events/{id}/attendance/export | Xuất XLSX kết quả |

Danh sách hỗ trợ `search` theo MSSV, `attended=true/false`, `offset`, `limit` tối đa 500. Export dùng cùng bộ lọc search/attended, xuất toàn bộ các dòng phù hợp. Thời gian lưu/ xuất UTC; frontend hiển thị Asia/Ho_Chi_Minh.

Ví dụ tạo sự kiện (Bearer của superadmin):

```json
{
  "title": "FIT CLUB’S DAY 2026",
  "description": "Liên hoan các CLB học thuật và Sinh viên 5 tốt khoa CNTT",
  "image_url": "/assets/fit-club-day-background-clean.webp",
  "starts_at": "2026-10-17T08:00:00+07:00",
  "checkin_open": false
}
```

Thêm admin/sinh viên bằng `{"email":"23110001@student.hcmute.edu.vn","name":"Nguyễn Văn A"}`. Có thể thêm trước khi tài khoản đăng nhập Google lần đầu. Import không đổi tên của tài khoản đã có.

## Excel

Download mẫu theo API, có 3 cột theo thứ tự `student_id`, `full_name`, `email`. Giữ MSSV dạng Text để không mất số 0; email có thể để trống, hệ thống suy ra từ MSSV. Không thêm cột. File tối đa 5 MB, 10.000 dòng; giới hạn giải nén 30 MB. Dòng trống bỏ qua. Lỗi dữ liệu trả số dòng và không nhập dòng nào; trùng trong file hoặc đã có trong sự kiện được báo riêng và bỏ qua. Trùng ở sự kiện khác vẫn được thêm vào sự kiện hiện tại. Export tên người dùng luôn là chuỗi, không thực thi công thức Excel.

## QR và điểm danh

QR JWT có mục đích riêng `checkin`, gắn user/event, hạn mặc định 120 giây; frontend tạo lại khi hết hạn. Chỉ sinh viên đã được thêm mới lấy được QR. Superadmin bật `checkin_open` khi bắt đầu; đóng sau khi kết thúc. Admin đọc QR bằng camera phía frontend, gửi token cho API. API kiểm quyền sự kiện, trạng thái mở, chữ ký, hạn và đăng ký trước khi ghi. Unique constraint chống ghi hai lần, quét lặp trả bản ghi cũ. Có thời điểm và người quét để truy vết. QR không chứa email/họ tên. QR có thể được chia sẻ trong thời hạn ngắn; nếu cần kiểm tra trực tiếp, giao diện admin đối chiếu họ tên/MSSV trả về khi quét.

## Kiểm thử

```sh
.venv/bin/pytest -q
```

Các test mock xác minh Google trong môi trường test. Đăng nhập Google thật cần OAuth client của bạn; không thể kiểm thử end-to-end khi chưa có cấu hình đó.

SQLite cho phát triển và vận hành nhỏ, dữ liệu tại `fitclub.db`. Trước triển khai nhiều instance: chuyển PostgreSQL (cài psycopg), thêm migration Alembic và backup DB. Không dùng create_all để nâng cấp schema đang có dữ liệu; hiện create_all chỉ tạo schema mới.

Tài liệu đối chiếu: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token và https://fastapi.tiangolo.com/reference/security/.

## Thêm superadmin

Superadmin khởi tạo: `24110303@student.hcmute.edu.vn` (đã cấu hình trong `.env`).

- `POST /superadmins`: JSON `{ "email": "24110001@student.hcmute.edu.vn", "name": "Họ tên" }` để cấp quyền; có thể cấp trước lần đăng nhập đầu tiên.
- `GET /superadmins`: danh sách tài khoản và email khởi tạo.
- `DELETE /superadmins/{user_id}`: thu hồi quyền được cấp qua DB; hiệu lực ngay cả với access token còn hạn. Không xóa quyền bootstrap qua API, quản lý danh sách bootstrap bằng `.env` để tránh khóa quản trị.

Chỉ superadmin được gọi các endpoint này. Tất cả superadmin vẫn phải dùng Google sinh viên đã xác minh.
