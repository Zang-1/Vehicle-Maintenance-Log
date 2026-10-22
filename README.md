# Vehicle Maintenance Log – Tài liệu thiết kế

Ứng dụng web giúp chủ xe máy, ô tô **lưu lịch sử bảo dưỡng**, **biết hạng mục nào sắp đến hạn** (theo ngày hoặc số km), **theo dõi chi phí**, và **chẩn đoán triệu chứng bằng AI** (Google Gemini).

Đồ án cuối kỳ môn **72ITDS30103 – Software Development Platforms**, VLU, HK 261.

| | |
|---|---|
| **Repo code** | [noway165/team01](https://github.com/noway165/team01) (repo dùng cho Lab 1–5 và chấm điểm) |
| **URL live** | https://team01-1lr2.onrender.com |
| **Công nghệ** | FastAPI · Jinja2 · PostgreSQL 16 (Compose / Supabase) · Podman · Render · GitHub Actions · Gemini API |

Repo này chỉ chứa **tài liệu thiết kế** (8 bước). Code nằm ở `team01`.

## Thành viên và phân công

| Thành viên | GitHub | Tài liệu | Code (`team01`) |
|---|---|---|---|
| **Kiều Bảo Giang** (nhóm trưởng) | @Zang-1 | 01 · 04 · 08 | Database (Supabase) · Nhắc lịch · Chẩn đoán AI |
| **Tăng Thoại Lâm** | @noway165 | 02 · 03 · 07 | Xe · Lần bảo dưỡng · CI/CD + Render |
| **Nguyễn Nam Khoa** | @namkhoa306 | 05 · 06 | Loại dịch vụ · Giao diện, Dashboard · Dockerfile + Compose |

Chi tiết (report, thuyết trình, lịch theo tuần): [docs/PHAN-CONG.md](docs/PHAN-CONG.md).

## Tài liệu thiết kế

| # | Bước | Người làm | Trạng thái |
|---|---|---|---|
| 01 | [Requirements](docs/01-requirements/requirements.md) | Giang | ✅ Xong |
| 02 | [Use Case Diagram](docs/02-use-case/) | Lâm | ⏳ |
| 03 | [Activity Diagram](docs/03-activity/) | Lâm | ⏳ |
| 04 | [ERD & Database Design](docs/04-database/erd.md) | Giang | ✅ Xong (đã chạy thử trên PostgreSQL 16) |
| 05 | [Wireframe](docs/05-wireframe/) | Khoa | ⏳ |
| 06 | [UI Design trên Figma](docs/06-ui-design/) | Khoa | ⏳ |
| 07 | [Architecture & Class Diagram](docs/07-architecture/) | Lâm | ⏳ |
| 08 | [Implementation Plan](docs/08-implementation-plan/implementation-plan.md) | Giang | ✅ Xong (cập nhật lại sau khi có 07) |

## Các lab được áp dụng

| Lab | Áp dụng vào |
|---|---|
| Lab 1 – Git/GitHub, Week 2 – Collaboration | Quy trình branch → PR → review → merge, `main` được bảo vệ |
| Lab 2 – Dockerfile | Đóng gói app thành image |
| Week 4 – Compose | `podman compose up --build` dựng web + PostgreSQL từ clean clone |
| Lab 3 – Render | URL HTTPS công khai |
| Lab 4 – GitHub Actions | CI (ruff, pytest, build) chặn PR hỏng; merge là tự deploy |
| Week 7 – Supabase | PostgreSQL trên cloud, `schema.sql`/`seed.sql` chạy lại được, RLS, connection pool |
| Lab 5 – AI API | Chẩn đoán triệu chứng bằng Gemini, gọi từ server, xử lý lỗi 429/timeout |

Bảng đầy đủ kèm trạng thái: mục 1 của [Implementation Plan](docs/08-implementation-plan/implementation-plan.md).

## Cách đóng góp

1. Clone: `git clone https://github.com/Zang-1/Vehicle-Maintenance-Log.git`
2. Tạo nhánh cho phần của mình, ví dụ `git checkout -b docs/02-use-case`.
3. Đặt file vào đúng thư mục `docs/0x-...`, commit, rồi `git push -u origin docs/02-use-case`.
4. Mở Pull Request vào `main`, nhờ một bạn khác review rồi merge.
