# 07 – Architecture & Class Diagram

**Người phụ trách:** Tăng Thoại Lâm · **Phiên bản:** 2.0 · **Đầu vào:** [02 Use Case](../02-use-case/), [04 Database](../04-database/erd.md), [08 Implementation Plan](../08-implementation-plan/implementation-plan.md) (mục 1–5)

Tài liệu chốt công nghệ, vẽ sơ đồ triển khai **khớp với những gì thật sự được deploy**, kiến trúc 3 tầng và class diagram của ứng dụng. Tên file, tên lớp, tên hàm ở đây là tên sẽ dùng trong code (cấu trúc repo ở mục 3 tài liệu 08). Sơ đồ ở mục 2 và 3 là bản dùng cho mục 2 "System architecture" của report; nếu cách deploy thay đổi thì phải sửa sơ đồ trong cùng PR.

## 1. Công nghệ chốt

Giữ nguyên lựa chọn ở mục 1 tài liệu 08 và chốt các điểm còn để mở:

| Thành phần | Chốt | Phiên bản / gói | Ghi chú |
|---|---|---|---|
| Ngôn ngữ | Python | 3.12 (cùng phiên bản ở Dockerfile và CI) | |
| Backend | FastAPI + Pydantic v2, chạy bằng uvicorn | `fastapi`, `uvicorn[standard]`, `pydantic` | Có sẵn trang `/docs` để thử API |
| Giao diện | Jinja2 templates + CSS + JavaScript `fetch` | `jinja2`; FastAPI phục vụ cả `templates/` và `static/` | Một service duy nhất, không có bước build frontend |
| Truy cập DB | psycopg 3 + connection pool | `psycopg[binary]`, `psycopg_pool` | SQL viết tay, tham số hóa `%(ten)s` (NFR-02) |
| Gọi AI | **`httpx`** gọi REST API của Gemini | `httpx` | **Chốt `httpx` thay cho `google-genai`**: đặt timeout 20 giây trực tiếp, đọc được mã HTTP gốc (429, 5xx) để ánh xạ đúng bảng BR-10, dễ mock trong test, ít phụ thuộc |
| Model AI | Gemini Flash của free tier | Tên model là hằng `GEMINI_MODEL` trong `app/services/ai.py`, lưu vào `diagnoses.model` | Kiểm tra lại tên model và rate limit trên Google AI Studio khi code M7 |
| Database | PostgreSQL 16 | `postgres:16-alpine` (local) · Supabase (cloud) | |
| Container | Podman + Dockerfile + Compose | Base image `python:3.12-slim` | |
| Cloud | Render Web Service, runtime Docker, gói Free | Auto-Deploy **tắt**, health check path `/health` | |
| CI/CD | GitHub Actions + Render Deploy Hook | Workflow `.github/workflows/ci-cd.yml`: job `check`, job `deploy` | |
| Kiểm thử | pytest + FastAPI `TestClient`, ruff | `pytest`, `ruff`, `httpx` (TestClient cần) | Không gọi Gemini thật, không cần DB thật (NFR-11) |

## 2. Sơ đồ triển khai – production

```mermaid
flowchart LR
    User["Trình duyệt<br/>máy tính / điện thoại 4G"]
    Dev["Lập trình viên"]

    subgraph GH["GitHub"]
        Repo["Repo Zang-1/<br/>Vehicle-Maintenance-Log<br/>main được bảo vệ"]
        GA["GitHub Actions · ci-cd.yml<br/>job check · job deploy<br/>secret RENDER_DEPLOY_HOOK"]
    end

    subgraph RD["Render (Free, runtime Docker)"]
        Edge["Render edge<br/>HTTPS *.onrender.com"]
        Web["Container web<br/>image build từ Dockerfile<br/>python:3.12-slim<br/>uvicorn app.main:app<br/>--host 0.0.0.0 --port $PORT"]
        Env[("Environment<br/>DATABASE_URL<br/>GEMINI_API_KEY<br/>APP_ENV=production")]
    end

    subgraph SB["Supabase (Free)"]
        Pool["Transaction pooler<br/>*.pooler.supabase.com:6543"]
        PG[("PostgreSQL 16<br/>6 bảng + 2 view<br/>RLS bật")]
    end

    Gemini["Google Gemini API<br/>generativelanguage.googleapis.com"]

    User -- "HTTPS 443" --> Edge --> Web
    Env -. "biến môi trường" .-> Web
    Web -- "DATABASE_URL · TLS · :6543<br/>psycopg_pool, max 5 kết nối" --> Pool --> PG
    Web -- "HTTPS · header x-goog-api-key<br/>timeout 20 giây" --> Gemini
    Dev -- "git push nhánh · mở PR" --> Repo
    Repo -- "pull_request · push main" --> GA
    GA -- "deploy hook<br/>(push main, check xanh)" --> Web
    Repo -. "Render kéo code, docker build" .-> Web

    classDef store fill:#fff4e5,stroke:#d97706,color:#7c2d12
    class Env,PG store
```

