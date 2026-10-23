# Phân công công việc – Vehicle Maintenance Log

Môn **72ITDS30103 – Software Development Platforms**

| Thành viên | GitHub | Vai trò chính |
|---|---|---|
| **Kiều Bảo Giang** (nhóm trưởng) | @Zang-1 | Yêu cầu · Database · AI · Kế hoạch |
| **Tăng Thoại Lâm** | @noway165 | UML · Kiến trúc · CI/CD + Render |
| **Nguyễn Nam Khoa** | @namkhoa306 | Giao diện · Docker/Compose |

Mỗi người có 3 loại việc: **tài liệu thiết kế** (8 bước), **code**, và **report + thuyết trình** theo Final Project Brief. Brief chấm cá nhân dựa trên commit của chính mình (4/10 điểm bảo vệ), nên ai làm phần nào thì commit phần đó.

## 1. Tài liệu thiết kế (8 bước)

| # | Bước | Người làm | Cần có trước | Sản phẩm nộp |
|---|---|---|---|---|
| 01 | Requirements | Giang ✅ | – | [`01-requirements/requirements.md`](01-requirements/requirements.md) |
| 02 | Use Case Diagram | Lâm ✅ | 01 | `02-use-case/`: sơ đồ + đặc tả use case chính, ghi mã `FR-xx` |
| 03 | Activity Diagram | Lâm ✅ | 01, 02 | `03-activity/`: ghi nhận bảo dưỡng, tạo nhắc lịch, **chẩn đoán AI (có nhánh lỗi)**, luồng CI/CD |
| 04 | ERD & Database Design | Giang ✅ | 01 | [`04-database/`](04-database/erd.md): ERD, từ điển dữ liệu, `schema.sql`, `seed.sql` (PostgreSQL, chạy được trên Supabase) |
| 05 | Wireframe | Khoa | 01, 02 | `05-wireframe/`: 11 màn hình S01–S11 |
| 06 | UI Design trên Figma | Khoa | 05 | `06-ui-design/`: link Figma, style guide, component, ảnh xuất |
| 07 | Architecture & Class Diagram | Lâm ✅ | 02, 04 | `07-architecture/`: **sơ đồ triển khai khớp thực tế** (Render + Supabase + Gemini + GitHub Actions), class diagram |
| 08 | Implementation Plan | Giang ✅ | 04, 07 | [`08-implementation-plan/implementation-plan.md`](08-implementation-plan/implementation-plan.md) |

## 2. Code

| Module | Người làm |
|---|---|
| M1 Database (Supabase, schema, pool) · M5 Nhắc lịch · M7 Chẩn đoán AI | **Giang** |
| M2 Xe · M3 Lần bảo dưỡng · P1 CI/CD + Render | **Lâm** |
| M0 Khung dự án FastAPI (cùng Giang) · M4 Loại dịch vụ · M6 Giao diện chung, Dashboard, Thống kê · P2 Dockerfile + Compose | **Khoa** |

Chi tiết từng module, API và hợp đồng giữa các module: mục 4 của [Implementation Plan](08-implementation-plan/implementation-plan.md).

## 3. Report và thuyết trình

| Người | Mục report | Khối thuyết trình |
|---|---|---|
| Giang | 5 Database · 6 AI · 7 Secret (cùng Khoa) · 8 tổng hợp bảng đóng góp | Dẫn demo |
| Lâm | 1 Platform selection · 2 Architecture · 4 CI/CD | Kiến trúc · Một lỗi đã gặp và cách sửa |
| Khoa | 3 Dockerfile & Compose · 7 Secret (cùng Giang) | Giới thiệu ứng dụng · Nếu làm lại · Clean clone trong demo |

## 4. Lộ trình theo phase

| Phase | Thời gian | Giang | Lâm | Khoa |
|---|---|---|---|---|
| **1. Thiết kế** ✅ | đến 25/10 | 01 · 04 · 08 ✅ | 02 · 03 · 07 ✅ | 05 trước 24/10 · 06 trước 29/10 |
| **2. Chạy local** | T6 23/10 → **T2 26/10** | Khung FastAPI + DB (M0, M1) · API + tab Nhắc lịch (M5) | Workflow CI + branch protection (P1) · Xe: xem, thêm (M2) · Lịch sử: xem (M3) | Dockerfile + Compose (P2) · `base.html`, Dashboard (M6) · API loại dịch vụ (M4) |
| **3. Lên Render + Supabase** | T3 27/10 → **T5 29/10** | Tạo Supabase, chạy schema + seed, đưa `DATABASE_URL` cho Lâm, thử pause/restore | Tạo Render service, đặt biến môi trường, deploy hook + job `deploy`, thử commit đến production | 06 Figma · trang S09 · giao diện trên điện thoại · URL vào README |
| **4. Hoàn thiện** | T6 30/10 → CN 8/11 | AI trên URL live (M7) · tạo/sửa nhắc lịch · audit secret · report mục 5, 6, 7 | Ghi nhận/sửa/xóa bảo dưỡng · sửa xe, lưu trữ, CSV · report mục 1, 2, 4 | Thống kê chi phí · chỉnh theo Figma · report mục 3, 7 |
| **5. Tập demo và nộp** | T2 9/11 → Session 20 | Report PDF, tập demo có bấm giờ | Nhánh "cố tình đỏ" cho demo | Clean clone trên máy khác · slide |

Mốc kiểm tra: **tối T2 26/10** (clean clone chạy được local trên 2 máy), **tối T5 29/10** (URL Render chạy với Supabase, merge là tự deploy). Việc theo từng ngày và điều kiện xong mỗi phase: mục 6 của [Implementation Plan](08-implementation-plan/implementation-plan.md).

## 5. Quy ước chung

- **Tên gọi thống nhất:** dùng chung mã `FR-xx`, `BR-xx` (tài liệu 01) và tên bảng/cột (tài liệu 04) trong use case, wireframe, class diagram và code.
- **Review chéo:** Lâm review tài liệu và PR của Giang, Giang review của Lâm, Khoa đối chiếu giao diện với 01–02 và review PR M2/M3. Review phải có nhận xét thật.
- **Git:** làm trên nhánh riêng, mở PR vào `main`, cần 1 người duyệt và check xanh mới merge; merge xong thì xóa nhánh. Không commit `.env`, key hay connection string ở bất kỳ đâu, kể cả ảnh chụp.
- **Sơ đồ:** ưu tiên Mermaid trong file `.md` (GitHub tự hiển thị). Nếu vẽ bằng draw.io/StarUML thì nộp cả file gốc lẫn ảnh `.png`.
