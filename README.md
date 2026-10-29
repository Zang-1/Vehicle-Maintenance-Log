# Vehicle Maintenance Log

Ứng dụng web giúp chủ xe máy, ô tô **lưu lịch sử bảo dưỡng**, **biết hạng mục nào sắp đến hạn** (theo ngày hoặc số km), **theo dõi chi phí**, và **chẩn đoán triệu chứng bằng AI** (Google Gemini).

Đồ án cuối kỳ môn **72ITDS30103 – Software Development Platforms**, VLU, HK 261.

| | |
|---|---|
| **Công nghệ** | FastAPI · Jinja2 · PostgreSQL 16 (Compose / Supabase) · Podman · Render · GitHub Actions · Gemini API |
| **URL live** | https://vehicle-maintenance-log.onrender.com/ |

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
| 02 | [Use Case Diagram](docs/02-use-case/) | Lâm | ✅ Xong |
| 03 | [Activity Diagram](docs/03-activity/) | Lâm | ✅ Xong |
| 04 | [ERD & Database Design](docs/04-database/erd.md) | Giang | ✅ Xong (đã chạy thử trên PostgreSQL 16) |
| 05 | [Wireframe](docs/05-wireframe/) | Khoa | ✅ Xong |
| 06 | [UI Design trên Figma](docs/06-ui-design/) | Khoa | ✅ Xong |
| 07 | [Architecture & Class Diagram](docs/07-architecture/) | Lâm | ✅ Xong |
| 08 | [Implementation Plan](docs/08-implementation-plan/implementation-plan.md) | Giang | ✅ Xong (đã cập nhật theo 07) |

## Lộ trình

| Phase | Thời gian | Kết quả |
|---|---|---|
| 1. Thiết kế | đến 25/10/2026 | 8 tài liệu thiết kế |
| 2. Chạy local | 23/10 – **26/10** | `podman compose up --build` từ clean clone; Dashboard, xe, lịch sử, nhắc lịch hiện trên `localhost:3000` |
| 3. Lên Render + Supabase | 27/10 – **29/10** | URL HTTPS công khai nối Supabase; merge vào `main` là tự deploy |
| 4. Hoàn thiện | 30/10 – 8/11 | AI chạy trên URL live, đủ chức năng, audit secret, bản nháp report |
| 5. Tập demo và nộp | 9/11 – Session 20 | Report PDF, demo đã tập trên máy khác |

Chi tiết theo ngày: mục 6 của [Implementation Plan](docs/08-implementation-plan/implementation-plan.md).

## Chạy code

### Cách chính: cả stack bằng một lệnh (Compose)

**Windows, nhanh nhất:** bấm đúp `chay-local.bat`. Script tự bật Podman, tạo `.env` (mật khẩu DB ngẫu nhiên) nếu chưa có, chạy `podman compose up --build -d`, chờ app sẵn sàng rồi mở http://localhost:3000. Bấm đúp `dung-local.bat` để dừng (dữ liệu vẫn giữ).

Hoặc chạy tay:

Cần Podman 4+ có compose provider (`podman compose version` phải in ra phiên bản). Trên Windows, Podman machine phải đang chạy (`podman machine start`). Chạy trong Git Bash:

```bash
git clone https://github.com/Zang-1/Vehicle-Maintenance-Log.git
cd Vehicle-Maintenance-Log
cp .env.example .env          # mở .env, đặt DB_PASSWORD (chỉ chữ và số), các dòng khác để nguyên
podman compose up --build
```

Chờ dòng `Uvicorn running on http://0.0.0.0:8000`, rồi mở **http://localhost:3000** để xem giao diện. Kiểm tra database: http://localhost:3000/health/db → `{"db":"ok","vehicles":3}`.

| Việc | Lệnh |
|---|---|
| Chạy nền | `podman compose up --build -d` |
| Trạng thái | `podman compose ps` |
| Xem log | `podman compose logs web` |
| Dừng (giữ dữ liệu) | `podman compose down` |
| Xóa dữ liệu, tạo lại từ `db/schema.sql` + `db/seed.sql` | `podman compose down -v` rồi `podman compose up --build` |

Chọn `DB_PASSWORD` trước lần chạy đầu và giữ nguyên: PostgreSQL lưu mật khẩu khi tạo volume, đổi về sau sẽ báo `password authentication failed` cho tới khi `down -v`. Không chạy `down -v` trước buổi demo.

**Nếu `podman compose` báo `failed to connect to the docker API at npipe:////./pipe/podman-machine-default`:** trên Windows, `podman machine start` lúc đó có in dòng `win-sshproxy.exe failed to start`, nên compose không có cổng Docker API. Cách vòng: mở API của Podman qua TCP, chỉ trong máy mình (`127.0.0.1`), rồi trỏ compose vào đó:

```bash
podman machine ssh "nohup podman system service --time=0 tcp://127.0.0.1:23750 >/tmp/svc.log 2>&1 &"
export DOCKER_HOST=tcp://localhost:23750
podman compose up --build
```

`DOCKER_HOST` chỉ có hiệu lực trong cửa sổ Git Bash đó. Máy không bị lỗi này thì bỏ qua bước trên.

| Endpoint | Trả về |
|---|---|
| `GET /` | Giao diện: Dashboard (S01). Các mục menu khác hiện trang "đang xây dựng" cho tới khi module tương ứng xong |
| `GET /api/info` | Tên app, phiên bản, môi trường (đối chiếu sau mỗi lần deploy) |
| `GET /api/stats/dashboard` | Số liệu cho Dashboard |
| `GET /chan-doan` | Giao diện Chẩn đoán AI (S10) |
| `POST /diagnose` | `{"symptom_text": "..."}` (10–1000 ký tự) → `{"suggestion": "..."}` từ Gemini. Thiếu/sai `GEMINI_API_KEY` hoặc AI lỗi → 503 `AI_UNAVAILABLE` kèm thông báo thân thiện, lý do chỉ ghi vào log (`ai failed: ...`) |
| `GET /health` | `{"status":"ok"}`, **không** chạm database (Render health check) |
| `GET /health/db` | `{"db":"ok","vehicles":N}`; mất database thì 503 `{"db":"error"}` sau tối đa 5 giây |
| `GET /docs` | Tài liệu API tự sinh của FastAPI |

### Chạy image với Supabase (giống trên Render)

```bash
podman build -t vml:dev .
podman run --rm -p 3000:8000 --env-file .env.cloud vml:dev     # .env.cloud: một dòng DATABASE_URL=<Supabase transaction pooler>
```

File `.env.cloud` nằm trong `.gitignore` và `.dockerignore`, không bao giờ vào repo hay image.

### Chạy test (giống job `check` của CI, không cần database)

Cần Python 3.12:

```bash
python -m venv .venv
source .venv/Scripts/activate        # macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && pytest -q
```

## Cách đóng góp

1. Clone: `git clone https://github.com/Zang-1/Vehicle-Maintenance-Log.git`
2. Tạo nhánh cho phần của mình, ví dụ `git checkout -b docs/02-use-case`.
3. Commit, rồi `git push -u origin docs/02-use-case`.
4. Mở Pull Request vào `main`, nhờ một bạn khác review rồi merge.