| Kết nối | Giao thức / cổng | Xác thực | Ghi chú |
|---|---|---|---|
| Trình duyệt → Render | HTTPS 443 | Không (không có đăng nhập) | Render cấp chứng chỉ TLS và chuyển request vào cổng `$PORT` của container (PR-01) |
| Container → Supabase | PostgreSQL qua TLS, **cổng 6543** (transaction pooler) | User/mật khẩu trong `DATABASE_URL` | Pooler không hỗ trợ prepared statement nên pool đặt `prepare_threshold=None` (tài liệu 04, mục 8) |
| Container → Gemini | HTTPS 443, REST `generateContent` | Key gửi trong **header** `x-goog-api-key`, không đặt trên URL để key không lọt vào log | Chỉ server gọi; trình duyệt không bao giờ thấy key (PR-06) |
| GitHub → Actions | Nội bộ GitHub | – | Sự kiện `pull_request` và `push` vào `main` |
| Actions → Render | HTTPS POST tới deploy hook | URL hook chính là bí mật (GitHub secret) | Chỉ job `deploy` chạy khi `check` xanh trên `main` (PR-04) |
| Render → GitHub | HTTPS | Render GitHub App | Render kéo code của commit mới nhất trên `main` rồi build `Dockerfile` |
| Render → container | HTTP `/health` | – | Health check không chạm DB, nên DB pause không làm Render coi service là chết (NFR-04) |

## 3. Sơ đồ triển khai – local (Compose)

```mermaid
flowchart LR
    User["Trình duyệt<br/>127.0.0.1:3000"]
    EnvFile[(".env<br/>DB_PASSWORD<br/>GEMINI_API_KEY (tùy chọn)")]

    subgraph CP["podman compose up --build"]
        Web["Service web<br/>build từ Dockerfile<br/>uvicorn :8000<br/>publish 127.0.0.1:3000 → 8000"]
        DB[("Service db<br/>postgres:16-alpine<br/>host db:5432<br/>healthcheck pg_isready")]
        Vol[("Volume dữ liệu<br/>của Postgres")]
        Init["db/schema.sql · db/seed.sql<br/>mount vào /docker-entrypoint-initdb.d<br/>(chạy ở lần khởi tạo đầu)"]
    end

    Gemini["Google Gemini API"]

    User -- HTTP --> Web
    EnvFile -. "biến môi trường" .-> Web
    EnvFile -. "DB_PASSWORD" .-> DB
    Web -- "DATABASE_URL ghép trong compose.yml<br/>host db, cổng 5432, không có pooler" --> DB
    DB --- Vol
    Init -.-> DB
    Web -. "chỉ khi .env có key" .-> Gemini
```

`web` khai báo `depends_on: db` với điều kiện `service_healthy`, nên app chỉ khởi động khi Postgres đã sẵn sàng.

**Local khác cloud ở đâu**

