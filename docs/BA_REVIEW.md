# Rà soát và nâng cấp FIT Club Day

Ngày: 16/10/2026. Nguồn: mã nhánh `e691212`, yêu cầu và lựa chọn trực tiếp của chủ dự án trong phiên làm việc. Đây là đánh giá yêu cầu và heuristic từ mã nguồn; chưa có phỏng vấn hay nghiên cứu hành vi người dùng thực tế.

## Cách áp dụng BA-Kit

Chuỗi: **ba-master → ba-ux → ba-prioritization → ba-validation**. Đánh giá hành trình và khoảng trống trước; ưu tiên phạm vi; triển khai; kiểm tra bằng tiêu chí và test thực thi. Bổ sung UI Design Brain cho bố cục / thành phần, TDD cho thay đổi nghiệp vụ, Playwright cho hành trình trình duyệt.

Kiến thức đối chiếu từ BA-Kit cục bộ:

- **UXR-032**, Nielsen heuristics: trạng thái hệ thống, ngăn lỗi, nhận biết thay vì ghi nhớ, khôi phục lỗi.
- **UXR-043**, yêu cầu từ điểm đứt hành trình: thiếu phản hồi phải dẫn đến yêu cầu phản hồi cụ thể.
- **VAL-022**, completeness: nguồn, vai trò, phụ thuộc và tiêu chí kiểm thử phải rõ.
- **PRI-006 / PRI-005**, ưu tiên: ghi rõ phần nằm ngoài bản phát hành, tránh gom tất cả thành Must.

Nguồn các mục: `docs/knowledge_base/specialized/ux_research.md`, `validation.md`, `prioritization.md` trong bản BA-Kit cài tại máy. Không có số liệu analytics để tính RICE hoặc cam kết KPI sử dụng.

## Các quyết định được chủ dự án xác nhận

1. Dashboard sáng, xanh navy, đồng bộ FIT/RTIC, dùng được trên điện thoại.
2. FIT Club Day là sự kiện chung gồm nhiều CLB tham gia.
3. Admin chỉ quản lý danh sách của CLB được gán; superadmin xem toàn bộ.
4. Điểm danh độc lập tại từng gian hàng CLB.
5. Sinh viên tự bấm **Tham gia CLB** khi sự kiện đang mở; admin tiếp tục chỉ quản lý danh sách CLB mình.

Sinh viên có thể thuộc nhiều CLB; admin có thể thêm/import danh sách và sinh viên có thể tự tham gia khi sự kiện mở. Cả sự kiện và gian hàng phải mở để điểm danh QR. Danh sách cũ chưa phân loại được giữ riêng, không tự đoán CLB.

## Hành trình và khoảng trống ban đầu

| Vai trò | Mục tiêu | Khoảng trống | Thay đổi |
|---|---|---|---|
| Sinh viên | Có vé đúng gian hàng, biết đã tham gia chưa | QR hết hạn phải bấm lại; không có kết quả cá nhân | Vé CLB, đếm hạn, tự làm mới, trạng thái tham gia |
| Admin CLB | Đón người tham gia và quản lý đúng danh sách | Chỉ có quyền theo sự kiện, không có phạm vi CLB | Danh sách / QR / kết quả / admin tách theo gian hàng |
| Superadmin | Điều phối toàn ngày hội | Không có CLB hay tổng hợp các gian hàng | Tạo gian hàng, gán admin, tổng hợp lượt và sinh viên duy nhất |
| Người dùng điện thoại | Điểm danh tại sự kiện | Nhiều form trên một trang, camera phụ thuộc API trình duyệt | Điều hướng theo vai trò, vé trên mobile, chọn ảnh QR, decoder cục bộ |

Điểm đứt cần xử lý: chưa được thêm vào CLB; sự kiện / gian hàng đóng; QR hết hạn hoặc sai gian hàng; mạng lỗi; Google chưa tải; token hết hạn; nhập Excel có dòng sai; thu hồi quyền khi phiên còn hiệu lực.

## Ưu tiên và giới hạn phạm vi

