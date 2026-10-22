# 08 – Implementation Plan (Kế hoạch triển khai)

**Người phụ trách:** Giang · **Đầu vào:** [01 Requirements](../01-requirements/requirements.md), [04 Database](../04-database/erd.md), [07 Architecture](../07-architecture/)

> Công nghệ ở mục 1 là **đề xuất**. Lâm chốt chính thức trong tài liệu 07; nếu đổi công nghệ thì chỉ cần sửa mục 1 và tên thư mục ở mục 2, phần chia module và kiểm thử giữ nguyên.

## 1. Công nghệ đề xuất

| Tầng | Công nghệ | Lý do |
|---|---|---|
| Frontend | ReactJS (Vite) + React Router + Axios, biểu đồ bằng Chart.js | Dựng lại sát giao diện Figma, nhiều tài liệu học |
| Backend | Node.js + Express, REST API, xác thực JWT, băm mật khẩu bcrypt | Cùng ngôn ngữ JavaScript với frontend, cả nhóm chỉ cần học một ngôn ngữ |
| Database | MySQL 8.0 (script ở tài liệu 04), truy cập qua thư viện `mysql2` với truy vấn tham số hóa | Đã thiết kế và chạy thử |
| Tác vụ định kỳ | `node-cron` chạy tiến trình nhắc lịch lúc 07:00 hằng ngày | FR-21 |
| Kiểm thử | Jest + Supertest (backend), Vitest + React Testing Library (frontend), Postman (API thủ công) | |
| Công cụ | GitHub (mã nguồn, Issues, Projects), Figma, MySQL Workbench | |

## 2. Cấu trúc thư mục mã nguồn

```
Vehicle-Maintenance-Log/
├── docs/                       # Tài liệu thiết kế (01 → 08)
├── database/                   # Copy schema.sql, seed.sql từ docs/04-database khi bắt đầu code
├── backend/
│   └── src/
│       ├── config/             # Kết nối DB, biến môi trường
│       ├── middlewares/        # auth (JWT), requireAdmin, validate, upload, errorHandler
│       ├── modules/
│       │   ├── auth/           # *.routes.js · *.controller.js · *.service.js · *.repository.js
│       │   ├── users/
│       │   ├── vehicles/
│       │   ├── garages/
│       │   ├── maintenance/    # records, items, attachments
│       │   ├── service-types/
│       │   ├── reminders/
│       │   ├── notifications/
│       │   └── statistics/
│       ├── jobs/               # reminder.job.js (node-cron)
│       └── app.js
└── frontend/
    └── src/
        ├── api/                # Hàm gọi API theo module
        ├── components/         # Button, Input, Card, Table, Modal, Badge... (theo Figma)
        ├── layouts/            # AuthLayout, MainLayout, AdminLayout
        ├── pages/              # S01 → S15 (theo danh sách màn hình ở tài liệu 01)
        ├── hooks/ · contexts/  # AuthContext, useNotifications...
        └── utils/
```

Mỗi module backend có 4 lớp: **routes** (khai báo URL) → **controller** (nhận request, trả response) → **service** (quy tắc nghiệp vụ BR-xx) → **repository** (truy vấn SQL). Tên lớp khớp với class diagram ở tài liệu 07.

## 3. Chia module và phân công lập trình

Mỗi người phụ trách trọn vẹn module của mình từ API đến giao diện, để tự chịu trách nhiệm và demo độc lập được.

| Module | FR | Màn hình | Người làm | Ghi chú |
|---|---|---|---|---|
| M0. Khung dự án | – | – | **Giang** (backend, DB) + **Khoa** (frontend) | Khởi tạo repo, cấu hình, layout chung, bộ component theo Figma |
| M1. Xác thực & Tài khoản | FR-01 → FR-04 | S02, S13 | **Giang** | Làm sớm nhất vì mọi module khác cần đăng nhập |
| M2. Quản lý xe | FR-05 → FR-10 | S04, S05, S06 (tab Thông tin) | **Lâm** | |
| M3. Garage | FR-16 | S12 | **Lâm** | |
| M4. Lịch sử bảo dưỡng | FR-11 → FR-15, FR-17 | S06 (tab Lịch sử), S07, S08 | **Lâm** | Module lớn nhất, gọi hàm của M6 để tính lại mốc nhắc lịch |
| M5. Loại dịch vụ (quản trị) | FR-26 | S14 | **Khoa** | Cần xong sớm để M4, M6 có dữ liệu chọn |
| M6. Nhắc lịch & Thông báo | FR-18 → FR-23 | S06 (tab Nhắc lịch), S09, S10 | **Giang** | Gồm tiến trình `reminder.job.js` |
| M7. Dashboard & Thống kê | FR-24, FR-25 | S03, S11 | **Khoa** | Dùng view `v_record_totals`, `v_reminder_status` |
| M8. Quản trị người dùng & thống kê hệ thống | FR-27, FR-28 | S15 | **Khoa** | |

