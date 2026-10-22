# 01 – Requirements (Đặc tả yêu cầu)

**Người phụ trách:** Giang · **Phiên bản:** 1.0

## 1. Giới thiệu

### 1.1. Bối cảnh

Nhiều chủ xe máy, ô tô không nhớ lần cuối thay nhớt, thay lọc gió hay bảo dưỡng định kỳ là khi nào, ở số km bao nhiêu và tốn bao nhiêu tiền. Hóa đơn giấy dễ thất lạc, sổ bảo dưỡng của hãng thì chỉ ghi ở đại lý. Hậu quả là bỏ lỡ mốc bảo dưỡng, xe xuống cấp nhanh và không kiểm soát được chi phí.

### 1.2. Mục đích hệ thống

**Vehicle Maintenance Log** là ứng dụng giúp chủ xe:

1. Lưu trữ thông tin các xe mình sở hữu.
2. Ghi lại lịch sử bảo dưỡng, sửa chữa (ngày, số km, hạng mục, chi phí, nơi làm, hóa đơn).
3. Được nhắc trước khi đến hạn bảo dưỡng theo **thời gian** hoặc **số km**.
4. Theo dõi tổng chi phí bảo dưỡng theo xe, theo tháng, theo hạng mục.

### 1.3. Phạm vi

| Trong phạm vi | Ngoài phạm vi (phiên bản này) |
|---|---|
| Quản lý tài khoản, xe, lịch sử bảo dưỡng, nhắc lịch, thông báo trong ứng dụng, thống kê chi phí, quản trị danh mục | Đặt lịch hẹn trực tiếp với garage |
| Đính kèm ảnh hóa đơn | Thanh toán trực tuyến |
| Xuất lịch sử bảo dưỡng ra file CSV | Theo dõi nhiên liệu, GPS, kết nối OBD |
| Gửi email nhắc lịch (tùy chọn, làm nếu kịp) | Ứng dụng di động gốc (native) |

### 1.4. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Xe | Phương tiện do người dùng sở hữu: xe máy, ô tô hoặc loại khác |
| Odometer (ODO) | Số km xe đã chạy, hiển thị trên đồng hồ công-tơ-mét |
| Lần bảo dưỡng (phiếu bảo dưỡng) | Một lần mang xe đi bảo dưỡng/sửa chữa, có thể gồm nhiều hạng mục |
| Hạng mục | Một công việc cụ thể trong lần bảo dưỡng, ví dụ "Thay nhớt máy", "Thay má phanh" |
| Loại dịch vụ | Danh mục chuẩn các hạng mục do quản trị viên quản lý, kèm chu kỳ khuyến nghị |
| Nhắc lịch | Quy tắc nhắc cho một loại dịch vụ của một xe: cứ X km hoặc Y tháng thì làm lại |
| Garage | Nơi thực hiện bảo dưỡng (đại lý, tiệm sửa xe) |

## 2. Người dùng (tác nhân)

| Tác nhân | Mô tả | Nhu cầu chính |
|---|---|---|
| **Khách** | Người chưa đăng nhập | Xem giới thiệu, đăng ký, đăng nhập, lấy lại mật khẩu |
| **Người dùng** (chủ xe) | Người đã có tài khoản; là đối tượng chính | Quản lý xe, ghi lịch sử bảo dưỡng, nhận nhắc lịch, xem chi phí |
| **Quản trị viên** | Người vận hành hệ thống | Quản lý tài khoản người dùng, quản lý danh mục loại dịch vụ, xem số liệu tổng quan |
| **Hệ thống nhắc lịch** (tác nhân thời gian) | Tiến trình chạy định kỳ của hệ thống | Kiểm tra các nhắc lịch sắp/đã đến hạn và sinh thông báo |

## 3. Mục tiêu

