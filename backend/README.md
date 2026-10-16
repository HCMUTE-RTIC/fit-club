# FIT Club Day — FastAPI backend

## Production Backend URL

- **API Base URL:** `https://event.hcmutertic.com`
- **Swagger UI:** https://event.hcmutertic.com/docs
- **ReDoc:** https://event.hcmutertic.com/redoc

## Chạy local

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Thay JWT_SECRET (ít nhất 32 ký tự ngẫu nhiên), GOOGLE_CLIENT_ID và SUPERADMIN_EMAILS.
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger local: http://localhost:8000/docs. Dashboard tại http://localhost:8000/; landing page giới thiệu tại `/landingpage`.

Google Cloud: tạo OAuth client loại Web application; thêm Authorized JavaScript origins của frontend. Frontend dùng Google Identity Services lấy `credential` (ID token), gửi POST `/auth/google` với JSON `{"credential":"..."}`. Backend xác minh chữ ký, audience, issuer, hạn token và `email_verified=true`. Sinh viên dùng email MSSV số 6–15 ký tự và `hd=student.hcmute.edu.vn`; email ngoài trường chỉ được đăng nhập trong chế độ nghiêm ngặt khi đã được cấp quyền admin/superadmin hoặc có trong bootstrap. Không có mật khẩu hay API đăng nhập giả. Họ tên lấy từ Google; email ngoài trường có mã tài khoản ổn định, không phải MSSV. Thư viện xác minh cần truy cập chứng thư Google qua internet.

Token trả về dùng `Authorization: Bearer <access_token>`. Hết phiên sau 60 phút; đăng nhập Google lại. Không lưu token vào URL. Khi triển khai dùng HTTPS và cấu hình CORS đúng origin.

## Vai trò

- Superadmin: email bootstrap nằm trong `SUPERADMIN_EMAILS` hoặc được superadmin khác cấp quyền. Có thể dùng Gmail đã xác minh; cấu hình không bỏ qua xác thực Google.
- Admin: được superadmin gán theo CLB; có thể dùng email Google ngoài trường đã được cấp quyền. Quyền được đọc từ DB trong từng request.
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

Superadmin khởi tạo của môi trường `event.hcmutertic.com`: `hovietanh147@gmail.com`, cấu hình trong `.env` riêng trên server.

- `POST /superadmins`: JSON `{ "email": "24110001@student.hcmute.edu.vn", "name": "Họ tên" }` để cấp quyền; có thể cấp trước lần đăng nhập đầu tiên.
- `GET /superadmins`: danh sách tài khoản và email khởi tạo.
- `DELETE /superadmins/{user_id}`: thu hồi quyền được cấp qua DB; hiệu lực ngay cả với access token còn hạn. Không xóa quyền bootstrap qua API, quản lý danh sách bootstrap bằng `.env` để tránh khóa quản trị.

Chỉ superadmin được gọi các endpoint này. Tất cả tài khoản vẫn phải đăng nhập qua Google có email đã xác minh. API `POST /access/grants` hỗ trợ cấp quyền chỉ bằng email và vai trò; admin cần thêm `event_id` và `club_id`. Xem [runbook môi trường mới](../docs/DEPLOYMENT.md).

## FIT Club Day: nhiều gian hàng CLB

Dashboard hiện dùng API CLB. Các bảng mới `event_clubs`, `club_admins`, `club_registrations`, `club_attendance` bổ sung vào schema hiện có; không đổi hoặc xóa bản ghi điểm danh cũ. Sao lưu DB trước khi triển khai phiên bản mới.

### Phân quyền và quy tắc

- Superadmin tạo CLB, gán / thu hồi admin và xem tổng hợp toàn sự kiện.
- Admin CLB chỉ đọc danh sách, thêm/import sinh viên, xuất kết quả và quét QR của CLB được gán. Có thể gán một người cho nhiều CLB.
- Sinh viên chỉ thấy các gian hàng đã được thêm vào; có vé và trạng thái tham gia riêng cho từng CLB. Không tự đăng ký qua dashboard.
- Một lần điểm danh hợp lệ tại RTIC không xác nhận tham gia DSC. QR dùng `kind=club_checkin`, gắn cả `event_id` và `club_id`; không hoán đổi được với access token hoặc QR API cũ.
- Sự kiện và CLB đều phải mở thì mới tạo QR hoặc quét được. Superadmin điều khiển sự kiện; admin CLB có thể mở/đóng gian hàng mình.
- Khi sự kiện đã có ít nhất một CLB, mọi API quản trị danh sách / điểm danh toàn sự kiện cũ chỉ còn dành cho superadmin. Quyền `EventAdmin` cũ không thể dùng để vượt phạm vi CLB; ban tổ chức cần gán lại admin cho gian hàng phù hợp.
- Danh sách và kết quả cũ không tự phân vào CLB vì hệ thống không biết CLB tương ứng. Superadmin nhập lại danh sách phù hợp cho từng gian hàng; dữ liệu điểm danh cũ vẫn được giữ riêng.

