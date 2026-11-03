-- db/schema.sql -- the whole schema of Vehicle Maintenance Log. Safe to run more than once.
-- PostgreSQL 16: chạy bởi Compose ở lần khởi động đầu và trong Supabase SQL Editor.
-- Người phụ trách: Kiều Bảo Giang (bước 04 - ERD & Database Design)

-- -------------------------------------------------------------
-- Tài khoản và phiên đăng nhập (FR-23 -> FR-25)
-- Mật khẩu chỉ lưu dạng băm scrypt; phiên chỉ lưu sha256 của token nằm trong cookie.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email         text NOT NULL UNIQUE CHECK (email = lower(email) AND length(email) BETWEEN 3 AND 254), -- BR-11
  display_name  text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 60),
  password_hash text NOT NULL,                                   -- '!' = không đăng nhập bằng mật khẩu được
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash text PRIMARY KEY,
  user_id    bigint NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions (user_id);

-- Tài khoản dùng thử: nút "Dùng thử" vào thẳng; dữ liệu mẫu (seed.sql) thuộc về tài khoản này.
INSERT INTO users (email, display_name, password_hash)
VALUES ('demo@sobaoduong.local', 'Tài khoản dùng thử', '!')
ON CONFLICT (email) DO NOTHING;

-- -------------------------------------------------------------
-- Danh mục loại dịch vụ (FR-11, FR-12)
-- user_id NULL = loại mặc định, mọi người cùng thấy, chỉ đọc. Có user_id = loại riêng của người đó.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS service_types (
  id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id                 bigint REFERENCES users (id),
  name                    text NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
  description             text,
  applies_to              text NOT NULL DEFAULT 'ALL' CHECK (applies_to IN ('MOTORBIKE', 'CAR', 'ALL')),
  default_interval_km     integer CHECK (default_interval_km > 0),
  default_interval_months integer CHECK (default_interval_months > 0),
  is_active               boolean NOT NULL DEFAULT true          -- BR-09: ngừng dùng thay vì xóa
);

-- -------------------------------------------------------------
-- Xe (FR-01 -> FR-05)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id          bigint NOT NULL REFERENCES users (id),         -- FR-25: xe của ai người đó thấy
  name             text NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
  vehicle_type     text NOT NULL CHECK (vehicle_type IN ('MOTORBIKE', 'CAR', 'OTHER')),
  brand            text,
  model            text,
  manufacture_year integer CHECK (manufacture_year BETWEEN 1950 AND 2100),
  license_plate    text,                                         -- BR-01: không trùng trong xe của một người
  current_odometer integer NOT NULL DEFAULT 0 CHECK (current_odometer >= 0),
  purchase_date    date,
  is_archived      boolean NOT NULL DEFAULT false,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------
-- Lần bảo dưỡng (FR-06 -> FR-09)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_records (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vehicle_id   bigint NOT NULL REFERENCES vehicles (id) ON DELETE RESTRICT, -- BR-09
  service_date date NOT NULL,                                    -- BR-03 kiểm tra ở app
  odometer     integer NOT NULL CHECK (odometer >= 0),
  garage_name  text,
  note         text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (vehicle_id, service_date, odometer)                    -- BR-04: chống nhập trùng
);

CREATE INDEX IF NOT EXISTS maintenance_records_vehicle_date_idx
  ON maintenance_records (vehicle_id, service_date DESC);

