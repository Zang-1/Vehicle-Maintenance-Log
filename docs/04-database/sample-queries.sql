-- Các truy vấn chính của ứng dụng (PostgreSQL).
-- Tham số viết theo kiểu psycopg: %(ten)s. Backend truyền giá trị riêng, không ghép chuỗi (NFR-02), ví dụ:
--   conn.execute(QUERY, {"vehicle_id": 1, "from_date": "2026-01-01", "to_date": "2026-12-31"})

-- FR-02: danh sách xe đang dùng + số nhắc lịch cần chú ý
SELECT v.id, v.name, v.vehicle_type, v.license_plate, v.current_odometer,
       count(*) FILTER (WHERE s.is_active AND s.status <> 'OK') AS attention_count
FROM vehicles v
LEFT JOIN v_reminder_status s ON s.vehicle_id = v.id
WHERE NOT v.is_archived
GROUP BY v.id
ORDER BY v.name;

-- FR-07: lịch sử bảo dưỡng của một xe trong khoảng ngày
SELECT record_id, service_date, odometer, garage_name, item_count, total_cost
FROM v_record_totals
WHERE vehicle_id = %(vehicle_id)s
  AND service_date BETWEEN %(from_date)s AND %(to_date)s
ORDER BY service_date DESC, record_id DESC;

-- FR-08: các hạng mục của một lần bảo dưỡng
SELECT i.id, st.name AS service_type_name, i.description, i.quantity, i.unit_price, i.line_total
FROM maintenance_items i
JOIN service_types st ON st.id = i.service_type_id
WHERE i.record_id = %(record_id)s
ORDER BY i.id;

-- FR-06: ghi nhận lần bảo dưỡng = 1 transaction (with conn.transaction(): ...)
--   1) INSERT lần bảo dưỡng, lấy id
INSERT INTO maintenance_records (vehicle_id, service_date, odometer, garage_name, note)
VALUES (%(vehicle_id)s, %(service_date)s, %(odometer)s, %(garage_name)s, %(note)s)
RETURNING id;
--   2) INSERT từng hạng mục (executemany)
INSERT INTO maintenance_items (record_id, service_type_id, description, quantity, unit_price)
VALUES (%(record_id)s, %(service_type_id)s, %(description)s, %(quantity)s, %(unit_price)s);
--   3) BR-02: nâng ODO của xe nếu ODO lần bảo dưỡng lớn hơn
UPDATE vehicles SET current_odometer = %(odometer)s
WHERE id = %(vehicle_id)s AND current_odometer < %(odometer)s;
--   Nhắc lịch không cần cập nhật: v_reminder_status tự lấy lần làm gần nhất (FR-15)

-- FR-14, FR-16: nhắc lịch quá hạn / sắp đến hạn (Dashboard)
SELECT reminder_id, vehicle_name, service_type_name, next_due_date, next_due_odometer,
       days_left, km_left, status
FROM v_reminder_status
WHERE is_active AND status <> 'OK'
ORDER BY (status = 'OVERDUE') DESC, days_left NULLS LAST, km_left NULLS LAST;

-- FR-16: chi phí tháng hiện tại
SELECT coalesce(sum(total_cost), 0) AS cost_this_month
FROM v_record_totals
WHERE service_date >= date_trunc('month', current_date);

-- FR-17: chi phí theo tháng
SELECT to_char(service_date, 'YYYY-MM') AS month, sum(total_cost) AS total_cost
FROM v_record_totals
WHERE service_date BETWEEN %(from_date)s AND %(to_date)s
GROUP BY 1
ORDER BY 1;

-- FR-17: chi phí theo loại dịch vụ
SELECT st.name AS service_type_name, sum(i.line_total) AS total_cost
FROM maintenance_items i
JOIN maintenance_records r ON r.id = i.record_id
JOIN service_types st      ON st.id = i.service_type_id
WHERE r.service_date BETWEEN %(from_date)s AND %(to_date)s
GROUP BY st.id
ORDER BY total_cost DESC;

-- FR-18 -> FR-21: lưu kết quả một lần chẩn đoán (thành công hoặc lỗi)
INSERT INTO diagnoses (vehicle_id, symptom_text, status, ai_suggestion, urgency_level,
                       suggested_service_type_id, error_code, model)
VALUES (%(vehicle_id)s, %(symptom_text)s, %(status)s, %(ai_suggestion)s, %(urgency_level)s,
        %(suggested_service_type_id)s, %(error_code)s, %(model)s)
RETURNING id, created_at;

-- FR-21: lịch sử chẩn đoán gần nhất
SELECT d.id, d.created_at, v.name AS vehicle_name, d.symptom_text, d.status,
       d.urgency_level, d.ai_suggestion, d.error_code
FROM diagnoses d
LEFT JOIN vehicles v ON v.id = d.vehicle_id
ORDER BY d.created_at DESC
LIMIT 20;

-- /health/db: chứng minh app với tới database
SELECT count(*) FROM vehicles;
