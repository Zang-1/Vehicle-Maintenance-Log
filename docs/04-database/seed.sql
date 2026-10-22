-- =============================================================
-- Vehicle Maintenance Log - Dữ liệu mẫu
-- Chạy sau schema.sql
-- =============================================================

USE vehicle_maintenance;

-- -------------------------------------------------------------
-- Tài khoản
-- password_hash dưới đây chỉ là chuỗi giữ chỗ, KHÔNG đăng nhập được.
-- Khi có backend: đăng ký tài khoản qua ứng dụng (mật khẩu sẽ được băm bcrypt),
-- rồi cấp quyền quản trị bằng: UPDATE users SET role = 'ADMIN' WHERE email = '...';
-- -------------------------------------------------------------
INSERT INTO users (user_id, full_name, email, password_hash, phone, role, email_reminder_enabled) VALUES
(1, 'Quản trị viên', 'admin@vml.local', '$2b$10$PLACEHOLDER.HASH.REPLACE.BY.APP.000000000000000000', NULL,         'ADMIN', FALSE),
(2, 'Nguyễn Văn An', 'an@vml.local',    '$2b$10$PLACEHOLDER.HASH.REPLACE.BY.APP.000000000000000000', '0901234567', 'USER',  TRUE),
(3, 'Trần Thị Bình', 'binh@vml.local',  '$2b$10$PLACEHOLDER.HASH.REPLACE.BY.APP.000000000000000000', NULL,         'USER',  FALSE);

-- -------------------------------------------------------------
-- Danh mục loại dịch vụ (chu kỳ tham khảo phổ biến)
-- -------------------------------------------------------------
INSERT INTO service_types (service_type_id, name, description, applies_to, default_interval_km, default_interval_months) VALUES
(1,  'Thay nhớt máy (xe máy)',    'Thay dầu động cơ xe máy',                  'MOTORBIKE', 1500,  2),
(2,  'Thay nhớt hộp số (xe tay ga)', 'Thay dầu láp/hộp số cho xe tay ga',     'MOTORBIKE', 6000,  6),
(3,  'Thay dầu động cơ (ô tô)',   'Thay dầu máy và lọc dầu',                  'CAR',       5000,  6),
(4,  'Thay lọc gió',              'Vệ sinh hoặc thay lọc gió động cơ',        'ALL',       10000, 12),
(5,  'Thay bugi',                 'Thay bugi đánh lửa',                       'ALL',       8000,  12),
(6,  'Bảo dưỡng phanh',           'Kiểm tra, thay má phanh/dầu phanh',        'ALL',       10000, 12),
(7,  'Thay lốp',                  'Thay lốp xe',                              'ALL',       30000, 36),
(8,  'Thay nước làm mát',         'Xả và thay nước làm mát',                  'CAR',       40000, 24),
(9,  'Thay ắc quy',               'Thay bình ắc quy',                         'ALL',       NULL,  24),
(10, 'Bảo dưỡng định kỳ tổng quát', 'Gói bảo dưỡng định kỳ theo khuyến nghị hãng', 'ALL',  10000, 6),
(11, 'Vệ sinh nồi / dây curoa',   'Vệ sinh bộ nồi, kiểm tra dây curoa xe tay ga', 'MOTORBIKE', 8000, 12),
(12, 'Sửa chữa khác',             'Các công việc sửa chữa không nằm trong danh mục', 'ALL', NULL, NULL);

-- -------------------------------------------------------------
-- Xe
-- -------------------------------------------------------------
INSERT INTO vehicles (vehicle_id, user_id, name, vehicle_type, brand, model, manufacture_year, license_plate, vin, current_odometer, purchase_date) VALUES
(1, 2, 'Vision đi làm',    'MOTORBIKE', 'Honda',  'Vision', 2022, '59X1-123.45', NULL,                 12850, '2022-03-15'),
(2, 2, 'Vios gia đình',    'CAR',       'Toyota', 'Vios',   2020, '51H-678.90',  'MR2B29F30L1234567', 45200, '2020-08-01'),
(3, 3, 'Air Blade',        'MOTORBIKE', 'Honda',  'Air Blade 125', 2021, '59P2-456.78', NULL,          20300, '2021-05-20');

-- -------------------------------------------------------------
-- Garage
-- -------------------------------------------------------------
INSERT INTO garages (garage_id, user_id, name, address, phone) VALUES
(1, 2, 'Honda Head Phát Tiến', '123 Nguyễn Văn Linh, Q.7, TP.HCM', '02838123456'),
(2, 2, 'Toyota Lý Thường Kiệt', '151 Lý Thường Kiệt, Q.Tân Bình, TP.HCM', '02838654321'),
(3, 3, 'Tiệm sửa xe Minh',      '45 Phan Văn Trị, Q.Gò Vấp, TP.HCM', NULL);