Khối lượng ước tính: Giang ~ M0 (BE) + M1 + M6 · Lâm ~ M2 + M3 + M4 · Khoa ~ M0 (FE) + M5 + M7 + M8.

### Hợp đồng giữa các module (thống nhất trước khi code)

| Bên cung cấp | Bên dùng | Nội dung |
|---|---|---|
| M1 (Giang) | Tất cả | Middleware `auth` gắn `req.user = { userId, role }`; `requireAdmin` cho route quản trị |
| M2 (Lâm) | M4, M6, M7 | `vehicleService.getOwnedVehicle(userId, vehicleId)`: trả xe hoặc lỗi 404 nếu không phải xe của mình (NFR-02) |
| M6 (Giang) | M4 | `reminderService.onMaintenanceSaved(recordId)`: tính lại mốc nhắc lịch (FR-20, BR-08) |
| M0 (Khoa) | Tất cả FE | Bộ component dùng chung, `MainLayout` có thanh điều hướng và chuông thông báo |

### Danh sách API chính

| Phương thức & URL | Mô tả | Module |
|---|---|---|
| `POST /api/auth/register` · `POST /api/auth/login` | Đăng ký, đăng nhập (trả JWT) | M1 |
| `GET/PUT /api/users/me` · `PUT /api/users/me/password` | Hồ sơ, đổi mật khẩu | M1 |
| `GET/POST /api/vehicles` · `GET/PUT/DELETE /api/vehicles/:id` | CRUD xe | M2 |
| `PATCH /api/vehicles/:id/odometer` · `PATCH /api/vehicles/:id/archive` | Cập nhật ODO, lưu trữ xe | M2 |
| `GET/POST /api/garages` · `PUT/DELETE /api/garages/:id` | CRUD garage | M3 |
| `GET/POST /api/vehicles/:id/records` | Lịch sử, ghi nhận lần bảo dưỡng | M4 |
| `GET/PUT/DELETE /api/records/:id` | Chi tiết, sửa, xóa lần bảo dưỡng | M4 |
| `POST /api/records/:id/attachments` · `DELETE /api/attachments/:id` | Hóa đơn | M4 |
| `GET /api/vehicles/:id/records/export` | Xuất CSV | M4 |
| `GET /api/service-types` · `POST/PUT /api/admin/service-types[/:id]` | Danh mục loại dịch vụ | M5 |
| `GET/POST /api/vehicles/:id/reminders` · `PUT/DELETE /api/reminders/:id` | Nhắc lịch | M6 |
| `GET /api/notifications` · `PATCH /api/notifications/:id/read` · `PATCH /api/notifications/read-all` | Thông báo | M6 |
| `GET /api/statistics/dashboard` · `GET /api/statistics/costs?groupBy=month\|vehicle\|serviceType` | Dashboard, thống kê | M7 |
| `GET /api/admin/users` · `PATCH /api/admin/users/:id/status` · `GET /api/admin/statistics` | Quản trị | M8 |

## 4. Thứ tự lập trình (6 sprint × 1 tuần)

Thứ tự theo phụ thuộc: khung dự án → đăng nhập → danh mục và xe → bảo dưỡng → nhắc lịch → thống kê.

