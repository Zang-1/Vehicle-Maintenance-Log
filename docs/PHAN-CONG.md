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
| 02 | Use Case Diagram | Lâm | 01 | `02-use-case/`: sơ đồ + đặc tả use case chính, ghi mã `FR-xx` |
| 03 | Activity Diagram | Lâm | 01, 02 | `03-activity/`: ghi nhận bảo dưỡng, tạo nhắc lịch, **chẩn đoán AI (có nhánh lỗi)**, luồng CI/CD |
| 04 | ERD & Database Design | Giang ✅ | 01 | [`04-database/`](04-database/erd.md): ERD, từ điển dữ liệu, `schema.sql`, `seed.sql` (PostgreSQL, chạy được trên Supabase) |
| 05 | Wireframe | Khoa | 01, 02 | `05-wireframe/`: 11 màn hình S01–S11 |
| 06 | UI Design trên Figma | Khoa | 05 | `06-ui-design/`: link Figma, style guide, component, ảnh xuất |
| 07 | Architecture & Class Diagram | Lâm | 02, 04 | `07-architecture/`: **sơ đồ triển khai khớp thực tế** (Render + Supabase + Gemini + GitHub Actions), class diagram |
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

## 4. Lịch theo mốc của Brief

| Tuần | Giang | Lâm | Khoa |
|---|---|---|---|
| **W7** (hiện tại) | Khung FastAPI + `/health`, `/health/db`; Supabase + schema (M1) | 02 Use Case, 03 Activity; workflow CI | 05 Wireframe; Dockerfile + Compose (P2) |
| **W8** – AI live | M7 Chẩn đoán AI | 07 Architecture; M2 Xe; Render + deploy tự động (P1) | 06 Figma; `base.html` + CSS |
| **W9** – audit + nháp report | M5 Nhắc lịch; audit secret | M3 Lần bảo dưỡng | M4 Loại dịch vụ; Dashboard, Thống kê |
| **W10** – tập demo, nộp report | Hoàn thiện report | Nhánh "cố tình đỏ" cho demo | Clean clone trên máy khác; slide |

## 5. Quy ước chung

- **Tên gọi thống nhất:** dùng chung mã `FR-xx`, `BR-xx` (tài liệu 01) và tên bảng/cột (tài liệu 04) trong use case, wireframe, class diagram và code.
- **Review chéo:** Lâm review tài liệu và PR của Giang, Giang review của Lâm, Khoa đối chiếu giao diện với 01–02 và review PR M2/M3. Review phải có nhận xét thật.
- **Git:** làm trên nhánh riêng, mở PR vào `main`, cần 1 người duyệt và check xanh mới merge; merge xong thì xóa nhánh. Không commit `.env`, key hay connection string ở bất kỳ đâu, kể cả ảnh chụp.
- **Sơ đồ:** ưu tiên Mermaid trong file `.md` (GitHub tự hiển thị). Nếu vẽ bằng draw.io/StarUML thì nộp cả file gốc lẫn ảnh `.png`.
