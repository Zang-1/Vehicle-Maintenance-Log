# 01 – Requirements (Đặc tả yêu cầu)

**Người phụ trách:** Kiều Bảo Giang · **Phiên bản:** 2.1

> Môn **72ITDS30103 – Software Development Platforms**. Theo Final Project Brief, đồ án là *một ứng dụng web CRUD ba tầng nhỏ, có một tính năng AI*. Thứ được chấm là **pipeline nền tảng** xung quanh ứng dụng (container, Compose, CI/CD, cloud database, AI call), không phải số lượng chức năng. Vì vậy phạm vi chức năng dưới đây được giữ ở mức vừa đủ, còn các yêu cầu nền tảng (mục 5.1) là bắt buộc.

## 1. Giới thiệu

### 1.1. Bối cảnh

Nhiều chủ xe máy, ô tô không nhớ lần cuối thay nhớt, thay lọc gió hay bảo dưỡng định kỳ là khi nào, ở số km bao nhiêu và tốn bao nhiêu tiền. Khi xe có tiếng kêu lạ hay đèn báo sáng, họ cũng không biết mức độ nghiêm trọng đến đâu, có cần mang đi sửa ngay hay không.

### 1.2. Mục đích hệ thống

**Vehicle Maintenance Log** giúp chủ xe:

1. Lưu thông tin các xe của mình.
2. Ghi lại lịch sử bảo dưỡng: ngày, số km, các hạng mục, chi phí, nơi làm.
3. Thấy ngay hạng mục nào **sắp đến hạn / quá hạn**, tính theo thời gian hoặc số km.
4. Theo dõi tổng chi phí bảo dưỡng.
5. **Chẩn đoán bằng AI:** mô tả triệu chứng bằng lời ("xe đề không nổ, có tiếng tạch tạch"), nhận gợi ý nguyên nhân, mức độ khẩn cấp và hạng mục nên kiểm tra.

### 1.3. Ba câu hỏi của Brief khi tự đề xuất đề tài

| Câu hỏi | Trả lời |
|---|---|
| Ứng dụng lưu những bản ghi nào? | Xe, lần bảo dưỡng (kèm các hạng mục và chi phí), nhắc lịch bảo dưỡng, lịch sử chẩn đoán AI. |
| Tính năng AI là gì? | Người dùng nhập triệu chứng của xe. Server gọi Google Gemini (miễn phí) và trả về gợi ý nguyên nhân, mức khẩn cấp (LOW / MEDIUM / HIGH) và hạng mục nên kiểm tra. |
| Người dùng thấy gì khi AI lỗi? | Trang vẫn hoạt động bình thường, chữ đã nhập được giữ nguyên. Một thông báo thân thiện cho biết lý do: hết lượt (429) thì "thử lại sau ít phút", quá thời gian thì "thử lại", chưa cấu hình key thì "tính năng tạm thời không khả dụng". Lần gọi lỗi vẫn được lưu lại kèm mã lỗi. |

### 1.4. Phạm vi

| Trong phạm vi | Ngoài phạm vi (lý do) |
|---|---|
| CRUD xe, lần bảo dưỡng + hạng mục, nhắc lịch, danh mục loại dịch vụ | **Đăng nhập, nhiều người dùng, phân quyền.** Brief yêu cầu phạm vi nhỏ; bản demo dùng chung một bộ dữ liệu |
| Trạng thái nhắc lịch được tính ngay khi mở trang | **Tiến trình chạy ngầm theo giờ, gửi email.** Render free sleep sau ~15 phút không dùng nên tác vụ hẹn giờ không chạy được |
| Thống kê chi phí | **Upload ảnh hóa đơn.** Brief khuyên tránh lưu file lớn hơn vài MB |
| Chẩn đoán AI qua Gemini, gọi từ server | Xử lý ảnh/video, huấn luyện mô hình, thời gian thực (socket), thanh toán. Brief yêu cầu tránh |

