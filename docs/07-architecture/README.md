# 07 – Architecture & Class Diagram

**Người phụ trách:** Tăng Thoại Lâm · **Đầu vào:** [02 Use Case](../02-use-case/), [04 Database](../04-database/erd.md), [08 Implementation Plan](../08-implementation-plan/implementation-plan.md) (mục 2–4)

Cần nộp:
1. **Sơ đồ triển khai khớp đúng thực tế.** Brief trừ điểm nếu sơ đồ không khớp deployment. Gồm: Trình duyệt → Render (container FastAPI) → Supabase (pooler 6543); Render → Gemini API; GitHub → Actions (`check`, `deploy`) → Render deploy hook. Vẽ thêm một sơ đồ cho môi trường local (Compose: `web` + `db`) và ghi rõ khác cloud ở đâu.
2. **Kiến trúc 3 tầng:** Presentation (Jinja2 + JS) / Logic (FastAPI routers + services) / Data (PostgreSQL).
3. **Class diagram:** Pydantic model cho từng bảng ở tài liệu 04 (`VehicleIn`, `VehicleOut`, `RecordIn`, `ItemIn`, `ReminderIn`, `DiagnoseIn`, `DiagnoseOut`...), các router, `AiService`, lớp ngoại lệ `AiError` (NO_KEY, RATE_LIMITED, TIMEOUT, UPSTREAM_ERROR), `ConnectionPool`.
4. Bảng trách nhiệm từng lớp và **chốt công nghệ** (bản đề xuất ở mục 2 tài liệu 08).