| Sprint | Giang | Lâm | Khoa | Kết quả cuối sprint |
|---|---|---|---|---|
| 1 | M0: khởi tạo backend, kết nối MySQL, chạy `schema.sql`, middleware lỗi | Học cấu trúc dự án, viết `vehicle.repository` | M0: khởi tạo frontend, router, layout, component theo Figma | Chạy được FE + BE + DB trên máy cả 3 người |
| 2 | M1: đăng ký, đăng nhập, JWT, hồ sơ | M2: API + màn hình danh sách/thêm/sửa xe | M5: quản lý loại dịch vụ | Đăng nhập rồi thêm được xe |
| 3 | M6 (phần 1): CRUD nhắc lịch, tính mốc đến hạn, `onMaintenanceSaved` | M4 (phần 1): ghi nhận lần bảo dưỡng + hạng mục, lịch sử | M7 (phần 1): Dashboard | Ghi nhận bảo dưỡng → nhắc lịch tự cập nhật |
| 4 | M6 (phần 2): tiến trình nhắc lịch, thông báo, chuông | M4 (phần 2): sửa/xóa, chi tiết, đính kèm hóa đơn; M3 garage | M7 (phần 2): thống kê chi phí, biểu đồ | **Đủ toàn bộ chức năng Must** |
| 5 | Kiểm thử tích hợp, sửa lỗi; FR-03, FR-23 nếu kịp | FR-17 xuất CSV; kiểm thử M2–M4 | M8 quản trị người dùng; responsive | Đủ chức năng Should, bắt đầu kiểm thử hệ thống |
| 6 | Kiểm thử hệ thống, chuẩn bị dữ liệu demo, hoàn thiện tài liệu | Sửa lỗi, viết hướng dẫn sử dụng | Chỉnh giao diện, quay video demo | Bản nộp cuối, demo |

Mốc kiểm tra: **cuối sprint 2** (đăng nhập + xe), **cuối sprint 4** (đủ Must), **cuối sprint 6** (nộp).

## 5. Kế hoạch kiểm thử

### 5.1. Các mức kiểm thử

| Mức | Phạm vi | Công cụ | Ai làm | Khi nào |
|---|---|---|---|---|
| Unit test | Hàm service chứa quy tắc nghiệp vụ: tính mốc nhắc lịch, trạng thái nhắc lịch, kiểm tra ODO, tính tổng chi phí | Jest | Người viết module | Trong sprint, cùng lúc viết code |
| Integration test | API + database thật (database test riêng) | Jest + Supertest | Người viết module | Trước khi mở Pull Request |
| System test | Chạy các kịch bản đầu-cuối trên giao diện theo bảng test case | Thủ công, ghi kết quả vào Google Sheet / GitHub Issues | Kiểm thử chéo: Giang test M2–M4, Lâm test M5/M7/M8, Khoa test M1/M6 | Sprint 5–6 |
| Acceptance test | Đối chiếu từng FR mức Must/Should với tài liệu 01 | Checklist | Cả nhóm | Cuối sprint 6 |

Mục tiêu: unit test phủ ≥ 70% các file `*.service.js`; 100% FR mức Must có ít nhất một test case hệ thống đạt.

### 5.2. Test case mẫu

| Mã | FR / BR | Kịch bản | Dữ liệu vào | Kết quả mong đợi |
|---|---|---|---|---|
| TC-01 | FR-01, BR-01 | Đăng ký email đã tồn tại | email `an@vml.local` | Báo lỗi "Email đã được sử dụng", không tạo tài khoản |
| TC-02 | FR-02, BR-13 | Đăng nhập tài khoản bị khóa | Tài khoản `is_active = FALSE` | Báo lỗi "Tài khoản đã bị khóa" |
| TC-03 | NFR-02 | Xem xe của người khác | User 2 gọi `GET /api/vehicles/3` | 404, không lộ dữ liệu |
| TC-04 | FR-05, BR-02 | Thêm xe trùng biển số của chính mình | Biển `59X1-123.45` | Báo lỗi trùng biển số |
| TC-05 | FR-09, BR-03 | Nhập ODO nhỏ hơn hiện tại | Xe ODO 12.850, nhập 12.000 | Báo lỗi, ODO giữ nguyên |
| TC-06 | FR-11, BR-05 | Lưu lần bảo dưỡng không có hạng mục | 0 hạng mục | Báo lỗi "Cần ít nhất một hạng mục" |
| TC-07 | FR-11, BR-04 | Ngày bảo dưỡng ở tương lai | Ngày mai | Báo lỗi |
| TC-08 | FR-11, BR-06 | Tính tổng chi phí | 4 × 210.000 + 1 × 150.000 | Tổng = 990.000 |
| TC-09 | FR-11, BR-03 | Lần bảo dưỡng có ODO lớn hơn ODO xe | Xe ODO 12.850, nhập 13.000 | ODO xe thành 13.000 |
| TC-10 | FR-20, BR-08 | Ghi nhận thay nhớt cho xe có nhắc lịch thay nhớt (1.500 km / 2 tháng) | Ngày 2026-10-22, ODO 13.000 | Mốc mới: 2026-12-22 hoặc 14.500 km; trạng thái "Còn hạn" |
| TC-11 | BR-07, BR-09 | Trạng thái khi km đến trước ngày | Còn 200 km, còn 30 ngày, ngưỡng 300 km/7 ngày | "Sắp đến hạn" |
| TC-12 | FR-21, BR-10 | Chạy tiến trình nhắc lịch 2 lần trong ngày | Nhắc lịch đang quá hạn | Chỉ sinh 1 thông báo |
| TC-13 | FR-18, BR-11 | Tạo nhắc lịch trùng loại dịch vụ trên cùng xe | Đã có nhắc "Thay nhớt" | Báo lỗi trùng |
| TC-14 | FR-10, BR-12 | Xóa xe đã có lịch sử | Xe 1 | Không cho xóa, gợi ý "Lưu trữ" |
| TC-15 | FR-15, NFR-08 | Tải hóa đơn 6 MB hoặc file `.exe` | | Báo lỗi định dạng/kích thước |
| TC-16 | FR-26, BR-14 | Xóa loại dịch vụ đã được dùng | "Thay nhớt máy (xe máy)" | Chỉ cho phép ngừng sử dụng |
| TC-17 | NFR-02 | Người dùng thường gọi API quản trị | `GET /api/admin/users` với token USER | 403 |
| TC-18 | FR-25 | Thống kê chi phí theo tháng năm 2026 của user 2 (dữ liệu `seed.sql`) | | 02: 1.960.000 · 03: 255.000 · 06: 135.000 · 08: 1.305.000 |