### 1.5. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Xe | Phương tiện: xe máy, ô tô hoặc loại khác |
| ODO | Số km xe đã chạy (đồng hồ công-tơ-mét) |
| Lần bảo dưỡng | Một lần mang xe đi bảo dưỡng/sửa chữa, gồm một hoặc nhiều hạng mục |
| Hạng mục | Một công việc cụ thể, ví dụ "Thay nhớt máy", kèm số lượng và đơn giá |
| Loại dịch vụ | Danh mục chuẩn các hạng mục, có chu kỳ khuyến nghị (km, tháng) |
| Nhắc lịch | Quy tắc "cứ X km hoặc Y tháng làm lại" cho một loại dịch vụ của một xe |
| Chẩn đoán | Một lần hỏi AI về triệu chứng của xe và kết quả trả về |

## 2. Tác nhân

| Tác nhân | Loại | Mô tả |
|---|---|---|
| **Chủ xe** | Người dùng chính | Truy cập URL công khai bằng trình duyệt (máy tính hoặc điện thoại), dùng mọi chức năng |
| **Google Gemini API** | Hệ thống ngoài | Nhận triệu chứng từ server, trả về gợi ý chẩn đoán. Có giới hạn số lần gọi (rate limit) của free tier |

Ghi chú cho use case (02): GitHub Actions, Render, Supabase là **nền tảng triển khai**, không phải tác nhân nghiệp vụ. Chúng được mô tả ở tài liệu 07 và 08.

## 3. Mục tiêu

| Mã | Mục tiêu | Cách đo |
|---|---|---|
| G-01 | Ghi một lần bảo dưỡng nhanh | Ghi xong một lần bảo dưỡng có 1 hạng mục trong ≤ 1 phút |
| G-02 | Không bỏ lỡ mốc bảo dưỡng | Mọi nhắc lịch quá hạn/sắp đến hạn đều hiện trên Dashboard |
| G-03 | Minh bạch chi phí | Xem tổng chi phí theo tháng, theo xe, theo loại dịch vụ trên 1 màn hình |
| G-04 | AI hữu ích nhưng không làm hỏng app | AI lỗi (429, timeout, thiếu key) thì các trang khác vẫn chạy, người dùng thấy thông báo rõ ràng |
| G-05 | Đạt đủ 5 tiêu chí demo của Brief | HTTPS công khai · Compose 1 lệnh · CI xanh · Merge là tự deploy · Không có secret trong repo |

## 4. Yêu cầu chức năng (Functional Requirements)

Ưu tiên: **Must** = bắt buộc cho demo · **Should** = nên có · **Could** = làm nếu kịp.

### 4.1. Quản lý xe

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-01 | Thêm xe | Tên gợi nhớ, loại xe, hãng, dòng xe, năm sản xuất, biển số, ODO hiện tại, ngày mua | Must |
| FR-02 | Danh sách xe | Hiển thị các xe đang dùng: tên, biển số, ODO, số nhắc lịch cần chú ý | Must |
| FR-03 | Chi tiết xe | Thông tin xe + lịch sử bảo dưỡng + nhắc lịch của xe | Must |
| FR-04 | Sửa xe, cập nhật ODO | Sửa thông tin; ODO mới không được nhỏ hơn ODO hiện tại | Must |
| FR-05 | Lưu trữ / Xóa xe | Lưu trữ xe đã bán (ẩn đi, giữ lịch sử); chỉ xóa hẳn được khi xe chưa có lịch sử | Should |