### API bổ sung

Tiền tố gian hàng: `/events/{event_id}/clubs/{club_id}`.

| Method | Path | Quyền và kết quả |
|---|---|---|
| GET / POST | `/events/{event_id}/clubs` | Danh sách CLB có quyền truy cập / superadmin tạo CLB |
| GET | `/events/{event_id}/summary` | Chỉ superadmin; tổng lượt đăng ký, lượt điểm danh và số sinh viên duy nhất đã ghé |
| GET | `{prefix}/summary` | Admin CLB / superadmin; số liệu và 6 lượt điểm danh gần nhất |
| GET / POST / DELETE | `{prefix}/admins[/{user_id}]` | Xem đội ngũ CLB / superadmin gán / thu hồi |
| PATCH | `{prefix}/checkin` | Admin CLB / superadmin; `{"checkin_open":true}` |
| GET / POST | `{prefix}/students` | Trang danh sách / thêm người tham gia |
| GET | `{prefix}/students/template` | Mẫu XLSX ba cột như API cũ |
| POST | `{prefix}/students/import` | Multipart `file`; giữ giới hạn và tính toàn vẹn như API cũ |
| GET | `{prefix}/attendance/export` | Xuất toàn bộ kết quả khớp bộ lọc của CLB |
| GET | `{prefix}/me` | Đăng ký và kết quả của chính tài khoản hiện tại |
| GET | `{prefix}/qr` | QR của chính sinh viên đã được thêm vào CLB |
| POST | `{prefix}/attendance/scan` | Admin CLB xác nhận; quét lặp trả bản ghi cũ |

`GET {prefix}/students` trả `{"items": [...], "total": 120, "offset": 0, "limit": 25}`. Bộ lọc `search` tìm tên, MSSV hoặc email; `attended` lọc trạng thái; `limit` tối đa 500. Tìm kiếm tên không bỏ dấu tiếng Việt. Export sử dụng cùng bộ lọc và không giới hạn ở trang đang xem.

Tổng hợp sự kiện tính **lượt** theo CLB: một sinh viên đăng ký hai CLB tạo hai lượt đăng ký, ghé cả hai tạo hai lượt điểm danh. `unique_attendees` đếm sinh viên duy nhất đã điểm danh trong các CLB.

### Kiểm tra giao diện bằng trình duyệt

Các test API dùng SQLite bộ nhớ; test trình duyệt mở server cục bộ trên cổng ngẫu nhiên, dùng API thật và chỉ mock xác minh Google. Không cần tài khoản Google thật hay DB production.

```sh
cd backend
uv run --with playwright playwright install chromium
uv run --with-requirements requirements.txt --with playwright python -m pytest tests/test_browser.py -q
```

Có thể đặt `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` để dùng Chromium đã cài. Bộ test kiểm tra menu theo quyền, mobile, tự làm mới QR, đọc ảnh QR và tạo CLB / gán admin. CI chạy toàn bộ test API, tách test trình duyệt để không yêu cầu browser trên runner triển khai.

QR ảnh dùng bản jsQR 1.4.0 phục vụ từ `frontend/vendor`; license Apache-2.0 đi kèm. Camera dùng BarcodeDetector nếu trình duyệt hỗ trợ, hoặc jsQR trên khung hình camera. Kết nối HTTPS và quyền camera vẫn cần khi triển khai thực tế.

### Nhận diện logo

Dashboard và vé dùng logo gốc trong `assets/brand/`; nguồn file ghi ở `SOURCES.md`. RTIC, DSC và ISC/ATTT được nhận diện từ tên CLB; CLB khác hiển thị chữ viết tắt cho đến khi bổ sung file nhận diện. Logo sự kiện và các đơn vị còn lại lấy từ `assets/bo-logo/ban-cat-goc/`. Các ảnh phục dựng không được dùng trong dashboard/vé. Logo được phục vụ qua static mount `/assets`, không thay đổi schema DB.