### 5.3. Quy trình xử lý lỗi

1. Người phát hiện tạo GitHub Issue, gắn nhãn `bug`, ghi bước tái hiện, kết quả mong đợi/thực tế, ảnh chụp, mã test case.
2. Giao cho người phụ trách module (bảng ở mục 3).
3. Sửa trên nhánh `fix/...`, trong Pull Request ghi `Fixes #<số issue>`; người phát hiện kiểm tra lại rồi đóng issue.

## 6. Quy trình làm việc với Git

- Nhánh `main` luôn chạy được; **không push thẳng** vào `main` khi đã bắt đầu code.
- Đặt tên nhánh: `feature/<module>-<mô tả>` (ví dụ `feature/m2-add-vehicle`), `fix/<mô tả>`, `docs/<bước>` (ví dụ `docs/02-use-case`).
- Commit message: `<loại>: <nội dung>` với loại ∈ `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Ví dụ: `feat(vehicles): them API cap nhat ODO`.
- Mỗi Pull Request cần **1 người khác duyệt** và test đi kèm chạy qua mới được merge.
- Trước khi bắt đầu làm mỗi ngày: `git checkout main && git pull`, rồi tạo/cập nhật nhánh của mình.
- Không commit file `.env`, `node_modules/`, file hóa đơn tải lên.

## 7. Định nghĩa "Hoàn thành" (Definition of Done)

Một chức năng được tính là xong khi:
- [ ] Đáp ứng đúng mô tả FR và các BR liên quan.
- [ ] Giao diện khớp thiết kế Figma, hiển thị được trên điện thoại.
- [ ] Có unit test cho logic nghiệp vụ và integration test cho API.
- [ ] Kiểm tra quyền truy cập (chỉ dữ liệu của mình, route quản trị chỉ cho ADMIN).
- [ ] Pull Request đã được duyệt và merge vào `main`.

## 8. Rủi ro và cách xử lý

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Thành viên chưa quen công nghệ | Chậm tiến độ sprint 1–2 | Sprint 1 dành cho dựng khung và học; Giang hướng dẫn cấu trúc module mẫu (M1) để mọi người làm theo |
| Module phụ thuộc nhau (M4 cần M2, M6) | Người sau phải chờ | Thống nhất "hợp đồng giữa các module" (mục 3) từ đầu; dùng dữ liệu `seed.sql` để làm song song |
| Lệch giữa thiết kế và code | Giao diện/DB không khớp tài liệu | Mọi thay đổi bảng/cột phải sửa `schema.sql` + tài liệu 04 trong cùng Pull Request |
| Xung đột khi merge | Mất thời gian | Pull `main` thường xuyên, Pull Request nhỏ, mỗi người làm trên thư mục module của mình |
| Trễ hạn | Thiếu chức năng khi nộp | Ưu tiên theo Must → Should → Could; chức năng Could chỉ làm khi đã đủ Must ở cuối sprint 4 |
