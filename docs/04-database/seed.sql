-- db/seed.sql -- demo rows for Vehicle Maintenance Log. Run after schema.sql.
-- Safe to run more than once: every insert skips rows that already exist (natural keys),
-- so ids are never hard-coded and nothing is duplicated.

-- -------------------------------------------------------------
-- Danh mục loại dịch vụ (chu kỳ tham khảo phổ biến)
-- -------------------------------------------------------------
INSERT INTO service_types (name, description, applies_to, default_interval_km, default_interval_months)
VALUES
  ('Thay nhớt máy (xe máy)',       'Thay dầu động cơ xe máy',                       'MOTORBIKE', 1500,  2),
  ('Thay nhớt hộp số (xe tay ga)', 'Thay dầu láp/hộp số cho xe tay ga',             'MOTORBIKE', 6000,  6),
  ('Thay dầu động cơ (ô tô)',      'Thay dầu máy và lọc dầu',                       'CAR',       5000,  6),
  ('Thay lọc gió',                 'Vệ sinh hoặc thay lọc gió động cơ',             'ALL',       10000, 12),
  ('Thay bugi',                    'Thay bugi đánh lửa',                            'ALL',       8000,  12),
  ('Bảo dưỡng phanh',              'Kiểm tra, thay má phanh/dầu phanh',             'ALL',       10000, 12),
  ('Thay lốp',                     'Thay lốp xe',                                   'ALL',       30000, 36),
  ('Thay nước làm mát',            'Xả và thay nước làm mát',                       'CAR',       40000, 24),
  ('Thay ắc quy',                  'Thay bình ắc quy',                              'ALL',       NULL,  24),
  ('Bảo dưỡng định kỳ tổng quát',  'Gói bảo dưỡng định kỳ theo khuyến nghị hãng',   'ALL',       10000, 6),
  ('Vệ sinh nồi / dây curoa',      'Vệ sinh bộ nồi, kiểm tra dây curoa xe tay ga',  'MOTORBIKE', 8000,  12),
  ('Sửa chữa khác',                'Công việc không nằm trong danh mục',            'ALL',       NULL,  NULL)
ON CONFLICT (name) DO NOTHING;

-- -------------------------------------------------------------
-- Xe
-- -------------------------------------------------------------
INSERT INTO vehicles (name, vehicle_type, brand, model, manufacture_year, license_plate, current_odometer, purchase_date)
VALUES
  ('Vision đi làm', 'MOTORBIKE', 'Honda',  'Vision',        2022, '59X1-123.45', 12850, '2022-03-15'),
  ('Vios gia đình', 'CAR',       'Toyota', 'Vios',          2020, '51H-678.90',  45200, '2020-08-01'),
  ('Air Blade',     'MOTORBIKE', 'Honda',  'Air Blade 125', 2021, '59P2-456.78', 20300, '2021-05-20')
ON CONFLICT (license_plate) DO NOTHING;

-- -------------------------------------------------------------
-- Lần bảo dưỡng
-- -------------------------------------------------------------
INSERT INTO maintenance_records (vehicle_id, service_date, odometer, garage_name, note)
SELECT v.id, x.service_date::date, x.odometer, x.garage_name, x.note
FROM (VALUES
  ('59X1-123.45', '2026-03-10',  9800, 'Honda Head Phát Tiến',  'Bảo dưỡng định kỳ'),
  ('59X1-123.45', '2026-06-05', 11300, 'Honda Head Phát Tiến',  NULL),
  ('59X1-123.45', '2026-08-20', 12500, 'Honda Head Phát Tiến',  'Thay nhớt, kiểm tra phanh'),
  ('51H-678.90',  '2026-02-18', 40100, 'Toyota Lý Thường Kiệt', 'Bảo dưỡng cấp 40.000 km'),
  ('51H-678.90',  '2026-08-02', 44800, 'Toyota Lý Thường Kiệt', NULL),
  ('59P2-456.78', '2026-07-12', 19800, 'Tiệm sửa xe Minh',      NULL)
) AS x(plate, service_date, odometer, garage_name, note)
JOIN vehicles v ON v.license_plate = x.plate
ON CONFLICT (vehicle_id, service_date, odometer) DO NOTHING;

