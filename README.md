# Vehicle Maintenance Log

Ứng dụng web giúp chủ xe máy, ô tô **lưu lịch sử bảo dưỡng**, **biết hạng mục nào sắp đến hạn** (theo ngày hoặc số km), **theo dõi chi phí**, và **chẩn đoán triệu chứng bằng AI** (Google Gemini).

Đồ án cuối kỳ môn **72ITDS30103 – Software Development Platforms**, VLU, HK 261.

| | |
|---|---|
| **Công nghệ** | FastAPI · Jinja2 · PostgreSQL 16 (Compose / Supabase) · Podman · Render · GitHub Actions · Gemini API |
| **URL live** | (cập nhật khi deploy lên Render) |

## Thành viên và phân công

| Thành viên | GitHub | Tài liệu | Code |
|---|---|---|---|
| **Kiều Bảo Giang** (nhóm trưởng) | @Zang-1 | 01 · 04 · 08 | Database (Supabase) · Nhắc lịch · Chẩn đoán AI |
| **Tăng Thoại Lâm** | @noway165 | 02 · 03 · 07 | Xe · Lần bảo dưỡng · CI/CD + Render |
| **Nguyễn Nam Khoa** | @namkhoa306 | 05 · 06 | Loại dịch vụ · Giao diện, Dashboard · Dockerfile + Compose |

Chi tiết (report, thuyết trình, lịch theo tuần): [docs/PHAN-CONG.md](docs/PHAN-CONG.md).

## Tài liệu thiết kế

| # | Bước | Người làm | Trạng thái |
|---|---|---|---|
| 01 | [Requirements](docs/01-requirements/requirements.md) | Giang | ✅ Xong |
| 02 | [Use Case Diagram](docs/02-use-case/) | Lâm | ✅ Xong (chờ review) |
| 03 | [Activity Diagram](docs/03-activity/) | Lâm | ✅ Xong (chờ review) |
| 04 | [ERD & Database Design](docs/04-database/erd.md) | Giang | ✅ Xong (đã chạy thử trên PostgreSQL 16) |
| 05 | [Wireframe](docs/05-wireframe/) | Khoa | ⏳ |
| 06 | [UI Design trên Figma](docs/06-ui-design/) | Khoa | ⏳ |
| 07 | [Architecture & Class Diagram](docs/07-architecture/) | Lâm | ✅ Xong (chờ review) |
| 08 | [Implementation Plan](docs/08-implementation-plan/implementation-plan.md) | Giang | ✅ Xong (cập nhật lại sau khi có 07) |

## Cách đóng góp

1. Clone: `git clone https://github.com/Zang-1/Vehicle-Maintenance-Log.git`
2. Tạo nhánh cho phần của mình, ví dụ `git checkout -b docs/02-use-case`.
3. Commit, rồi `git push -u origin docs/02-use-case`.
4. Mở Pull Request vào `main`, nhờ một bạn khác review rồi merge.
