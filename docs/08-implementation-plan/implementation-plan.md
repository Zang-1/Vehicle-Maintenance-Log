# 08 – Implementation Plan (Kế hoạch triển khai)

**Người phụ trách:** Kiều Bảo Giang · **Phiên bản:** 2.0 (áp dụng Final Project Brief và Lab 1 → Lab 5)
**Đầu vào:** [01 Requirements](../01-requirements/requirements.md) · [04 Database](../04-database/erd.md) · [07 Architecture](../07-architecture/)

> **Repo code chính thức: [noway165/team01](https://github.com/noway165/team01).** Đây là repo nhóm đã dùng cho Lab 1–4, và Brief chỉ chấm những gì có trong repo nhóm. Repo này (`Zang-1/Vehicle-Maintenance-Log`) chứa tài liệu thiết kế. Khi code, copy các file cần dùng (ví dụ `docs/04-database/*.sql` → `team01/db/`) sang `team01` bằng Pull Request.

## 1. Các lab được áp dụng vào đồ án

Brief chấm **pipeline nền tảng**. Mỗi lab là một mảnh của pipeline đó:

| Lab / Tuần | Đã làm trong lab | Áp dụng vào đồ án | Trạng thái (22/10/2026) |
|---|---|---|---|
| **Lab 1** – Git/GitHub (W1) | Danh tính Git, SSH key, branch → commit → PR → review → merge | Mọi thay đổi qua PR có người duyệt; mỗi thành viên có commit của mình để bảo vệ cá nhân | ✅ Đã có quy trình (PR #1 → #27) |
| **Week 2 Practice** – Collaboration | Repo nhóm, collaborator, `.gitignore`, `.env.example`, branch protection | `main` được bảo vệ: bắt buộc PR + 1 review + check `check` xanh | ✅ |
| **Lab 2** – Dockerfile (W3) | `python:*-slim`, `.dockerignore`, sắp xếp layer cache, `podman run -p` | Dockerfile của app; phần "Dockerfile explained" của report | ✅ · ⚠️ Python 3.14 trong Dockerfile khác 3.12 trong CI |
| **Week 4** – Compose | `web` + `db` (`postgres:16-alpine`), healthcheck, volume, host `db` | `podman compose up --build` dựng cả stack từ clean clone (5 điểm demo) | ✅ · cần thay `db/schema.sql` bằng schema của đề tài |
| **Lab 3** – Render (W5) | Đọc `PORT`, `/health` không chạm DB, biến môi trường trên Render, đọc log, rollback | URL HTTPS công khai (6 điểm demo) | ✅ `team01-1lr2.onrender.com` |
| **Lab 4** – GitHub Actions (W6) | Job `check` (compileall, ruff, pytest), branch protection, job `deploy` gọi `RENDER_DEPLOY_HOOK` khi push vào `main` | CI xanh trên PR (5 điểm), merge là tự deploy (5 điểm) | ✅ · ⚠️ bản 0.3.1 chưa lên URL; nghi deploy hook trỏ sai service · ⚠️ chưa có bước **build image** mà Brief yêu cầu |
| **Week 7** – Supabase | `schema.sql`/`seed.sql` chạy lại được, RLS, transaction pooler `6543`, connection pool, pause/restore | Managed PostgreSQL gắn bằng `DATABASE_URL`; mục "Database" của report | ⏳ Nhánh `week7-schema`, `week7-pool` đang chờ PR |
| **Lab 5** – AI API (W8) | Gemini API key, gọi từ server, xử lý lỗi, mock trong test | Tính năng chẩn đoán triệu chứng `/diagnose` | ⏳ Đang là placeholder |
| **Week 9** – Config & security | Audit secret | Mục "Secret and configuration management" của report; demo `git grep` không ra key (4 điểm) | ⏳ |

## 2. Công nghệ

Dựa trên starter của môn và những gì đã làm trong lab. Lâm chốt chính thức ở tài liệu 07.

| Thành phần | Công nghệ | Chọn thay cho (ghi vào report, mục Platform selection) |
|---|---|---|
| Backend | **FastAPI** (Python 3.12), Pydantic | Starter của môn; Flask/Django: nặng hơn, không có sẵn `/docs` |
| Giao diện | **Jinja2 templates** + CSS + một ít JavaScript (`fetch`) do chính FastAPI phục vụ | React/Vue: phải build và deploy thêm một service, vượt phạm vi Brief |
| Database | **PostgreSQL 16**: Compose (local) / **Supabase** (cloud), thư viện `psycopg` + `psycopg_pool` | Neon (cũng free, nhưng lab dùng Supabase); MySQL (Brief yêu cầu PostgreSQL) |
| Container | **Podman** + Dockerfile, **Compose** | Docker Desktop (cần license cho tổ chức lớn; Podman miễn phí, không cần daemon) |
| Cloud | **Render** Web Service (Docker, Free) | Railway, Fly.io (gói miễn phí bị giới hạn hoặc phải thêm phương thức thanh toán; kiểm tra lại điều khoản hiện tại khi viết report) |
| CI/CD | **GitHub Actions** + Render Deploy Hook | Render Auto-Deploy (không có cổng chặn khi test đỏ) |
| AI | **Google Gemini API** (Google AI Studio, free tier, không cần billing), gọi từ server bằng `google-genai` hoặc `httpx` | OpenAI (không còn free tier); gọi AI từ trình duyệt (lộ key) |
| Kiểm thử | pytest + FastAPI `TestClient`, ruff | |

**Cái giá của lựa chọn** (report yêu cầu nêu): Render free sleep sau ~15 phút nên lần mở đầu chậm và không chạy được tác vụ hẹn giờ; Supabase free pause sau 7 ngày không hoạt động; Gemini free tier có rate limit nên lúc demo có thể gặp 429.

## 3. Kiến trúc triển khai

Sơ đồ này phải **khớp với những gì thật sự được deploy** (Brief trừ điểm nếu không khớp). Lâm vẽ bản chính thức ở tài liệu 07.

```mermaid
flowchart LR
    U["Trình duyệt<br/>(máy tính / điện thoại)"] -- HTTPS --> R
    subgraph Render["Render (Free, Docker)"]
        R["Container web<br/>FastAPI + Jinja2<br/>uvicorn :$PORT"]
    end
    R -- "DATABASE_URL<br/>pooler :6543" --> S[("Supabase<br/>PostgreSQL 16")]
    R -- "GEMINI_API_KEY<br/>HTTPS" --> G["Google Gemini API"]
    Dev["Lập trình viên"] -- "git push nhánh → PR" --> GH["GitHub<br/>noway165/team01"]
    GH -- "pull_request / push main" --> GA["GitHub Actions<br/>check: ruff · pytest · build image"]
    GA -- "deploy: curl RENDER_DEPLOY_HOOK<br/>(chỉ khi push vào main)" --> Render
```

Local (Compose) khác cloud ở chỗ: database là container `db` trong cùng mạng Compose (host `db`, không có pooler), web publish ở `127.0.0.1:3000`, biến môi trường đọc từ `.env`.

## 4. Cấu trúc mã nguồn trong `team01`

```
team01/
├── .github/workflows/ci-cd.yml   # Lab 4
├── Dockerfile · .dockerignore    # Lab 2
├── compose.yml                   # Week 4
├── .env.example                  # mọi biến môi trường, không có giá trị bí mật
├── db/
│   ├── schema.sql                # từ docs/04-database (Week 7)
│   └── seed.sql
├── app/
│   ├── main.py                   # tạo app, lifespan mở/đóng pool, /, /health, /health/db, gắn router
│   ├── db.py                     # ConnectionPool (nhánh week7-pool)
│   ├── routers/
│   │   ├── vehicles.py           # /api/vehicles
│   │   ├── records.py            # /api/records, /api/vehicles/{id}/records
│   │   ├── service_types.py      # /api/service-types
│   │   ├── reminders.py          # /api/reminders
│   │   ├── stats.py              # /api/stats/...
│   │   ├── diagnose.py           # /diagnose, /api/diagnoses
│   │   └── pages.py              # các trang HTML (Jinja2)
│   ├── services/
│   │   └── ai.py                 # gọi Gemini, ánh xạ lỗi → NO_KEY / RATE_LIMITED / TIMEOUT / UPSTREAM_ERROR
│   ├── templates/                # base.html + từng màn hình S01 → S11
│   └── static/                   # style.css (theo Figma), app.js
└── tests/                        # pytest, chạy trong CI; mock Gemini, không cần DB thật
```

Mỗi router chỉ làm 3 việc: kiểm tra input (Pydantic) → chạy SQL tham số hóa (mẫu ở `sample-queries.sql`) → trả JSON. Trang HTML gọi các API này bằng `fetch`. Nhờ vậy cùng một API vừa được test bằng `TestClient`, vừa xem được ở `/docs`.

## 5. Chia module và phân công lập trình

Mỗi người làm trọn module của mình từ API, template đến test, để tự trả lời được câu hỏi bảo vệ cá nhân về commit của mình.

| Module | FR | Màn hình | Người làm | Việc chính |
|---|---|---|---|---|
| **M1. Database** | – | – | **Giang** | Merge `week7-schema` và `week7-pool`; thay `db/schema.sql`, `db/seed.sql` bằng bản của đề tài; `/health/db` đếm `vehicles`; chạy SQL trên Supabase; đổi `DATABASE_URL` trên Render |
| **M2. Xe** | FR-01 → FR-05 | S02, S03, S04 (tab Thông tin) | **Lâm** | Thay dict trong RAM bằng bảng `vehicles` |
| **M3. Lần bảo dưỡng** | FR-06 → FR-10 | S04 (tab Lịch sử), S05, S06 | **Lâm** | Ghi nhận trong 1 transaction (record + items + nâng ODO) |
| **M4. Loại dịch vụ** | FR-11, FR-12 | S09 | **Khoa** | |
| **M5. Nhắc lịch** | FR-13 → FR-15 | S04 (tab Nhắc lịch), S07 | **Giang** | Đọc trạng thái từ `v_reminder_status` |
| **M6. Giao diện chung, Dashboard, Thống kê** | FR-16, FR-17 | S01, S08 + `base.html` | **Khoa** | Layout, CSS theo Figma, điều hướng, biểu đồ |
| **M7. Chẩn đoán AI** (Lab 5) | FR-18 → FR-22 | S10, S11 | **Giang** | `services/ai.py`, xử lý lỗi theo BR-10, lưu `diagnoses`, mock trong test |
| **P1. CI/CD + Render** | PR-01, PR-04 | – | **Lâm** (chủ repo, chủ service) | Thêm bước build image vào CI; kiểm tra `RENDER_DEPLOY_HOOK` trỏ đúng service; giữ một service chính thức |
| **P2. Dockerfile + Compose** | PR-02, PR-03 | – | **Khoa** | Thống nhất Python 3.12 (Dockerfile = CI); `exec uvicorn`; thử clean clone trên máy khác |

### Hợp đồng giữa các module

| Bên cung cấp | Bên dùng | Nội dung |
|---|---|---|
| M1 (Giang) | Tất cả | `app/db.py` có `pool`; dùng `with pool.connection() as conn:` |
| M2 (Lâm) | M3, M5, M7 | `GET /api/vehicles/{id}` trả 404 nếu không có xe |
| M4 (Khoa) | M3, M5, M7 | `GET /api/service-types?active=true` |
| M6 (Khoa) | Tất cả | `templates/base.html` (thanh điều hướng, vùng thông báo lỗi), `static/style.css`, hàm `showError(message)` trong `app.js` |

### Danh sách API

| Phương thức & URL | Mô tả | Module |
|---|---|---|
| `GET /` · `GET /health` · `GET /health/db` | Thông tin app · sống (không chạm DB) · DB ok/503 | M1 |
| `GET/POST /api/vehicles` · `GET/PUT/DELETE /api/vehicles/{id}` | CRUD xe (DELETE trả 409 nếu xe đã có lịch sử) | M2 |
| `PATCH /api/vehicles/{id}/archive` | Lưu trữ xe | M2 |
| `GET/POST /api/vehicles/{id}/records` · `GET/PUT/DELETE /api/records/{id}` | Lịch sử, ghi nhận, chi tiết, sửa, xóa | M3 |
| `GET /api/vehicles/{id}/records.csv` | Xuất CSV | M3 |
| `GET/POST /api/service-types` · `PUT /api/service-types/{id}` | Danh mục | M4 |
| `GET /api/reminders?vehicle_id=&status=` · `POST /api/reminders` · `PUT/DELETE /api/reminders/{id}` | Nhắc lịch kèm trạng thái | M5 |
| `GET /api/stats/dashboard` · `GET /api/stats/costs?group_by=month\|vehicle\|service_type&from=&to=` | Dashboard, thống kê | M6 |
| `POST /diagnose` · `GET /api/diagnoses` | Chẩn đoán AI (giữ đúng URL của starter), lịch sử | M7 |

## 6. Tính năng AI – thiết kế chi tiết (Lab 5)

| Câu hỏi của Brief | Thiết kế |
|---|---|
| **Gọi ở đâu?** | Chỉ ở server, trong `app/services/ai.py`, được `POST /diagnose` gọi. Trình duyệt không bao giờ thấy key hay gọi thẳng Gemini |
| **Bảo mật key?** | `GEMINI_API_KEY` đọc bằng `os.getenv`. Local: `.env` (đã gitignore). Production: Render → Environment. CI: không cần key, vì test mock hàm gọi AI. Đổi tên `AI_API_KEY` hiện có trong `.env.example` thành `GEMINI_API_KEY` cho khớp slide |
| **Thiếu key thì sao?** | App **vẫn khởi động** (khác `DATABASE_URL`, biến bắt buộc). `/diagnose` trả 503 `NO_KEY`; các trang khác không bị ảnh hưởng |
| **Rate limit?** | Free tier giới hạn số request mỗi phút và mỗi ngày (xem trang *Rate limits* của Google AI Studio cho model đang dùng). Gặp 429 thì **không tự gọi lại**: trả ngay 429 kèm thông báo. Nút "Chẩn đoán" bị khóa trong lúc chờ để tránh bấm liên tục |
| **Timeout?** | 20 giây; quá thời gian thì trả 504 |
| **Người dùng thấy gì khi lỗi?** | Thông báo theo bảng BR-10 (tài liệu 01) hiện ngay trên trang; ô triệu chứng giữ nguyên nội dung; các phần khác của trang vẫn dùng được |
| **Prompt** | Gửi kèm loại xe, hãng, dòng xe, ODO (nếu chọn xe) và danh sách tên loại dịch vụ đang dùng; yêu cầu trả về JSON `{suggestion, urgency_level, service_type}`. Server kiểm tra JSON bằng Pydantic; sai định dạng thì xử lý như `UPSTREAM_ERROR` |
| **Bằng chứng cho report** | Bảng `diagnoses` lưu mọi lần gọi kèm `error_code`; log server ghi chi tiết lỗi (không ghi key) |

## 7. Thứ tự thực hiện theo mốc của Brief

Hôm nay là **22/10/2026 (Week 7)**. Brief chấm tại **Session 20**.

| Tuần (mốc Brief) | Giang | Lâm | Khoa | Kết quả phải có cuối tuần |
|---|---|---|---|---|
| **W7** (Session 14 – Cloud DB) | Push và mở PR cho `week7-schema`, `week7-pool`; tạo Supabase cùng region với Render; PR **M1** thay schema của đề tài | Tài liệu **02 Use Case**, **03 Activity**; kiểm tra `RENDER_DEPLOY_HOOK` | Tài liệu **05 Wireframe**; PR **P2** (Python 3.12, `exec`) | `/health/db` trên URL live → ok với Supabase |
| **W8** (Session 16 – AI) | **M7** chẩn đoán AI chạy trên URL live, xử lý đủ lỗi | Tài liệu **07**; **M2** xe; **P1** thêm bước build image vào CI | Tài liệu **06 Figma**; **M6** `base.html` + CSS | AI chạy trên URL live, lỗi được xử lý |
| **W9** (Session 18 – Config & security) | **M5** nhắc lịch; audit secret; viết mục report của mình | **M3** lần bảo dưỡng | **M4** loại dịch vụ; **M6** Dashboard + thống kê | Đủ chức năng Must; audit secret xong; góp ý peer review thành Issues; **bản nháp report đủ 8 mục** |
| **W10** (Session 19) | Sửa lỗi, hoàn thiện report | Sửa lỗi; chuẩn bị nhánh "cố tình đỏ" cho demo | Thử **clean clone trên máy khác**; slide | Demo đã tập có bấm giờ; **nộp report PDF** |
| **Session 20** | Demo + bảo vệ | | | |

Chức năng **Should/Could** (FR-05, FR-10, FR-12, FR-17, FR-21, FR-22) chỉ làm khi các chức năng Must và 5 tiêu chí demo đã xong.

## 8. Kế hoạch kiểm thử

### 8.1. Các mức kiểm thử

| Mức | Phạm vi | Công cụ | Chạy ở đâu |
|---|---|---|---|
| Lint + compile | Toàn bộ code Python | `ruff check .`, `python -m compileall` | CI, mỗi PR |
| Unit / API test | Route trả đúng mã khi input sai (422), khi không tìm thấy (404); `/health` không chạm DB; `services/ai.py` ánh xạ đúng 429/timeout/thiếu key (mock) | pytest + `TestClient` + `monkeypatch` | CI, mỗi PR |
| Kiểm thử database | `schema.sql` + `seed.sql` chạy 2 lần không lỗi; ràng buộc chặn dữ liệu sai; `v_reminder_status` tính đúng | `psql` trên `postgres:16-alpine` (Compose) | Local trước khi mở PR sửa `db/` |
| Kiểm thử hệ thống | Kịch bản đầu-cuối trên URL live, theo bảng 8.2 | Thủ công, ghi kết quả vào GitHub Issues | W9–W10, kiểm thử chéo (người này test module của người kia) |
| Kiểm thử nền tảng | 5 tiêu chí demo + các tình huống lỗi | Theo bảng 8.3 | W10, trên máy chưa từng có project |

Nguyên tắc từ Lab 4 và Lab 5: test trong CI **không cần database thật và không gọi Gemini thật**. `conftest.py` đặt `DATABASE_URL` giả, còn hàm gọi AI được thay bằng mock. Nhờ vậy pipeline xanh mà không cần secret.

### 8.2. Test case chức năng

| Mã | FR / BR | Kịch bản | Kết quả mong đợi |
|---|---|---|---|
| TC-01 | FR-01, BR-01 | Thêm xe trùng biển số `51H-678.90` | 409, báo trùng biển số |
| TC-02 | FR-04, BR-02 | Cập nhật ODO 12.000 cho xe đang 12.850 | 422, ODO giữ nguyên |
| TC-03 | FR-05, BR-09 | Xóa xe đã có lịch sử | 409, gợi ý "Lưu trữ" |
| TC-04 | FR-06, BR-04 | Ghi nhận bảo dưỡng không có hạng mục | 422 |
| TC-05 | FR-06, BR-03 | Ngày bảo dưỡng là ngày mai | 422 |
| TC-06 | FR-06, BR-05 | Hạng mục 4 × 210.000 và 1 × 150.000 | Tổng chi phí 990.000 |
| TC-07 | FR-06, BR-02 | Ghi nhận ODO 13.000 cho xe đang 12.850 | ODO xe thành 13.000 |
| TC-08 | FR-15, BR-07 | Ghi nhận thay nhớt (nhắc lịch 1.500 km / 2 tháng) ngày 22/10/2026, ODO 13.000 | Nhắc lịch chuyển sang "Còn hạn", mốc 22/12/2026 hoặc 14.500 km |
| TC-09 | FR-14, BR-08 | Còn 200 km, còn 30 ngày, ngưỡng 300 km / 7 ngày | "Sắp đến hạn" |
| TC-10 | FR-13, BR-06 | Tạo nhắc lịch trùng loại dịch vụ trên cùng xe | 409 |
| TC-11 | FR-17 | Chi phí theo tháng năm 2026 với dữ liệu `seed.sql` | 02: 1.960.000 · 03: 255.000 · 06: 135.000 · 07: 225.000 · 08: 1.305.000 |
| TC-12 | FR-19 | Chẩn đoán "phanh kêu rít khi bóp mạnh" (AI chạy được) | 200, có gợi ý + mức khẩn cấp; 1 dòng `diagnoses` status OK |
| TC-13 | FR-20 | Mock Gemini trả 429 | 429, thông báo "hết lượt…"; dòng `diagnoses` với `RATE_LIMITED`; ô nhập giữ nguyên |
| TC-14 | FR-20 | Không đặt `GEMINI_API_KEY` | App vẫn khởi động; `/diagnose` → 503 `NO_KEY`; `/api/vehicles` vẫn 200 |
| TC-15 | FR-20 | Mock Gemini treo quá 20 giây | 504 |
| TC-16 | FR-18 | Triệu chứng 5 ký tự | 422, không gọi AI |

### 8.3. Test case nền tảng (khớp tiêu chí demo của Brief)

| Mã | Tiêu chí | Cách kiểm tra | Kết quả mong đợi |
|---|---|---|---|
| PT-01 | HTTPS công khai (6đ) | Mở URL Render trên điện thoại dùng 4G | Trang tải được, có ổ khóa HTTPS |
| PT-02 | Compose 1 lệnh (5đ) | Máy chưa từng có project: `git clone` → `cp .env.example .env` → đặt `DB_PASSWORD` → `podman compose up --build` | `http://localhost:3000/health/db` → ok, có dữ liệu mẫu |
| PT-03 | CI chặn PR hỏng (5đ) | PR cố tình làm test đỏ | Check `check` đỏ, nút merge bị khóa |
| PT-04 | Merge là tự deploy (5đ) | Sửa test, tăng `APP_VERSION`, merge | Actions: `check` → `deploy` xanh; Render Events có commit hash mới; `/` hiện version mới |
| PT-05 | Không có secret trong repo (4đ) | `git grep -n -i -E "pooler.supabase\|AIza\|api.render.com/deploy"` và `git log -p` cho các từ đó | Không ra kết quả |
| PT-06 | Supabase pause | Pause project → gọi `/health/db` và `/health` → Restore | 503 rồi tự ok lại, `/health` luôn 200, không redeploy |
| PT-07 | Render ngủ | Không truy cập 15 phút rồi mở lại | Lần đầu chậm (~1 phút) nhưng tải được. Lúc demo: mở URL trước 5 phút |

### 8.4. Quy trình xử lý lỗi

1. Người phát hiện tạo GitHub Issue, gắn nhãn `bug`, ghi bước tái hiện, kết quả mong đợi/thực tế, mã test case. **Ảnh chụp không được có key hay connection string.**
2. Giao cho người phụ trách module ở mục 5.
3. Sửa trên nhánh riêng; trong PR ghi `Fixes #<số>`; người phát hiện kiểm tra lại. Brief tính điểm "closed issues" vào phần làm việc nhóm.

## 9. Quy trình Git (Lab 1, Week 2, Lab 4)

- `main` được bảo vệ: **Require a pull request** (1 approving review) và **Require status checks** (`check`). Không ai commit thẳng vào `main`.
- Tên nhánh: `feature/<module>-<mô-tả>` (ví dụ `feature/m2-vehicles-db`), `fix/<mô-tả>`, `docs/<bước>`.
- Commit message: câu mệnh lệnh tiếng Anh, < 60 ký tự, giống lịch sử repo. Ví dụ: `Add vehicles table and CRUD endpoints`.
- Review phải có nhận xét thật, không chỉ bấm Approve. Merge xong thì **Delete branch**.
- **Mỗi người dùng đúng một danh tính Git** (tên + email) trên mọi máy, để bảng đóng góp khớp với lịch sử commit:

| Thành viên | `user.name` | `user.email` | GitHub |
|---|---|---|---|
| Kiều Bảo Giang | `Kieu Bao Giang` | giangbao041@gmail.com | @Zang-1 |
| Tăng Thoại Lâm | (Lâm chốt) | lam.2474802010210@vanlanguni.vn | @noway165 |
| Nguyễn Nam Khoa | (Khoa chốt) | chọn **một** trong 2 email đang dùng | @namkhoa306 |

## 10. Quản lý cấu hình và secret

| Biến | Bí mật? | Local | Render | GitHub Actions |
|---|---|---|---|---|
| `APP_NAME`, `APP_ENV` | Không | `.env` | Environment (`APP_ENV=production`) | Không cần |
| `PORT` | Không | Mặc định 8000 | **Render tự đặt, không ghi đè** | Không cần |
| `DB_PASSWORD` | Có | `.env` (chỉ chữ + số) | Không dùng | Không cần |
| `DATABASE_URL` | **Có** | `compose.yml` ghép (host `db`) | Environment = Supabase transaction pooler `:6543` | Giá trị giả trong `conftest.py` |
| `GEMINI_API_KEY` | **Có** | `.env` | Environment | Không cần (test dùng mock) |
| `RENDER_DEPLOY_HOOK` | **Có** | Không có | Không có | Repository secret |

`.env` và `.env.*` nằm trong `.gitignore` và `.dockerignore`. `.env.example` liệt kê đủ tên biến, không có giá trị.

**Nếu lộ key** (trả lời câu hỏi của report):
1. Thu hồi ngay: tạo key Gemini mới / đổi mật khẩu DB Supabase / tạo lại deploy hook trên Render.
2. Cập nhật giá trị mới ở Render Environment hoặc GitHub Secrets, rồi redeploy.
3. Xóa key khỏi lịch sử Git nếu đã commit (`git filter-repo`), vì xóa ở commit sau thì key vẫn còn trong lịch sử. Báo nhóm và giảng viên.

## 11. Phân công report và thuyết trình

**Report** (PDF, tối đa 12 trang, 8 mục bắt buộc):

| Mục | Người viết |
|---|---|
| 1. Platform selection rationale | Lâm |
| 2. System architecture (sơ đồ khớp deployment) | Lâm |
| 3. Dockerfile and Compose explained | Khoa |
| 4. CI/CD pipeline walkthrough | Lâm |
| 5. Database schema and integration | Giang |
| 6. AI API integration | Giang |
| 7. Secret and configuration management | Giang + Khoa |
| 8. Individual contribution table (khớp lịch sử commit, cả nhóm ký) | Cả nhóm (Giang tổng hợp) |

**Thuyết trình 10 phút** (mỗi người giữ ít nhất một khối, theo gợi ý của Brief):

| Thời lượng | Nội dung | Người trình bày |
|---|---|---|
| 1 phút | Ứng dụng làm gì, cho ai | Khoa |
| 2 phút | Kiến trúc: các thành phần, giao tiếp ra sao | Lâm |
| 4 phút | Demo trực tiếp theo thứ tự đã tập (mục 12) | Giang dẫn; Lâm làm phần CI/deploy; Khoa làm phần clean clone |
| 2 phút | Một lỗi đã gặp và cách sửa (ví dụ: deploy hook trỏ sai service, Supabase pause) | Lâm |
| 1 phút | Nếu làm lại sẽ làm khác gì | Khoa |

## 12. Kịch bản demo (theo Brief)

1. **Đánh thức service:** mở URL live trước 5 phút.
2. **Kiểm tra DB:** nếu Supabase đang pause thì Restore và chạy một truy vấn.
3. **Clean clone:** trên máy chưa từng có project, clone, một lệnh, stack chạy.
4. **Cổng chặn:** mở PR cố tình hỏng, check đỏ chặn merge.
5. **Deploy:** sửa, merge, thay đổi lên URL live.
6. **Repo sạch:** chạy `git grep` tìm key trước lớp, không ra gì.
7. **AI:** chẩn đoán một triệu chứng trên URL live. Nếu gặp 429 thì đó chính là cơ hội cho thấy thông báo lỗi thân thiện.

## 13. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Deploy hook trỏ sai service (bản 0.3.1 không lên URL dù job deploy xanh) | Lâm kiểm tra Render → Events trong W7; tạo lại hook của service chính thức, cập nhật secret |
| Python 3.14 (Dockerfile) khác 3.12 (CI): CI xanh nhưng image lỗi | Khoa thống nhất 3.12 (PR P2) và thêm bước build image vào CI (P1) |
| Clean clone chỉ chạy trên một máy | Tập trên máy khác từ W10; README ghi đủ bước |
| Supabase pause khi demo | Restore trước giờ demo; app đã tự phục hồi (PT-06) |
| Gemini 429 lúc demo | Thông báo thân thiện là một phần của demo; đã có dòng `RATE_LIMITED` mẫu trong `seed.sql` |
| Lịch sử commit lệch nhau giữa các thành viên | Mỗi người làm module riêng (mục 5); kiểm tra `git shortlog -sne` mỗi tuần |
| Lộ secret qua ảnh chụp, group chat | Không dán connection string ở đâu ngoài Render/GitHub Secrets; audit ở W9 |