### 4.2. Lịch sử bảo dưỡng

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-06 | Ghi nhận lần bảo dưỡng | Chọn xe, ngày, ODO lúc làm, nơi làm, ghi chú; thêm 1..n hạng mục (loại dịch vụ, mô tả, số lượng, đơn giá) | Must |
| FR-07 | Xem lịch sử | Các lần bảo dưỡng của một xe, mới nhất trước, có tổng chi phí; lọc theo khoảng ngày | Must |
| FR-08 | Chi tiết lần bảo dưỡng | Các hạng mục, thành tiền, tổng chi phí | Must |
| FR-09 | Sửa / Xóa lần bảo dưỡng | Có hộp thoại xác nhận khi xóa | Must |
| FR-10 | Xuất CSV | Xuất lịch sử bảo dưỡng của một xe | Could |

### 4.3. Loại dịch vụ

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-11 | Xem danh mục | Danh sách loại dịch vụ đang dùng, có sẵn dữ liệu mẫu từ `seed.sql` | Must |
| FR-12 | Thêm / Sửa / Ngừng dùng | Tên, mô tả, áp dụng cho loại xe, chu kỳ mặc định (km, tháng) | Should |

### 4.4. Nhắc lịch

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-13 | Tạo nhắc lịch | Chọn xe + loại dịch vụ; chu kỳ km và/hoặc tháng (điền sẵn từ chu kỳ mặc định); ngưỡng báo trước | Must |
| FR-14 | Xem / Sửa / Tạm dừng / Xóa nhắc lịch | Kèm trạng thái **Còn hạn / Sắp đến hạn / Quá hạn** và số ngày, số km còn lại | Must |
| FR-15 | Tự tính mốc đến hạn | Mốc tiếp theo tính từ lần bảo dưỡng gần nhất có hạng mục cùng loại dịch vụ. Người dùng không phải cập nhật tay | Must |

### 4.5. Dashboard và thống kê

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-16 | Dashboard | Trang chủ: số xe, các nhắc lịch quá hạn/sắp đến hạn, chi phí tháng này, 5 lần bảo dưỡng gần nhất | Must |
| FR-17 | Thống kê chi phí | Chi phí theo tháng, theo xe, theo loại dịch vụ trong khoảng thời gian chọn | Should |

### 4.6. Chẩn đoán bằng AI

| Mã | Chức năng | Mô tả | Ưu tiên |
|---|---|---|---|
| FR-18 | Gửi triệu chứng | Nhập mô tả triệu chứng (10–1.000 ký tự), có thể chọn xe để AI biết loại xe, hãng, ODO | Must |
| FR-19 | Nhận kết quả | Hiển thị gợi ý nguyên nhân, mức khẩn cấp LOW/MEDIUM/HIGH, hạng mục nên kiểm tra, kèm câu lưu ý "chỉ mang tính tham khảo" | Must |
| FR-20 | Xử lý khi AI lỗi | Thiếu key, quá thời gian, 429, lỗi 5xx: trả thông báo thân thiện, giữ nguyên dữ liệu đã nhập, app không crash (xem BR-10) | Must |
| FR-21 | Lịch sử chẩn đoán | Lưu mọi lần gọi (thành công hoặc lỗi) vào database; xem lại danh sách | Should |
| FR-22 | Tạo nhắc lịch từ gợi ý | Từ kết quả chẩn đoán, bấm một nút để ghi nhận bảo dưỡng hoặc tạo nhắc lịch cho hạng mục được gợi ý | Could |

## 5. Yêu cầu phi chức năng

### 5.1. Yêu cầu nền tảng (bắt buộc theo Final Project Brief)

