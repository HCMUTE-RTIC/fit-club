# Triển khai event.hcmutertic.com

## Đích triển khai

- SSH ứng dụng: `ssh -p 9010 root@222.253.80.30` → `bigdata-server-andyanh`, IP LAN `192.168.1.17`.
- Từ máy ứng dụng: `ssh root@192.168.1.80` → máy Nginx `proxmox`.
- App: `192.168.1.17:8512`, systemd `fit-club-event.service`, chạy với tài khoản hệ thống `fit-event`.
- Code bất biến theo release: `/srv/fit-club-event/releases/<commit>`; symlink đang chạy: `/srv/fit-club-event/current`.
- Cấu hình thật: `/etc/fit-club-event/.env`, mode `0600`, không nằm trong Git. Chỉ bản mẫu được version hóa.
- SQLite: `/var/lib/fit-club-event/fitclub.db`; backup khi cập nhật: `/var/backups/fit-club-event/`.

Khởi tạo `SUPERADMIN_EMAILS=hovietanh147@gmail.com`. `STUDENT_EMAIL_ONLY=true` vẫn hạn chế người tham gia thông thường; Gmail chỉ đăng nhập được nếu là bootstrap superadmin hoặc đã được cấp quyền admin/superadmin. Mọi tài khoản phải qua Google xác minh email.

## Cài release

Tạo archive từ commit đã kiểm thử, chuyển archive và `backend/deploy/install-event-release.sh` lên máy ứng dụng, rồi chạy với quyền root:

```sh
bash install-event-release.sh <COMMIT_SHA> /root/fit-club-event-<COMMIT_SHA>.tar.gz
```

Script tạo user / cấu hình lần đầu, tạo venv bằng `/usr/bin/python3`, cài dependency, chạy toàn bộ test API, backup DB nếu có, đổi symlink, restart và kiểm tra `/health`. Nếu health check lỗi, tự quay lại release trước (hoặc dừng service nếu đây là lần cài đầu).

CI GitHub tiếp tục chạy test trên push `main`. Bước triển khai đến máy chủ cũ chỉ chạy khi gọi workflow thủ công; triển khai domain mới thực hiện trực tiếp trên máy chủ nêu trên.

## Nginx và SSL

Trên `192.168.1.80`, đặt bộ file `event.hcmutertic.com.http.conf`, `event.hcmutertic.com.conf` và `configure-event-edge.sh` cùng một thư mục rồi chạy script.

Script thực hiện:

1. Kiểm tra health của upstream LAN.
2. Cài site HTTP vào `/etc/nginx/sites-available/event.hcmutertic.com`.
3. Tạo symlink tương ứng trong `/etc/nginx/sites-enabled/`.
4. Chạy `nginx -t`, reload, cấp chứng chỉ Certbot bằng HTTP-01 webroot `/var/www/letsencrypt`.
5. Cài cấu hình HTTPS, kiểm tra và reload lại.
6. Bật `certbot.timer`; deploy hook kiểm tra rồi reload Nginx khi gia hạn.

Bản ghi A `event.hcmutertic.com` phải trỏ tới `222.253.80.30`. Không tạo bản ghi AAAA nếu đường IPv6 chưa được đưa về proxy này.

## Google OAuth

Ứng dụng dùng Google Identity Services callback trong JavaScript, gửi ID token đến `/auth/google`; không dùng OAuth code exchange hay Client Secret. Tạo Web Client ID với JavaScript origin `https://event.hcmutertic.com`; Redirect URI để trống. Xem [hướng dẫn thiết lập của Google](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).

Sau khi có Client ID, trên máy ứng dụng chạy:

```sh
bash /srv/fit-club-event/current/backend/deploy/set-google-client-id.sh 'YOUR_WEB_CLIENT_ID.apps.googleusercontent.com'
```

Script chỉ thay `GOOGLE_CLIENT_ID`, giữ JWT secret và các cấu hình khác, giữ mode `0600` rồi restart service. Không đưa Client Secret, file cấu hình thật hoặc JWT secret vào Git / ticket / log.

## Cấp quyền theo email

Superadmin bấm **Cấp quyền** trên dashboard, nhập email, chọn **Superadmin toàn hệ thống** hoặc **Admin CLB**. Với admin, phải chọn CLB trong sự kiện hiện tại. Họ tên có thể để trống và được cập nhật từ Google ở lần đăng nhập đầu tiên.

API: `POST /access/grants`, Bearer của superadmin:

```json
{"email":"staff@example.com","role":"superadmin"}
```

```json
{"email":"staff@example.com","role":"admin","event_id":1,"club_id":2}
```

Thu hồi qua API / giao diện quản trị hiện có. Quyền được kiểm tra từ DB trong từng request; email ngoài trường bị từ chối đăng nhập mới sau khi không còn quyền.

## Mở sự kiện và tiếp nhận sinh viên

Superadmin mở sự kiện để sinh viên thấy tổng quan và danh sách gian hàng. Sinh viên bấm **Tham gia CLB**; API chỉ thêm chính tài khoản đã xác thực, có xử lý đăng ký trùng. Admin CLB thấy danh sách mới sau làm mới / đồng bộ, nhưng không được xem danh sách của CLB khác.

Mở sự kiện chưa tự mở điểm danh cho từng gian hàng. Admin chọn CLB → **Quét điểm danh** → **Mở điểm danh CLB** khi sẵn sàng. Vé của sinh viên phân biệt rõ đăng ký và đã điểm danh.

Giao diện có menu **Tài khoản** hiển thị email Google đang dùng, giúp phân biệt tài khoản sinh viên và tài khoản superadmin. Các trang đã mở từ bản cũ cần tải lại để nhận JavaScript/CSS mới.

## Kiểm tra và rollback

Kiểm tra `systemctl status fit-club-event`, `https://event.hcmutertic.com/health`, schema `/openapi.json`, hình logo và trạng thái TLS. Login thật chỉ xác nhận sau khi có Web Client ID và đăng nhập bằng tài khoản Google.

Quay lại release trước:

```sh
ln -sfn /srv/fit-club-event/releases/<PREVIOUS_COMMIT> /srv/fit-club-event/current
systemctl restart fit-club-event
curl --fail http://192.168.1.17:8512/health
```

Không xóa `.env`, DB hoặc backup khi rollback. Nếu cần gỡ site mới, trên proxy bỏ đúng symlink `/etc/nginx/sites-enabled/event.hcmutertic.com`, chạy `nginx -t` rồi reload; các site khác không đổi.