| Mã | Mục tiêu | Cách đo |
|---|---|---|
| G-01 | Ghi một lần bảo dưỡng nhanh | Người dùng mới ghi xong một lần bảo dưỡng 1 hạng mục trong ≤ 1 phút |
| G-02 | Không bỏ lỡ mốc bảo dưỡng | 100% nhắc lịch đến hạn đều sinh thông báo trong vòng 24 giờ |
| G-03 | Minh bạch chi phí | Người dùng xem được tổng chi phí theo xe / tháng / hạng mục trong 1 màn hình |
| G-04 | Dữ liệu an toàn, riêng tư | Người dùng chỉ thấy dữ liệu của chính mình |

## 4. Yêu cầu chức năng (Functional Requirements)

Mức ưu tiên: **Must** = bắt buộc cho bản demo · **Should** = nên có · **Could** = làm nếu kịp.

### 4.1. Tài khoản

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-01 | Đăng ký | Tạo tài khoản bằng họ tên, email, mật khẩu. Email không được trùng | Khách | Must |
| FR-02 | Đăng nhập / Đăng xuất | Đăng nhập bằng email + mật khẩu; đăng xuất khỏi phiên | Khách, Người dùng, QTV | Must |
| FR-03 | Quên mật khẩu | Gửi liên kết đặt lại mật khẩu qua email | Khách | Could |
| FR-04 | Cập nhật hồ sơ | Sửa họ tên, số điện thoại; đổi mật khẩu (phải nhập mật khẩu cũ) | Người dùng | Should |

### 4.2. Quản lý xe

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-05 | Thêm xe | Nhập tên gợi nhớ, loại xe, hãng, dòng xe, năm sản xuất, biển số, số khung (VIN), số km hiện tại, ngày mua, ảnh xe | Người dùng | Must |
| FR-06 | Xem danh sách xe | Hiển thị các xe của mình dạng thẻ: ảnh, tên, biển số, ODO, số nhắc lịch sắp đến hạn | Người dùng | Must |
| FR-07 | Xem chi tiết xe | Thông tin xe + lịch sử bảo dưỡng gần nhất + các nhắc lịch của xe | Người dùng | Must |
| FR-08 | Sửa thông tin xe | Sửa các trường ở FR-05 | Người dùng | Must |
| FR-09 | Cập nhật số km | Nhập số ODO mới cho xe (không được nhỏ hơn số hiện tại) | Người dùng | Must |
| FR-10 | Lưu trữ / Xóa xe | Lưu trữ xe đã bán (ẩn khỏi danh sách, giữ lịch sử); xóa hẳn chỉ khi xe chưa có lịch sử | Người dùng | Should |

### 4.3. Lịch sử bảo dưỡng

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-11 | Ghi nhận lần bảo dưỡng | Chọn xe, ngày, số ODO lúc làm, garage, ghi chú; thêm một hoặc nhiều hạng mục (loại dịch vụ, mô tả, số lượng, đơn giá) | Người dùng | Must |
| FR-12 | Xem lịch sử bảo dưỡng | Danh sách các lần bảo dưỡng của một xe, mới nhất trước; lọc theo khoảng ngày, loại dịch vụ | Người dùng | Must |
| FR-13 | Xem chi tiết lần bảo dưỡng | Các hạng mục, tổng chi phí, garage, ảnh hóa đơn | Người dùng | Must |
| FR-14 | Sửa / Xóa lần bảo dưỡng | Sửa thông tin và hạng mục; xóa có xác nhận | Người dùng | Must |
| FR-15 | Đính kèm hóa đơn | Tải lên ảnh/PDF hóa đơn cho một lần bảo dưỡng | Người dùng | Should |
| FR-16 | Quản lý garage | Lưu danh sách garage hay dùng (tên, địa chỉ, SĐT) để chọn nhanh khi ghi nhận | Người dùng | Should |
| FR-17 | Xuất CSV | Xuất lịch sử bảo dưỡng của một xe ra file CSV | Người dùng | Could |