| Khía cạnh | Local (Compose) | Production (Render + Supabase) |
|---|---|---|
| Database | Container `db` trong cùng mạng Compose | Supabase managed PostgreSQL |
| Host trong `DATABASE_URL` | `db` (tên service, không phải `localhost`) | `*.pooler.supabase.com` |
| Cổng DB | 5432, kết nối thẳng, không pooler | 6543, transaction pooler |
| Tạo bảng, dữ liệu mẫu | Tự chạy `schema.sql` + `seed.sql` khi volume còn trống | Dán vào Supabase SQL Editor một lần (script chạy lại được) |
| Biến môi trường lấy từ | `.env` (đã gitignore) | Render → Environment |
| Địa chỉ app | `http://127.0.0.1:3000`, HTTP | `https://<tên-service>.onrender.com`, HTTPS |
| Cách chạy bản mới | `podman compose up --build` | Merge vào `main` → Actions → deploy hook |
| `$PORT` | Không đặt, uvicorn dùng mặc định 8000 | Render tự đặt, không ghi đè |
| Ngủ khi không dùng | Không | Render sleep sau ~15 phút; Supabase pause sau 7 ngày không hoạt động |
| Gemini | Chỉ chạy khi `.env` có key; không có key thì `/diagnose` trả 503 `NO_KEY` | Key ở Render Environment |

## 4. Kiến trúc 3 tầng

```mermaid
flowchart TB
    subgraph P["Presentation (trình duyệt)"]
        direction LR
        T["templates/<br/>base.html + S01 → S11<br/>(Jinja2, server render khung trang)"]
        J["static/app.js<br/>fetch tới /api/*, /diagnose<br/>showError(message)"]
        C["static/style.css<br/>theo Figma"]
    end

    subgraph L["Logic (FastAPI)"]
        direction LR
        M["main.py<br/>tạo app, lifespan,<br/>/, /health, /health/db"]
        R["routers/<br/>pages · vehicles · records ·<br/>service_types · reminders ·<br/>stats · diagnose"]
        SC["schemas.py<br/>Pydantic model<br/>kiểm tra input, định dạng output"]
        AI["services/ai.py<br/>AiService, AiError"]
    end

    subgraph DA["Data"]
        direction LR
        DBP["db.py<br/>ConnectionPool (psycopg_pool)"]
        PG[("PostgreSQL 16<br/>bảng + v_record_totals,<br/>v_reminder_status")]
    end

    Gemini["Google Gemini API"]

    J -- "JSON qua HTTP(S)" --> R
    T -. "render bởi router pages<br/>(TemplateResponse)" .- R
    R --> SC
    R -- "chỉ router diagnose" --> AI
    AI -- HTTPS --> Gemini
    R -- "with pool.connection()" --> DBP
    M --> DBP
    DBP -- "SQL tham số hóa" --> PG
```

**Quy tắc giữa các tầng**
- Trình duyệt chỉ nói chuyện với FastAPI. Không bao giờ gọi thẳng Supabase hay Gemini (NFR-01, PR-06).
- Mỗi router làm đúng 3 việc (tài liệu 08, mục 3): nhận input đã được Pydantic kiểm tra → chạy SQL tham số hóa → trả JSON hoặc trang HTML. Router không ghép chuỗi SQL.
- Quy tắc tính toán nằm ở tầng Data khi có thể: thành tiền là cột sinh tự động, tổng chi phí và trạng thái nhắc lịch là view. Router chỉ đọc, nên không có chỗ nào tính lệch nhau.
- Phần gọi Gemini tách riêng trong `services/ai.py`, để router `diagnose` không phụ thuộc chi tiết HTTP của Gemini và để test thay hàm này bằng mock (NFR-11).
- `/health` nằm ở `main.py` và không chạm DB; `/health/db` mượn một kết nối từ pool và trả 503 khi lỗi (NFR-04, NFR-05).

## 5. Luồng xử lý một request: `POST /diagnose`