| Mã | Yêu cầu | Bằng chứng khi demo |
|---|---|---|
| PR-01 | Ứng dụng chạy công khai qua **HTTPS** trên nền tảng cloud miễn phí (Render) | Mở URL trên điện thoại dùng 4G |
| PR-02 | **Dockerfile** build ứng dụng thành image; có `.dockerignore`; layer được sắp xếp để tận dụng cache | `podman build` từ clean clone |
| PR-03 | **Compose** dựng toàn bộ môi trường local (web + PostgreSQL) bằng **1 lệnh** từ clean clone | `podman compose up --build` |
| PR-04 | **GitHub Actions**: lint (ruff) + test (pytest) + build image trên mỗi Pull Request; merge vào `main` thì tự deploy qua Render deploy hook | Lịch sử Actions, PR bị chặn khi đỏ |
| PR-05 | **Managed PostgreSQL** trên cloud (Supabase), gắn vào app chỉ bằng biến môi trường `DATABASE_URL` | `/health/db` trên URL live |
| PR-06 | **Tính năng AI** gọi API miễn phí (Gemini) **từ server**; key không nằm trong repo | Gọi `/diagnose` trên URL live; `git grep` không ra key |
| PR-07 | **Zero credit card:** mọi nền tảng đăng ký miễn phí, không cần thẻ | |
| PR-08 | Không ai commit thẳng vào `main`; mọi thay đổi qua PR có người khác duyệt; branch protection bật | Cài đặt repo, lịch sử PR |

### 5.2. Yêu cầu chất lượng

| Mã | Nhóm | Yêu cầu |
|---|---|---|
| NFR-01 | Bảo mật | Secret (`DATABASE_URL`, `GEMINI_API_KEY`, `RENDER_DEPLOY_HOOK`) chỉ nằm ở `.env` (local, đã gitignore), Render Environment và GitHub Secrets; không có trong code, ảnh chụp, lịch sử Git |
| NFR-02 | Bảo mật | Truy vấn SQL tham số hóa (psycopg); kiểm tra dữ liệu vào bằng Pydantic |
| NFR-03 | Bảo mật | Bật Row Level Security trên mọi bảng để chặn REST API tự động của Supabase (app kết nối bằng owner nên không bị ảnh hưởng) |
| NFR-04 | Tin cậy | `/health` trả 200 mà **không** chạm database (để Render health check không lỗi khi DB tạm dừng); `/health/db` báo 503 khi mất DB |
| NFR-05 | Tin cậy | Mất kết nối DB hoặc Supabase pause: app không crash, tự phục hồi khi DB có lại, không cần redeploy (connection pool có pre-ping) |
| NFR-06 | Tin cậy | Gọi AI có timeout (≤ 20 giây), không tự gọi lại liên tục khi gặp 429 |
| NFR-07 | Hiệu năng | Trang danh sách phản hồi < 2 giây khi server đã thức (lần đầu sau khi Render ngủ có thể chậm ~1 phút) |
| NFR-08 | Khả dụng | Giao diện tiếng Việt, dùng được trên điện thoại (rộng từ 360px) |
| NFR-09 | Khả dụng | Xóa xe, lần bảo dưỡng phải có hộp thoại xác nhận |
| NFR-10 | Bảo trì | Script `db/schema.sql` và `db/seed.sql` chạy lại nhiều lần không lỗi, không nhân đôi dữ liệu (chạy được cả trong Compose lẫn Supabase SQL Editor) |
| NFR-11 | Bảo trì | Test trong CI **không gọi Gemini thật** (dùng mock), để pipeline luôn chạy được và không tốn lượt gọi |

## 6. Quy tắc nghiệp vụ