-- -------------------------------------------------------------
-- Hạng mục (tìm lần bảo dưỡng theo biển số + ngày + ODO)
-- -------------------------------------------------------------
INSERT INTO maintenance_items (record_id, service_type_id, description, quantity, unit_price)
SELECT r.id, st.id, x.description, x.quantity, x.unit_price
FROM (VALUES
  ('59X1-123.45', '2026-03-10',  9800, 'Thay nhớt máy (xe máy)',       'Nhớt Honda 0.8L',              1, 120000),
  ('59X1-123.45', '2026-03-10',  9800, 'Thay nhớt hộp số (xe tay ga)', 'Nhớt hộp số 120ml',            1, 40000),
  ('59X1-123.45', '2026-03-10',  9800, 'Thay lọc gió',                 'Lọc gió Honda chính hãng',     1, 95000),
  ('59X1-123.45', '2026-06-05', 11300, 'Thay nhớt máy (xe máy)',       'Nhớt Castrol Power1 0.8L',     1, 135000),
  ('59X1-123.45', '2026-08-20', 12500, 'Thay nhớt máy (xe máy)',       'Nhớt Castrol Power1 0.8L',     1, 135000),
  ('59X1-123.45', '2026-08-20', 12500, 'Bảo dưỡng phanh',              'Má phanh trước',               1, 180000),
  ('51H-678.90',  '2026-02-18', 40100, 'Thay dầu động cơ (ô tô)',      'Dầu Toyota 0W-20',             4, 210000),
  ('51H-678.90',  '2026-02-18', 40100, 'Thay dầu động cơ (ô tô)',      'Lọc dầu',                      1, 150000),
  ('51H-678.90',  '2026-02-18', 40100, 'Thay lọc gió',                 'Lọc gió động cơ',              1, 320000),
  ('51H-678.90',  '2026-02-18', 40100, 'Bảo dưỡng định kỳ tổng quát',  'Công bảo dưỡng cấp 40.000 km', 1, 650000),
  ('51H-678.90',  '2026-08-02', 44800, 'Thay dầu động cơ (ô tô)',      'Dầu Toyota 0W-20',             4, 210000),
  ('51H-678.90',  '2026-08-02', 44800, 'Thay dầu động cơ (ô tô)',      'Lọc dầu',                      1, 150000),
  ('59P2-456.78', '2026-07-12', 19800, 'Thay nhớt máy (xe máy)',       'Nhớt Motul 0.8L',              1, 125000),
  ('59P2-456.78', '2026-07-12', 19800, 'Vệ sinh nồi / dây curoa',      'Vệ sinh nồi',                  1, 100000)
) AS x(plate, service_date, odometer, service_type, description, quantity, unit_price)
JOIN vehicles v            ON v.license_plate = x.plate
JOIN maintenance_records r ON r.vehicle_id = v.id
                          AND r.service_date = x.service_date::date
                          AND r.odometer = x.odometer
JOIN service_types st      ON st.name = x.service_type
WHERE NOT EXISTS (
  SELECT 1 FROM maintenance_items i
  WHERE i.record_id = r.id AND i.description = x.description
);

-- -------------------------------------------------------------
-- Nhắc lịch (mốc đến hạn được view v_reminder_status tự tính)
-- -------------------------------------------------------------
INSERT INTO reminders (vehicle_id, service_type_id, interval_km, interval_months, start_date, start_odometer)
SELECT v.id, st.id, x.interval_km, x.interval_months, x.start_date::date, x.start_odometer
FROM (VALUES
  ('59X1-123.45', 'Thay nhớt máy (xe máy)',      1500,  2,  '2026-01-01', 8000),
  ('59X1-123.45', 'Thay lọc gió',                10000, 12, '2026-01-01', 8000),
  ('51H-678.90',  'Thay dầu động cơ (ô tô)',     5000,  6,  '2026-01-01', 38000),
  ('51H-678.90',  'Bảo dưỡng định kỳ tổng quát', 10000, 6,  '2026-01-01', 38000),
  ('59P2-456.78', 'Thay nhớt máy (xe máy)',      1500,  2,  '2026-01-01', 18000)
) AS x(plate, service_type, interval_km, interval_months, start_date, start_odometer)
JOIN vehicles v       ON v.license_plate = x.plate
JOIN service_types st ON st.name = x.service_type
ON CONFLICT (vehicle_id, service_type_id) DO NOTHING;

-- -------------------------------------------------------------
-- Lịch sử chẩn đoán AI: 1 lần thành công, 1 lần bị 429
-- -------------------------------------------------------------
INSERT INTO diagnoses (vehicle_id, symptom_text, status, ai_suggestion, urgency_level, suggested_service_type_id, error_code, model, created_at)
SELECT v.id, x.symptom_text, x.status, x.ai_suggestion, x.urgency_level, st.id, x.error_code, x.model, x.created_at::timestamptz
FROM (VALUES
  ('59X1-123.45', 'Phanh trước kêu rít khi bóp mạnh, tay phanh hơi sâu', 'OK',
   'Má phanh trước có thể đã mòn hoặc bám bẩn. Nên kiểm tra độ dày má phanh và dầu phanh trong tuần này.',
   'MEDIUM', 'Bảo dưỡng phanh', NULL, 'gemini-flash', '2026-10-15 09:30:00+07'),
  ('51H-678.90',  'Đèn báo kiểm tra động cơ sáng sau khi đổ xăng', 'FAILED',
   NULL, NULL, NULL, 'RATE_LIMITED', 'gemini-flash', '2026-10-16 20:05:00+07')
) AS x(plate, symptom_text, status, ai_suggestion, urgency_level, service_type, error_code, model, created_at)
JOIN vehicles v ON v.license_plate = x.plate
LEFT JOIN service_types st ON st.name = x.service_type
WHERE NOT EXISTS (
  SELECT 1 FROM diagnoses d WHERE d.symptom_text = x.symptom_text AND d.created_at = x.created_at::timestamptz
);