Backlog hiện có 12 nhóm yêu cầu, với 2 Must, 3 Should, 2 Could và 5 Won't. FR-07 được triển khai theo xác nhận trực tiếp của chủ dự án về luồng sinh viên tự tham gia.

| ID | Nhóm yêu cầu | Ưu tiên | Quyết định |
|---|---|---|---|
| FR-01 | Phân quyền và danh sách theo CLB | Must | Triển khai; nền tảng của các bước còn lại |
| FR-02 | Điểm danh độc lập theo gian hàng | Must | Triển khai; ngăn xác nhận nhầm CLB |
| FR-03 | Dashboard và điều phối có dữ liệu thật | Should | Triển khai trên FR-01/02 |
| FR-04 | Vé sinh viên và trạng thái cá nhân | Should | Triển khai trên FR-02 |
| FR-05 | Tìm kiếm, phân trang và xuất cùng bộ lọc | Could | Triển khai; giảm thao tác quản lý danh sách |
| FR-06 | Nhập Excel và phản hồi theo dòng | Could | Triển khai; tái sử dụng quy tắc kiểm tra hiện có |
| FR-07 | Sinh viên tự đăng ký vào gian hàng | Should | Đã triển khai: xem sự kiện mở, tự tham gia, nhận vé; không thay đổi quyền admin |
| FR-08 | Chứng nhận, điểm rèn luyện tự động | Won't | Cần tiêu chí công nhận từ khoa |
| FR-09 | Gamification, passport và quà tặng | Won't | Cần luật tích điểm / chống nhận quà trùng |
| FR-10 | Điểm danh ngoại tuyến | Won't | Cần giải quyết đồng bộ và xung đột dữ liệu |
| FR-11 | PostgreSQL, migration và đa instance | Won't | Chưa có yêu cầu quy mô; giữ schema cũ, bổ sung bảng mới |
| FR-12 | Email / thông báo bên ngoài | Won't | Chưa có yêu cầu gửi và nhà cung cấp |

Đây là phạm vi cải tiến đầu tiên, không đại diện cho toàn bộ backlog vận hành lâu dài.

## Tiêu chí nghiệm thu

| ID | Ca thành công | Biên / lỗi | Bằng chứng |
|---|---|---|---|
| FR-01 | Superadmin tạo CLB và gán admin; admin thấy CLB được gán | Admin bị chặn đọc/ghi CLB khác, kể cả dùng quyền sự kiện cũ; thu hồi có hiệu lực với token cũ | `test_clubs.py`: identity, cross-club read/write, legacy bypass, revocation; browser tạo CLB/gán admin |
| FR-02 | Quét QR đúng CLB tạo một bản ghi có người quét / thời gian | QR sai CLB, sai event, sai mục đích, hết hạn hoặc sửa bị từ chối; quét trùng giữ bản ghi cũ; đóng event/CLB ngăn ghi | `test_clubs.py`: independent checkins, closure, token checks; browser quét ảnh QR |
| FR-03 | Tổng quan CLB đếm đúng; superadmin thấy lượt tổng hợp và sinh viên duy nhất | CLB rỗng trả số 0 và tỷ lệ 0; admin không lấy được tổng sự kiện | `test_clubs.py`: summary / empty summary; browser số liệu admin |
| FR-04 | Sinh viên thấy vé, QR tự đổi khi hết hạn, trạng thái riêng từng CLB | Chưa đăng ký / đóng gian hàng có hướng dẫn; access token không thay được QR; đổi ngữ cảnh xóa QR cũ | `test_clubs.py`: status / closure / purpose; browser mobile / renewal |
| FR-05 | Tìm tên, MSSV, email; trả items/total/offset/limit | Trang rỗng vẫn có tổng đúng; ký tự `%` không trở thành wildcard; export gồm toàn bộ kết quả khớp | `test_clubs.py`: filters / pagination / export; browser tìm kiếm |
| FR-06 | File hợp lệ thêm đúng vào CLB; dòng trùng báo riêng | File có dòng sai không thêm dòng nào; giới hạn dung lượng / dòng / giải nén giữ nguyên; không lọt sang CLB khác | `test_clubs.py`: scoped atomic import; test API cũ kiểm tra parser dùng chung |
| FR-07 | Tài khoản chưa đăng ký thấy sự kiện mở, tự tham gia CLB và nhận vé | Chỉ đăng ký cho mình; gọi lặp không thêm trùng; đóng sự kiện ngăn đăng ký; QR vẫn đợi gian hàng mở; không có quyền xem roster CLB | `test_discovery.py` và browser journey ở 360/390/768 px |