-- -------------------------------------------------------------
-- Hạng mục trong lần bảo dưỡng (FR-06, FR-08)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_items (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  record_id       bigint NOT NULL REFERENCES maintenance_records (id) ON DELETE CASCADE,
  service_type_id bigint NOT NULL REFERENCES service_types (id) ON DELETE RESTRICT, -- BR-09
  description     text,
  quantity        numeric(8, 2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
  unit_price      numeric(12, 0) NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
  line_total      numeric(14, 0) GENERATED ALWAYS AS (round(quantity * unit_price)) STORED -- BR-05
);

CREATE INDEX IF NOT EXISTS maintenance_items_record_idx ON maintenance_items (record_id);
CREATE INDEX IF NOT EXISTS maintenance_items_service_type_idx ON maintenance_items (service_type_id);

-- -------------------------------------------------------------
-- Nhắc lịch (FR-13 -> FR-15)
-- start_date / start_odometer: mốc gốc khi xe chưa có lần bảo dưỡng nào cùng loại (BR-07)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reminders (
  id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vehicle_id         bigint NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
  service_type_id    bigint NOT NULL REFERENCES service_types (id) ON DELETE RESTRICT,
  interval_km        integer CHECK (interval_km > 0),
  interval_months    integer CHECK (interval_months > 0),
  start_date         date NOT NULL DEFAULT current_date,
  start_odometer     integer NOT NULL DEFAULT 0 CHECK (start_odometer >= 0),
  notify_before_days integer NOT NULL DEFAULT 7 CHECK (notify_before_days >= 0),
  notify_before_km   integer NOT NULL DEFAULT 300 CHECK (notify_before_km >= 0),
  is_active          boolean NOT NULL DEFAULT true,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (vehicle_id, service_type_id),                          -- BR-06
  CHECK (interval_km IS NOT NULL OR interval_months IS NOT NULL) -- BR-06
);

-- -------------------------------------------------------------
-- Lịch sử chẩn đoán AI (FR-18 -> FR-21)
-- Lưu cả lần gọi lỗi: bằng chứng cho mục "AI API integration" của report
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diagnoses (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id       bigint NOT NULL REFERENCES users (id),
  vehicle_id    bigint REFERENCES vehicles (id) ON DELETE SET NULL,
  symptom_text  text NOT NULL CHECK (length(symptom_text) BETWEEN 10 AND 1000),
  status        text NOT NULL CHECK (status IN ('OK', 'FAILED')),
  ai_suggestion text,
  urgency_level text CHECK (urgency_level IN ('LOW', 'MEDIUM', 'HIGH')),
  suggested_service_type_id bigint REFERENCES service_types (id) ON DELETE SET NULL,
  error_code    text CHECK (error_code IN ('NO_KEY', 'RATE_LIMITED', 'TIMEOUT', 'UPSTREAM_ERROR')),
  model         text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'OK' AND ai_suggestion IS NOT NULL AND error_code IS NULL)
      OR (status = 'FAILED' AND error_code IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS diagnoses_created_at_idx ON diagnoses (created_at DESC);

-- -------------------------------------------------------------
-- Nâng cấp database tạo trước khi có tài khoản (Supabase): dữ liệu cũ thành của tài khoản dùng thử.
-- Với database mới, các lệnh dưới không làm gì.
-- -------------------------------------------------------------
ALTER TABLE service_types ADD COLUMN IF NOT EXISTS user_id bigint REFERENCES users (id);
ALTER TABLE vehicles      ADD COLUMN IF NOT EXISTS user_id bigint REFERENCES users (id);
ALTER TABLE diagnoses     ADD COLUMN IF NOT EXISTS user_id bigint REFERENCES users (id);
UPDATE vehicles  SET user_id = (SELECT id FROM users WHERE email = 'demo@sobaoduong.local') WHERE user_id IS NULL;
UPDATE diagnoses SET user_id = (SELECT id FROM users WHERE email = 'demo@sobaoduong.local') WHERE user_id IS NULL;
ALTER TABLE vehicles  ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE diagnoses ALTER COLUMN user_id SET NOT NULL;

-- Trùng tên loại việc / trùng biển số chỉ tính trong dữ liệu của một người (thay cho UNIQUE toàn bảng)
ALTER TABLE service_types DROP CONSTRAINT IF EXISTS service_types_name_key;
ALTER TABLE vehicles      DROP CONSTRAINT IF EXISTS vehicles_license_plate_key;
CREATE UNIQUE INDEX IF NOT EXISTS service_types_user_name_key ON service_types (user_id, name) NULLS NOT DISTINCT;
CREATE UNIQUE INDEX IF NOT EXISTS vehicles_user_plate_key ON vehicles (user_id, license_plate);
CREATE INDEX IF NOT EXISTS vehicles_user_idx ON vehicles (user_id);
CREATE INDEX IF NOT EXISTS diagnoses_user_idx ON diagnoses (user_id, created_at DESC);

-- -------------------------------------------------------------
-- View: tổng chi phí mỗi lần bảo dưỡng (BR-05)
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_record_totals WITH (security_invoker = true) AS
SELECT
  r.id                                   AS record_id,
  r.vehicle_id,
  r.service_date,
  r.odometer,
  r.garage_name,
  r.note,
  count(i.id)                            AS item_count,
  coalesce(sum(i.line_total), 0)         AS total_cost
FROM maintenance_records r
LEFT JOIN maintenance_items i ON i.record_id = r.id
GROUP BY r.id;

-- -------------------------------------------------------------
-- View: trạng thái nhắc lịch, tính ngay lúc đọc (BR-06 -> BR-08)
-- Không cần tác vụ chạy ngầm: Render free sleep nên cron không đáng tin.
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW v_reminder_status WITH (security_invoker = true) AS
WITH base AS (
  SELECT
    rm.*,
    v.name             AS vehicle_name,
    v.current_odometer,
    st.name            AS service_type_name,
    last.service_date  AS last_service_date,
    last.odometer      AS last_service_odometer
  FROM reminders rm
  JOIN vehicles v       ON v.id = rm.vehicle_id
  JOIN service_types st ON st.id = rm.service_type_id
  LEFT JOIN LATERAL (                                            -- lần làm gần nhất cùng loại dịch vụ
    SELECT r.service_date, r.odometer
    FROM maintenance_records r
    JOIN maintenance_items i ON i.record_id = r.id
    WHERE r.vehicle_id = rm.vehicle_id
      AND i.service_type_id = rm.service_type_id
    ORDER BY r.service_date DESC, r.odometer DESC
    LIMIT 1
  ) last ON true
), due AS (
  SELECT
    base.*,
    CASE WHEN last_service_date >= start_date THEN last_service_date ELSE start_date END AS base_date,
    CASE WHEN last_service_date >= start_date THEN last_service_odometer ELSE start_odometer END AS base_odometer
  FROM base
), calc AS (
  SELECT
    due.*,
    (base_date + make_interval(months => interval_months))::date AS next_due_date,
    base_odometer + interval_km                                  AS next_due_odometer
  FROM due
)
SELECT
  id AS reminder_id,
  vehicle_id,
  vehicle_name,
  service_type_id,
  service_type_name,
  interval_km,
  interval_months,
  base_date,
  base_odometer,
  next_due_date,
  next_due_odometer,
  current_odometer,
  next_due_date - current_date            AS days_left,
  next_due_odometer - current_odometer    AS km_left,
  is_active,
  CASE
    WHEN next_due_date <= current_date
      OR next_due_odometer <= current_odometer THEN 'OVERDUE'
    WHEN next_due_date - current_date <= notify_before_days
      OR next_due_odometer - current_odometer <= notify_before_km THEN 'DUE_SOON'
    ELSE 'OK'
  END                                     AS status
FROM calc;

-- Supabase publishes an automatic REST API for tables in "public". We do not use it.
-- RLS on + no policies = that API sees nothing. The app connects as the table
-- owner, which bypasses RLS, so the app is not affected.
ALTER TABLE service_types       ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles            ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_items   ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders           ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagnoses           ENABLE ROW LEVEL SECURITY;
ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions            ENABLE ROW LEVEL SECURITY;