-- -------------------------------------------------------------
-- Lần bảo dưỡng + hạng mục
-- -------------------------------------------------------------
INSERT INTO maintenance_records (record_id, vehicle_id, garage_id, service_date, odometer, note) VALUES
(1, 1, 1, '2026-03-10', 9800,  'Bảo dưỡng định kỳ'),
(2, 1, 1, '2026-06-05', 11300, NULL),
(3, 1, 1, '2026-08-20', 12500, 'Thay nhớt, kiểm tra phanh'),
(4, 2, 2, '2026-02-18', 40100, 'Bảo dưỡng cấp 40.000 km'),
(5, 2, 2, '2026-08-02', 44800, NULL),
(6, 3, 3, '2026-07-12', 19800, NULL);

INSERT INTO maintenance_items (record_id, service_type_id, description, quantity, unit_price) VALUES
(1, 1,  'Nhớt Honda 0.8L',             1, 120000),
(1, 2,  'Nhớt hộp số 120ml',           1, 40000),
(1, 4,  'Lọc gió Honda chính hãng',    1, 95000),
(2, 1,  'Nhớt Castrol Power1 0.8L',    1, 135000),
(3, 1,  'Nhớt Castrol Power1 0.8L',    1, 135000),
(3, 6,  'Má phanh trước',              1, 180000),
(4, 3,  'Dầu Toyota 0W-20',            4, 210000),
(4, 3,  'Lọc dầu',                     1, 150000),
(4, 4,  'Lọc gió động cơ',             1, 320000),
(4, 10, 'Công bảo dưỡng cấp 40.000 km', 1, 650000),
(5, 3,  'Dầu Toyota 0W-20',            4, 210000),
(5, 3,  'Lọc dầu',                     1, 150000),
(6, 1,  'Nhớt Motul 0.8L',             1, 125000),
(6, 11, 'Vệ sinh nồi',                 1, 100000);

-- -------------------------------------------------------------
-- Nhắc lịch (next_due_* = last_service_* + chu kỳ, BR-08)
-- -------------------------------------------------------------
INSERT INTO reminders (reminder_id, vehicle_id, service_type_id, interval_km, interval_months,
                       last_service_date, last_service_odometer, next_due_date, next_due_odometer, last_notified_level) VALUES
(1, 1, 1,  1500,  2,  '2026-08-20', 12500, '2026-10-20', 14000, 'OVERDUE'),  -- quá hạn theo ngày
(2, 1, 4,  10000, 12, '2026-03-10', 9800,  '2027-03-10', 19800, 'NONE'),
(3, 2, 3,  5000,  6,  '2026-08-02', 44800, '2027-02-02', 49800, 'NONE'),
(4, 2, 10, 10000, 6,  '2026-02-18', 40100, '2026-08-18', 50100, 'OVERDUE'),  -- quá hạn theo ngày
(5, 3, 1,  1500,  2,  '2026-07-12', 19800, '2026-09-12', 21300, 'OVERDUE');

-- -------------------------------------------------------------
-- Thông báo
-- -------------------------------------------------------------
INSERT INTO notifications (user_id, reminder_id, type, title, message, is_read, created_at, read_at) VALUES
(2, 1, 'DUE_SOON', 'Sắp đến hạn thay nhớt', 'Xe "Vision đi làm" sắp đến hạn Thay nhớt máy (xe máy) vào 20/10/2026.', TRUE,  '2026-10-13 07:00:00', '2026-10-13 08:15:00'),
(2, 1, 'OVERDUE',  'Quá hạn thay nhớt',     'Xe "Vision đi làm" đã quá hạn Thay nhớt máy (xe máy) từ 20/10/2026.',   FALSE, '2026-10-20 07:00:00', NULL),
(2, 4, 'OVERDUE',  'Quá hạn bảo dưỡng định kỳ', 'Xe "Vios gia đình" đã quá hạn Bảo dưỡng định kỳ tổng quát từ 18/08/2026.', FALSE, '2026-08-18 07:00:00', NULL),
(3, 5, 'OVERDUE',  'Quá hạn thay nhớt',     'Xe "Air Blade" đã quá hạn Thay nhớt máy (xe máy) từ 12/09/2026.',       FALSE, '2026-09-12 07:00:00', NULL);