### 4.4. Nhắc lịch và thông báo

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-18 | Tạo nhắc lịch | Chọn xe + loại dịch vụ, đặt chu kỳ theo km và/hoặc theo tháng (gợi ý sẵn từ chu kỳ mặc định của loại dịch vụ), đặt ngưỡng báo trước | Người dùng | Must |
| FR-19 | Xem / Sửa / Tạm dừng / Xóa nhắc lịch | Danh sách nhắc lịch kèm trạng thái: Còn hạn / Sắp đến hạn / Quá hạn | Người dùng | Must |
| FR-20 | Tự cập nhật mốc nhắc | Khi ghi nhận lần bảo dưỡng có hạng mục trùng loại dịch vụ của nhắc lịch, hệ thống tự tính lại mốc đến hạn tiếp theo | Hệ thống | Must |
| FR-21 | Sinh thông báo | Định kỳ mỗi ngày, hệ thống kiểm tra nhắc lịch sắp đến hạn/quá hạn và tạo thông báo trong ứng dụng | Hệ thống nhắc lịch | Must |
| FR-22 | Xem thông báo | Biểu tượng chuông hiển thị số thông báo chưa đọc; xem danh sách, đánh dấu đã đọc | Người dùng | Must |
| FR-23 | Gửi email nhắc lịch | Gửi email kèm thông báo nếu người dùng bật tùy chọn | Hệ thống nhắc lịch | Could |

### 4.5. Thống kê

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-24 | Dashboard | Trang chủ sau đăng nhập: số xe, nhắc lịch sắp đến hạn, chi phí tháng này, các lần bảo dưỡng gần đây | Người dùng | Must |
| FR-25 | Thống kê chi phí | Biểu đồ chi phí theo tháng, theo xe, theo loại dịch vụ trong khoảng thời gian chọn | Người dùng | Should |

### 4.6. Quản trị

| Mã | Chức năng | Mô tả | Tác nhân | Ưu tiên |
|---|---|---|---|---|
| FR-26 | Quản lý loại dịch vụ | Thêm/sửa/ngừng dùng loại dịch vụ: tên, mô tả, áp dụng cho loại xe, chu kỳ mặc định (km, tháng) | QTV | Must |
| FR-27 | Quản lý người dùng | Xem danh sách, tìm kiếm, khóa/mở khóa tài khoản | QTV | Should |
| FR-28 | Thống kê hệ thống | Số người dùng, số xe, số lần bảo dưỡng được ghi theo tháng | QTV | Could |

## 5. Yêu cầu phi chức năng (Non-functional Requirements)

| Mã | Nhóm | Yêu cầu |
|---|---|---|
| NFR-01 | Bảo mật | Mật khẩu lưu dạng băm (bcrypt), không lưu bản rõ |
| NFR-02 | Bảo mật | Mọi API (trừ đăng ký/đăng nhập) yêu cầu xác thực; người dùng chỉ truy cập dữ liệu của mình; chức năng quản trị chỉ dành cho vai trò ADMIN |
| NFR-03 | Bảo mật | Chống SQL Injection (dùng truy vấn tham số hóa/ORM), kiểm tra dữ liệu đầu vào ở cả client và server |
| NFR-04 | Hiệu năng | Các màn hình danh sách phản hồi < 2 giây với 1.000 bản ghi bảo dưỡng/người dùng |
| NFR-05 | Khả dụng | Giao diện tiếng Việt, responsive (máy tính và điện thoại, chiều rộng từ 360px) |
| NFR-06 | Khả dụng | Thông báo lỗi rõ ràng, gắn với ô nhập bị sai |
| NFR-07 | Tin cậy | Xóa dữ liệu quan trọng (xe, lần bảo dưỡng) phải có hộp thoại xác nhận |
| NFR-08 | Lưu trữ | File hóa đơn tối đa 5 MB, định dạng JPG/PNG/PDF |
| NFR-09 | Bảo trì | Mã nguồn quản lý bằng Git trên GitHub, theo quy ước ở tài liệu 08 |
| NFR-10 | Tương thích | Chạy tốt trên Chrome, Edge, Firefox bản mới nhất |

## 6. Quy tắc nghiệp vụ (Business Rules)