Yêu cầu giao diện bổ sung: các luồng mới được kiểm tra ở 360, 390 và 768 px, thêm quản trị / form ở 375 px; không tràn ngang toàn trang, bảng cuộn trong vùng riêng; nút chính có vùng chạm tối thiểu 44 px. Menu Tài khoản hiển thị email đăng nhập. Trang đang trống tự cập nhật khi sự kiện được mở. Dialog có đóng / hủy / Escape; camera và QR dừng khi rời ngữ cảnh; không dựng dữ liệu người dùng bằng HTML chưa escape.

## Reflection Mode (System 2)

- Tách điểm danh sự kiện cũ khỏi điểm danh gian hàng; không chuyển kết quả cũ thành kết quả CLB khi chưa có mapping.
- Quyền `EventAdmin` cũ là đường có thể lách phạm vi mới. Đã có test tái hiện trả 200; sau sửa, trả 403 cho quản trị danh sách toàn sự kiện khi có CLB.
- Tổng hợp phải phân biệt **lượt** và **người duy nhất**. Giao diện toàn sự kiện dùng nhãn lượt; không trình bày một sinh viên ghé hai gian hàng như hai sinh viên.
- Không xem ảnh chụp đẹp là bằng chứng usability. Chưa có nghiên cứu với sinh viên / admin tại sự kiện, chưa kiểm thử camera trên thiết bị vật lý và chưa kiểm thử Google OAuth thật.
- Chỉ mở tự tham gia khi công tắc sự kiện đã bật, theo quyết định của chủ dự án; không mở rộng sang phát quà, chứng nhận hoặc gửi tin.

## Đánh giá nghiệm thu phạm vi

**7/7 nhóm triển khai có nguồn, phạm vi quyền, phụ thuộc và ca thành công/biên/lỗi.** Đây là đánh giá đầy đủ của phạm vi tài liệu, không phải chứng nhận chất lượng tổng thể hay điểm khảo sát UX. FR-03/04/05/06/07 có phụ thuộc vào mô hình quyền và điểm danh FR-01/02.

Khuyến nghị: đủ điều kiện bàn giao bản sửa để chủ dự án xem và chạy UAT. Người nhận tiếp theo là chủ dự án / đại diện CLB để xác nhận hành trình thực tế; nếu phát hiện thiếu quy tắc, quay lại `ba-master` để bổ sung phạm vi trước khi mở rộng.

Kết quả thực thi ngày 16/10/2026: **127 test qua**, gồm 115 test API và 12 trường hợp trình duyệt. Có một cảnh báo deprecation từ Starlette TestClient; không có test lỗi. `node --check frontend/app.js` và `git diff --check` qua. CI chạy toàn bộ test API. Ảnh kiểm tra bố cục nằm tại `docs/previews/`; số liệu trên ảnh là dữ liệu giả lập.

Nhận diện giao diện: logo HCMUTE, FIT, RTIC, DSC và ISC dùng file PNG gốc sao chép nguyên vẹn; nguồn được ghi ở `assets/brand/SOURCES.md`. Logo sự kiện và đơn vị còn lại dùng bản cắt từ poster gốc. Logo theo CLB được đồng bộ ở dashboard, danh sách gian hàng và vé sinh viên; có test chuyển CLB kiểm tra cả hình nhận diện lẫn tên vé.

Việc cần xác nhận trước vận hành: cấu hình OAuth đúng origin, backup DB, mapping danh sách cũ vào CLB, gán lại admin và thử camera trên thiết bị dùng tại sự kiện. Những mục này chưa được coi là đã hoàn thành bằng bộ test cục bộ.