Request phức tạp nhất của hệ thống, đi qua đủ 3 tầng và gọi ra hệ thống ngoài. Luồng nghiệp vụ đầy đủ ở activity diagram 3 của [tài liệu 03](../03-activity/README.md#3-chẩn-đoán-ai).

```mermaid
sequenceDiagram
    autonumber
    actor U as Chủ xe
    participant JS as app.js (S10)
    participant R as routers/diagnose.py
    participant AI as services/ai.py
    participant G as Gemini API
    participant DB as PostgreSQL

    U->>JS: Nhập triệu chứng, bấm Chẩn đoán
    JS->>JS: Khóa nút, hiện Đang chẩn đoán
    JS->>R: POST /diagnose {symptom_text, vehicle_id}
    R->>R: DiagnoseIn kiểm tra 10–1.000 ký tự
    alt Input sai
        R-->>JS: 422
    else Input đúng
        R->>DB: SELECT xe (nếu có), tên service_types đang dùng
        R->>AI: diagnose(symptom_text, vehicle, service_type_names)
        alt Thiếu GEMINI_API_KEY
            AI-->>R: raise AiError(NO_KEY)
        else Có key
            AI->>G: POST generateContent (timeout 20 giây)
            alt 200 + JSON hợp lệ
                G-->>AI: {suggestion, urgency_level, service_type}
                AI-->>R: AiSuggestion
            else 429
                G-->>AI: 429
                AI-->>R: raise AiError(RATE_LIMITED)
            else Quá 20 giây
                AI-->>R: raise AiError(TIMEOUT)
            else 5xx, lỗi mạng, JSON sai
                AI-->>R: raise AiError(UPSTREAM_ERROR)
            end
        end
        alt Thành công
            R->>DB: INSERT diagnoses (OK, ai_suggestion, urgency_level, suggested_service_type_id, model)
            R-->>JS: 200 DiagnoseOut
            JS-->>U: Hiện gợi ý + mức khẩn cấp + lưu ý tham khảo
        else AiError
            R->>R: Ghi log chi tiết (không có key)
            R->>DB: INSERT diagnoses (FAILED, error_code)
            R-->>JS: 503 / 429 / 504 / 502 ErrorOut
            JS-->>U: showError(message), giữ nguyên ô nhập
        end
    end
    JS->>JS: Mở lại nút Chẩn đoán
```

## 6. Class diagram

Ứng dụng viết theo kiểu FastAPI: router là module Python chứa các hàm xử lý, không phải lớp. Trong class diagram, mỗi module được vẽ như một lớp có nhãn `«router»` hoặc `«module»`, các hàm là phương thức. Kiểu dữ liệu ghi theo Python: `X | None` là có thể trống, `list[X]` là danh sách, `Decimal` cho tiền (khớp `numeric` của PostgreSQL).

Pydantic model đặt trong `app/schemas.py`. Quy ước tên: `...In` là dữ liệu trình duyệt gửi lên (đã kiểm tra ràng buộc), `...Out` là dữ liệu server trả về. Các kiểu liệt kê dùng `StrEnum`, giá trị trùng với `CHECK ... IN (...)` ở `schema.sql`.

### 6.1. Pydantic model – xe, bảo dưỡng, loại dịch vụ, nhắc lịch

```mermaid
classDiagram
    direction LR

    class VehicleIn {
        +name: str  1–100 ký tự
        +vehicle_type: VehicleType
        +brand: str | None
        +model: str | None
        +manufacture_year: int | None  1950–2100
        +license_plate: str | None
        +current_odometer: int = 0  ≥ 0
        +purchase_date: date | None
    }
    class VehicleOut {
        +id: int
        +is_archived: bool
        +created_at: datetime
    }
    class VehicleListItem {
        +id: int
        +name: str
        +vehicle_type: VehicleType
        +license_plate: str | None
        +current_odometer: int
        +attention_count: int
    }

    class ItemIn {
        +service_type_id: int
        +description: str | None
        +quantity: Decimal = 1  > 0
        +unit_price: Decimal = 0  ≥ 0
    }
    class RecordIn {
        +service_date: date
        +odometer: int  ≥ 0
        +garage_name: str | None
        +note: str | None
        +items: list[ItemIn]  ít nhất 1
        +check_not_future() BR-03
    }
    class ItemOut {
        +id: int
        +service_type_id: int
        +service_type_name: str
        +description: str | None
        +quantity: Decimal
        +unit_price: Decimal
        +line_total: Decimal
    }
    class RecordSummary {
        +record_id: int
        +service_date: date
        +odometer: int
        +garage_name: str | None
        +item_count: int
        +total_cost: Decimal
    }
    class RecordOut {
        +vehicle_id: int
        +note: str | None
        +items: list[ItemOut]
    }

    class ServiceTypeIn {
        +name: str  1–100 ký tự
        +description: str | None
        +applies_to: AppliesTo = ALL
        +default_interval_km: int | None  > 0
        +default_interval_months: int | None  > 0
        +is_active: bool = True
    }
    class ServiceTypeOut {
        +id: int
    }

    class ReminderIn {
        +vehicle_id: int
        +service_type_id: int
        +interval_km: int | None  > 0
        +interval_months: int | None  > 0
        +start_date: date | None  trống = hôm nay
        +start_odometer: int | None  trống = ODO xe
        +notify_before_days: int = 7
        +notify_before_km: int = 300
        +is_active: bool = True
        +check_has_interval() BR-06
    }
    class ReminderOut {
        +reminder_id: int
        +vehicle_id: int
        +vehicle_name: str
        +service_type_id: int
        +service_type_name: str
        +interval_km: int | None
        +interval_months: int | None
        +base_date: date
        +base_odometer: int
        +next_due_date: date | None
        +next_due_odometer: int | None
        +days_left: int | None
        +km_left: int | None
        +is_active: bool
        +status: ReminderStatus
    }

    class VehicleType {
        <<enumeration>>
        MOTORBIKE
        CAR
        OTHER
    }
    class AppliesTo {
        <<enumeration>>
        MOTORBIKE
        CAR
        ALL
    }
    class ReminderStatus {
        <<enumeration>>
        OK
        DUE_SOON
        OVERDUE
    }

    VehicleIn <|-- VehicleOut
    RecordSummary <|-- RecordOut
    ServiceTypeIn <|-- ServiceTypeOut
    RecordIn *-- "1..*" ItemIn
    RecordOut *-- "1..*" ItemOut
    VehicleIn ..> VehicleType
    ServiceTypeIn ..> AppliesTo
    ReminderOut ..> ReminderStatus
```

| Model | Bảng / view ở tài liệu 04 | Dùng ở API |
|---|---|---|
| `VehicleIn`, `VehicleOut` | `vehicles` | `POST`, `PUT`, `GET /api/vehicles/{id}` |
| `VehicleListItem` | `vehicles` + `v_reminder_status` (đếm nhắc lịch cần chú ý) | `GET /api/vehicles` |
| `RecordIn`, `ItemIn` | `maintenance_records`, `maintenance_items` | `POST /api/vehicles/{id}/records`, `PUT /api/records/{id}` |
| `RecordSummary` | `v_record_totals` | `GET /api/vehicles/{id}/records`, Dashboard |
| `RecordOut`, `ItemOut` | `v_record_totals` + `maintenance_items` + `service_types` | `GET /api/records/{id}` |
| `ServiceTypeIn`, `ServiceTypeOut` | `service_types` | `/api/service-types` |
| `ReminderIn` | `reminders` | `POST /api/reminders`, `PUT /api/reminders/{id}` |
| `ReminderOut` | `v_reminder_status` | `GET /api/reminders`, Dashboard |

### 6.2. Pydantic model – chẩn đoán AI, thống kê, lỗi

```mermaid
classDiagram
    direction LR

    class DiagnoseIn {
        +symptom_text: str  10–1.000 ký tự
        +vehicle_id: int | None
    }
    class AiSuggestion {
        +suggestion: str
        +urgency_level: UrgencyLevel
        +service_type: str | None
    }
    class DiagnoseOut {
        +diagnosis_id: int
        +suggestion: str
        +urgency_level: UrgencyLevel
        +suggested_service_type_id: int | None
        +suggested_service_type_name: str | None
        +disclaimer: str
    }
    class DiagnosisOut {
        +id: int
        +created_at: datetime
        +vehicle_name: str | None
        +symptom_text: str
        +status: DiagnosisStatus
        +urgency_level: UrgencyLevel | None
        +ai_suggestion: str | None
        +error_code: AiErrorCode | None
    }
    class DashboardOut {
        +vehicle_count: int
        +cost_this_month: Decimal
        +attention_reminders: list[ReminderOut]
        +recent_records: list[RecordSummary]
    }
    class CostRow {
        +label: str
        +total_cost: Decimal
    }
    class ErrorOut {
        +error_code: str
        +message: str
    }
    class ReminderOut {
        <<xem 6.1>>
    }
    class RecordSummary {
        <<xem 6.1>>
    }

    class UrgencyLevel {
        <<enumeration>>
        LOW
        MEDIUM
        HIGH
    }
    class DiagnosisStatus {
        <<enumeration>>
        OK
        FAILED
    }
    class AiErrorCode {
        <<enumeration>>
        NO_KEY
        RATE_LIMITED
        TIMEOUT
        UPSTREAM_ERROR
    }

    DashboardOut o-- "0..*" ReminderOut
    DashboardOut o-- "0..5" RecordSummary
    AiSuggestion ..> UrgencyLevel
    DiagnoseOut ..> UrgencyLevel
    DiagnosisOut ..> DiagnosisStatus
    DiagnosisOut ..> AiErrorCode
```

| Model | Bảng ở tài liệu 04 | Vai trò |
|---|---|---|
| `DiagnoseIn` | `diagnoses.symptom_text`, `vehicle_id` | Body của `POST /diagnose`; sai độ dài thì 422, không gọi AI |
| `AiSuggestion` | `diagnoses.ai_suggestion`, `urgency_level` | Kiểm tra JSON Gemini trả về. Sai định dạng thì `AiService` coi là `UPSTREAM_ERROR` |
| `DiagnoseOut` | 1 dòng `diagnoses` có `status = OK` | Kết quả trả cho S10, luôn có `disclaimer` (FR-19) |
| `DiagnosisOut` | `diagnoses` + `vehicles.name` | Một dòng lịch sử ở S11 (FR-21) |
| `DashboardOut`, `CostRow` | `v_record_totals`, `v_reminder_status` | `GET /api/stats/dashboard`, `GET /api/stats/costs` |
| `ErrorOut` | – | Body của mọi lỗi nghiệp vụ (404, 409, lỗi AI). Lỗi 422 giữ định dạng mặc định của FastAPI để `app.js` biết trường nào sai |

### 6.3. Router, AiService, AiError, ConnectionPool

```mermaid
classDiagram
    direction LR

    class main {
        <<module>>
        +app: FastAPI
        +lifespan(app) mở / đóng pool
        +root() dict  tên app, phiên bản
        +health() dict  không chạm DB
        +health_db() dict  503 nếu lỗi
    }
    class db {
        <<module>>
        +pool: ConnectionPool
        +open_pool() None
        +close_pool() None
    }
    class ConnectionPool {
        <<psycopg_pool>>
        +conninfo = DATABASE_URL
        +max_size = 5
        +max_lifetime = 300
        +check = check_connection
        +kwargs: prepare_threshold=None, connect_timeout=5
        +connection() Connection
    }

    class vehicles {
        <<router>>
        +list_vehicles() list[VehicleListItem]
        +create_vehicle(body: VehicleIn) VehicleOut
        +get_vehicle(id) VehicleOut
        +update_vehicle(id, body: VehicleIn) VehicleOut
        +delete_vehicle(id) None
        +archive_vehicle(id) VehicleOut
    }
    class records {
        <<router>>
        +list_records(vehicle_id, from_date, to_date) list[RecordSummary]
        +create_record(vehicle_id, body: RecordIn) RecordOut
        +get_record(id) RecordOut
        +update_record(id, body: RecordIn) RecordOut
        +delete_record(id) None
        +export_csv(vehicle_id) StreamingResponse
    }
    class service_types {
        <<router>>
        +list_service_types(active: bool | None) list[ServiceTypeOut]
        +create_service_type(body: ServiceTypeIn) ServiceTypeOut
        +update_service_type(id, body: ServiceTypeIn) ServiceTypeOut
    }
    class reminders {
        <<router>>
        +list_reminders(vehicle_id, status) list[ReminderOut]
        +create_reminder(body: ReminderIn) ReminderOut
        +update_reminder(id, body: ReminderIn) ReminderOut
        +delete_reminder(id) None
    }
    class stats {
        <<router>>
        +dashboard() DashboardOut
        +costs(group_by, from_date, to_date) list[CostRow]
    }
    class diagnose {
        <<router>>
        +diagnose(body: DiagnoseIn) DiagnoseOut
        +list_diagnoses() list[DiagnosisOut]
        -save_diagnosis(conn, ...) int
    }
    class pages {
        <<router>>
        +một hàm cho mỗi màn hình S01 → S11
        trả TemplateResponse
    }

    class AiService {
        <<module services/ai.py>>
        +GEMINI_MODEL: str
        +TIMEOUT_SECONDS = 20
        +diagnose(symptom_text, vehicle, service_type_names) AiSuggestion
        -build_prompt(symptom_text, vehicle, service_type_names) str
        -call_gemini(prompt) dict
        -parse_response(raw) AiSuggestion
    }
    class AiError {
        <<Exception>>
        +code: AiErrorCode
        +status_code: int
        +user_message: str
    }
    class AiErrorCode {
        <<enumeration>>
        NO_KEY = 503
        RATE_LIMITED = 429
        TIMEOUT = 504
        UPSTREAM_ERROR = 502
    }

    main --> db : lifespan
    db *-- ConnectionPool
    vehicles --> db
    records --> db
    service_types --> db
    reminders --> db
    stats --> db
    diagnose --> db
    diagnose --> AiService
    AiService ..> AiError : raise
    diagnose ..> AiError : bắt, đổi thành ErrorOut
    AiError --> AiErrorCode
```

**`AiService` ánh xạ lỗi sang `AiError`** (bảng BR-10 tài liệu 01):

| Điều kiện trong `services/ai.py` | `AiErrorCode` | HTTP trả trình duyệt | `user_message` |
|---|---|---|---|
| `os.getenv("GEMINI_API_KEY")` rỗng | `NO_KEY` | 503 | Tính năng chẩn đoán AI tạm thời không khả dụng. |
| Gemini trả `429` | `RATE_LIMITED` | 429 | Đã hết lượt chẩn đoán miễn phí, vui lòng thử lại sau ít phút. |
| `httpx.TimeoutException` (quá 20 giây) | `TIMEOUT` | 504 | AI phản hồi quá lâu, vui lòng thử lại. |
| Gemini trả `5xx` hoặc 4xx khác (ví dụ key sai), `httpx.TransportError` (lỗi mạng), JSON không qua được `AiSuggestion` | `UPSTREAM_ERROR` | 502 | Không nhận được kết quả từ AI, vui lòng thử lại. |

Request gửi Gemini đặt `generationConfig.responseMimeType = "application/json"` để model trả JSON, nhưng server vẫn luôn kiểm tra lại bằng `AiSuggestion` vì model có thể trả sai.

## 7. Trách nhiệm từng thành phần

| Thành phần | File | Trách nhiệm | FR / yêu cầu | Module (08) |
|---|---|---|---|---|
| `main` | `app/main.py` | Tạo app, gắn router, mount `static/`; lifespan mở pool khi khởi động, đóng khi tắt; `/` trả tên + phiên bản (dùng kiểm tra deploy PT-04); `/health` không chạm DB; `/health/db` đếm `vehicles`, lỗi thì 503; đăng ký exception handler đổi `AiError` và lỗi nghiệp vụ thành `ErrorOut` | NFR-04, NFR-05 | M0 |
| `db` + `ConnectionPool` | `app/db.py` | Một pool dùng chung cho cả app; đọc `DATABASE_URL` (bắt buộc, thiếu thì app dừng ngay khi khởi động); kiểm tra kết nối trước khi cho mượn, thay kết nối sau 5 phút, `prepare_threshold=None` cho pooler 6543, `connect_timeout=5` | PR-05, NFR-05 | M1 |
| `schemas` | `app/schemas.py` | Tất cả Pydantic model ở mục 6.1–6.2: ràng buộc độ dài, khoảng giá trị, kiểu liệt kê; validator `check_not_future` (BR-03), `check_has_interval` (BR-06) | NFR-02 | Người làm module tương ứng |
| `vehicles` | `app/routers/vehicles.py` | CRUD xe; kiểm tra ODO mới không nhỏ hơn ODO hiện tại (BR-02); bắt vi phạm UNIQUE biển số → 409 (BR-01); xóa xe có lịch sử → 409 (BR-09); trả 404 cho M3, M5, M7 | FR-01 → FR-05 | M2 |
| `records` | `app/routers/records.py` | Lịch sử, chi tiết; ghi nhận và sửa trong **một transaction** (record + items + nâng ODO); bắt vi phạm UNIQUE (xe, ngày, ODO) → 409 (BR-04); xuất CSV | FR-06 → FR-10 | M3 |
| `service_types` | `app/routers/service_types.py` | Danh mục, lọc `active`; thêm/sửa/ngừng dùng, không có xóa (BR-09) | FR-11, FR-12 | M4 |
| `reminders` | `app/routers/reminders.py` | CRUD nhắc lịch; điền mặc định `start_date`, `start_odometer`; trùng → 409 (BR-06); đọc trạng thái từ `v_reminder_status` | FR-13 → FR-15 | M5 |
| `stats` | `app/routers/stats.py` | Số liệu Dashboard và thống kê chi phí từ hai view; nhóm theo loại dịch vụ cộng theo hạng mục | FR-16, FR-17 | M6 |
| `diagnose` | `app/routers/diagnose.py` | Kiểm tra `DiagnoseIn`; lấy thông tin xe và tên loại dịch vụ; gọi `AiService`; lưu **mọi** lần gọi vào `diagnoses` (OK hoặc FAILED); trả `DiagnoseOut` hoặc `ErrorOut`; lịch sử chẩn đoán | FR-18 → FR-22, BR-10 | M7 |
| `pages` | `app/routers/pages.py` | Trả trang HTML S01 → S11 bằng Jinja2; dữ liệu do `app.js` tải qua API | Tài liệu 01, mục 7 | M6 (khung), mỗi người trang của module mình |
| `AiService` | `app/services/ai.py` | Đọc key bằng `os.getenv`; tạo prompt; gọi Gemini bằng `httpx` với timeout 20 giây, key ở header; **không tự gọi lại** khi gặp 429; kiểm tra JSON bằng `AiSuggestion`; ánh xạ lỗi thành `AiError`; ghi log chi tiết nhưng không ghi key | PR-06, NFR-01, NFR-06 | M7 |
| `AiError`, `AiErrorCode` | `app/services/ai.py` | Mang mã lỗi, HTTP status và câu thông báo thân thiện theo BR-10 | FR-20 | M7 |
| `app.js` | `app/static/app.js` | Gọi API bằng `fetch`, khóa nút khi chờ, `showError(message)` cho `ErrorOut`, hiện lỗi 422 dưới đúng ô nhập | NFR-08 | M6 |

## 8. Cấu trúc thư mục `app/` theo class diagram

```
app/
├── main.py              # main
├── db.py                # db, ConnectionPool
├── schemas.py           # Pydantic model mục 6.1, 6.2
├── routers/
│   ├── vehicles.py      # «router» vehicles      – M2 (Lâm)
│   ├── records.py       # «router» records       – M3 (Lâm)
│   ├── service_types.py # «router» service_types – M4 (Khoa)
│   ├── reminders.py     # «router» reminders     – M5 (Giang)
│   ├── stats.py         # «router» stats         – M6 (Khoa)
│   ├── diagnose.py      # «router» diagnose      – M7 (Giang)
│   └── pages.py         # «router» pages
├── services/
│   └── ai.py            # AiService, AiError, AiErrorCode
├── templates/           # base.html + S01 → S11
└── static/              # style.css, app.js
```

So với mục 3 tài liệu 08: thêm `app/schemas.py` cho các Pydantic model. Phần còn lại giữ nguyên.

## 9. Ghi chú cho tài liệu 08

Đề xuất Giang cập nhật tài liệu 08 sau khi nhóm duyệt tài liệu này:

1. **Mục 1:** thư viện gọi AI chốt là `httpx` (lý do ở mục 1 tài liệu này).
2. **Mục 3:** thêm `app/schemas.py`.
3. **Hợp đồng với M6 (`showError`):** lỗi nghiệp vụ và lỗi AI trả body `ErrorOut` `{error_code, message}`; lỗi 422 giữ định dạng mặc định của FastAPI. `app.js` chỉ cần xử lý hai dạng này.
4. **Mục 5 (Bảo mật key):** gửi key Gemini qua header `x-goog-api-key`, không đặt trong query string `?key=`, để key không xuất hiện trong log request.
5. **Mục 9:** health check path của Render đặt là `/health`.