| Mã | Quy tắc |
|---|---|
| BR-01 | Mỗi email chỉ đăng ký được một tài khoản |
| BR-02 | Biển số xe là duy nhất trong phạm vi các xe của một người dùng (không bắt buộc nhập với xe chưa có biển) |
| BR-03 | Số ODO của xe không được giảm. Khi ghi nhận lần bảo dưỡng có ODO lớn hơn ODO hiện tại, ODO của xe được cập nhật theo |
| BR-04 | Ngày bảo dưỡng không được ở tương lai |
| BR-05 | Một lần bảo dưỡng phải có ít nhất một hạng mục |
| BR-06 | Chi phí hạng mục = số lượng × đơn giá, không âm. Tổng chi phí lần bảo dưỡng = tổng chi phí các hạng mục |
| BR-07 | Nhắc lịch phải có ít nhất một chu kỳ: theo km hoặc theo tháng. Có cả hai thì cái nào đến trước tính là đến hạn |
| BR-08 | Mốc đến hạn = lần làm gần nhất + chu kỳ (ngày + số tháng, ODO + số km). Nếu chưa có lần làm nào thì tính từ ngày/ODO lúc tạo nhắc lịch |
| BR-09 | Trạng thái nhắc lịch: **Quá hạn** nếu đã qua mốc; **Sắp đến hạn** nếu còn ≤ ngưỡng báo trước (mặc định 7 ngày hoặc 300 km); còn lại là **Còn hạn** |
| BR-10 | Mỗi nhắc lịch chỉ sinh tối đa một thông báo cho mỗi trạng thái (Sắp đến hạn, Quá hạn) trong một chu kỳ, tránh thông báo lặp |
| BR-11 | Một xe chỉ có một nhắc lịch cho mỗi loại dịch vụ |
| BR-12 | Xe đã có lịch sử bảo dưỡng không được xóa hẳn, chỉ được lưu trữ |
| BR-13 | Tài khoản bị khóa không đăng nhập được; dữ liệu vẫn được giữ |
| BR-14 | Loại dịch vụ đã được dùng thì không xóa, chỉ ngừng sử dụng (ẩn khỏi danh sách chọn) |

## 7. Danh sách màn hình dự kiến

Dùng làm đầu vào cho Wireframe (05) và UI Design (06).

| # | Màn hình | FR liên quan |
|---|---|---|
| S01 | Trang giới thiệu (landing) | – |
| S02 | Đăng ký / Đăng nhập / Quên mật khẩu | FR-01 → FR-03 |
| S03 | Dashboard | FR-24 |
| S04 | Danh sách xe | FR-06, FR-10 |
| S05 | Thêm / Sửa xe | FR-05, FR-08 |
| S06 | Chi tiết xe (tab Thông tin · Lịch sử · Nhắc lịch) | FR-07, FR-09, FR-12, FR-19 |
| S07 | Ghi nhận / Sửa lần bảo dưỡng | FR-11, FR-14, FR-15 |
| S08 | Chi tiết lần bảo dưỡng | FR-13 |
| S09 | Tạo / Sửa nhắc lịch | FR-18, FR-19 |
| S10 | Thông báo | FR-22 |
| S11 | Thống kê chi phí | FR-25 |
| S12 | Garage của tôi | FR-16 |
| S13 | Hồ sơ cá nhân | FR-04 |
| S14 | Quản trị: Loại dịch vụ | FR-26 |
| S15 | Quản trị: Người dùng · Thống kê hệ thống | FR-27, FR-28 |

## 8. Giả định và ràng buộc

- Ứng dụng web, một người dùng có thể có nhiều xe; mỗi xe chỉ thuộc một người dùng (chưa hỗ trợ chia sẻ xe).
- Đơn vị tiền tệ là VNĐ, đơn vị quãng đường là km.
- Tiến trình nhắc lịch chạy mỗi ngày một lần (ví dụ 7:00 sáng).
- Nhóm 3 người, thời gian khoảng 4 tuần cho phần thiết kế và 6 tuần cho phần lập trình (xem tài liệu 08).