| Mã | Quy tắc |
|---|---|
| BR-01 | Biển số xe là duy nhất (bỏ trống được với xe chưa có biển) |
| BR-02 | ODO của xe không được giảm. Ghi nhận bảo dưỡng có ODO lớn hơn ODO xe thì ODO xe được cập nhật theo |
| BR-03 | Ngày bảo dưỡng không được ở tương lai |
| BR-04 | Một lần bảo dưỡng có ít nhất một hạng mục; không có hai lần bảo dưỡng trùng xe + ngày + ODO |
| BR-05 | Thành tiền hạng mục = số lượng × đơn giá (không âm). Tổng chi phí = tổng thành tiền các hạng mục, luôn được tính, không nhập tay |
| BR-06 | Nhắc lịch có ít nhất một chu kỳ (km hoặc tháng). Có cả hai thì cái nào đến trước tính là đến hạn. Mỗi xe chỉ có một nhắc lịch cho mỗi loại dịch vụ |
| BR-07 | Mốc gốc = lần bảo dưỡng gần nhất có hạng mục cùng loại dịch vụ. Nếu chưa có thì lấy ngày và ODO lúc tạo nhắc lịch. Mốc đến hạn = mốc gốc + chu kỳ |
| BR-08 | **Quá hạn** nếu đã qua mốc ngày hoặc mốc km. **Sắp đến hạn** nếu còn ≤ ngưỡng báo trước (mặc định 7 ngày hoặc 300 km). Còn lại là **Còn hạn** |
| BR-09 | Xe đã có lịch sử không xóa hẳn được, chỉ lưu trữ. Loại dịch vụ đã được dùng không xóa được, chỉ ngừng dùng |
| BR-10 | Khi AI lỗi, server trả mã và thông báo theo bảng dưới. Không lộ chi tiết kỹ thuật hay key cho trình duyệt; chi tiết chỉ ghi vào log server |

Bảng xử lý lỗi AI (BR-10, FR-20):

| Tình huống | Mã server trả | Người dùng thấy | Lưu `diagnoses.error_code` |
|---|---|---|---|
| Chưa cấu hình `GEMINI_API_KEY` | 503 | "Tính năng chẩn đoán AI tạm thời không khả dụng." | `NO_KEY` |
| Gemini trả 429 (hết lượt free tier) | 429 | "Đã hết lượt chẩn đoán miễn phí, vui lòng thử lại sau ít phút." | `RATE_LIMITED` |
| Quá thời gian chờ | 504 | "AI phản hồi quá lâu, vui lòng thử lại." | `TIMEOUT` |
| Gemini lỗi 5xx / trả về không đúng định dạng | 502 | "Không nhận được kết quả từ AI, vui lòng thử lại." | `UPSTREAM_ERROR` |
| Triệu chứng quá ngắn/dài | 422 | Báo lỗi ngay dưới ô nhập (không gọi AI) | (không lưu) |

## 7. Danh sách màn hình

Dùng làm đầu vào cho Wireframe (05) và UI Design (06).

| # | Màn hình | FR |
|---|---|---|
| S01 | Dashboard (trang chủ) | FR-16 |
| S02 | Danh sách xe | FR-02, FR-05 |
| S03 | Thêm / Sửa xe | FR-01, FR-04 |
| S04 | Chi tiết xe (Thông tin · Lịch sử · Nhắc lịch) | FR-03, FR-07, FR-14 |
| S05 | Ghi nhận / Sửa lần bảo dưỡng | FR-06, FR-09 |
| S06 | Chi tiết lần bảo dưỡng | FR-08 |
| S07 | Tạo / Sửa nhắc lịch | FR-13, FR-14 |
| S08 | Thống kê chi phí | FR-17 |
| S09 | Loại dịch vụ | FR-11, FR-12 |
| S10 | Chẩn đoán AI (form + kết quả + các trạng thái lỗi) | FR-18 → FR-20, FR-22 |
| S11 | Lịch sử chẩn đoán | FR-21 |

**Lưu ý cho Khoa:** màn hình S10 phải có thiết kế cho cả trạng thái *đang chờ*, *thành công* và *từng loại lỗi* ở bảng BR-10. Brief chấm điểm phần "người dùng thấy gì khi AI lỗi".

## 8. Giả định và ràng buộc

- Đơn vị tiền tệ VNĐ, quãng đường km. Giao diện tiếng Việt.
- Tài liệu và code nằm chung trong repo nhóm **Zang-1/Vehicle-Maintenance-Log**; Brief chỉ tính những gì có trong repo nhóm.
- Mốc thời gian theo Brief: Week 8 (Session 16) có AI chạy trên URL live, Week 9 (Session 18) audit secret + bản nháp report đủ 8 mục, Session 20 demo.
