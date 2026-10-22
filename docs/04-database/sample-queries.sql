-- =============================================================
-- Vehicle Maintenance Log - Các truy vấn chính của ứng dụng
-- Tham số dạng :ten_tham_so sẽ được truyền từ backend (truy vấn tham số hóa, NFR-03)
-- =============================================================

USE vehicle_maintenance;

-- FR-06: danh sách xe đang dùng + số nhắc lịch cần chú ý
SELECT v.vehicle_id, v.name, v.vehicle_type, v.license_plate, v.current_odometer, v.image_url,
       COUNT(CASE WHEN s.is_active AND s.status <> 'OK' THEN 1 END) AS attention_count
FROM vehicles v
LEFT JOIN v_reminder_status s ON s.vehicle_id = v.vehicle_id
WHERE v.user_id = :user_id AND v.is_archived = FALSE
GROUP BY v.vehicle_id, v.name, v.vehicle_type, v.license_plate, v.current_odometer, v.image_url
ORDER BY v.name;

-- FR-12: lịch sử bảo dưỡng của một xe, lọc theo khoảng ngày và loại dịch vụ (tùy chọn)
SELECT t.record_id, t.service_date, t.odometer, g.name AS garage_name, t.item_count, t.total_cost
FROM v_record_totals t
LEFT JOIN garages g ON g.garage_id = t.garage_id
WHERE t.vehicle_id = :vehicle_id
  AND t.user_id = :user_id                                   -- chỉ xem dữ liệu của mình (NFR-02)
  AND t.service_date BETWEEN :from_date AND :to_date
  AND (:service_type_id IS NULL OR EXISTS (
        SELECT 1 FROM maintenance_items i
        WHERE i.record_id = t.record_id AND i.service_type_id = :service_type_id))
ORDER BY t.service_date DESC, t.record_id DESC;

-- FR-13: chi tiết các hạng mục của một lần bảo dưỡng
SELECT i.item_id, st.name AS service_type_name, i.description, i.quantity, i.unit_price, i.line_total
FROM maintenance_items i
JOIN service_types st ON st.service_type_id = i.service_type_id
WHERE i.record_id = :record_id
ORDER BY i.item_id;

-- FR-20: sau khi lưu lần bảo dưỡng, tính lại mốc cho các nhắc lịch có loại dịch vụ trùng (BR-08)
-- Chỉ cập nhật khi lần bảo dưỡng mới hơn mốc hiện tại; đặt lại last_notified_level (BR-10)
UPDATE reminders rm
JOIN maintenance_records r ON r.vehicle_id = rm.vehicle_id
JOIN maintenance_items i   ON i.record_id = r.record_id AND i.service_type_id = rm.service_type_id
SET rm.last_service_date     = r.service_date,
    rm.last_service_odometer = r.odometer,
    rm.next_due_date         = IF(rm.interval_months IS NULL, NULL, DATE_ADD(r.service_date, INTERVAL rm.interval_months MONTH)),
    rm.next_due_odometer     = IF(rm.interval_km IS NULL, NULL, r.odometer + rm.interval_km),
    rm.last_notified_level   = 'NONE'
WHERE r.record_id = :record_id
  AND r.service_date >= rm.last_service_date;

-- BR-03: cập nhật ODO của xe nếu ODO lần bảo dưỡng lớn hơn
UPDATE vehicles v
JOIN maintenance_records r ON r.vehicle_id = v.vehicle_id
SET v.current_odometer = r.odometer
WHERE r.record_id = :record_id AND r.odometer > v.current_odometer;

-- FR-21: tiến trình nhắc lịch hằng ngày - tìm nhắc lịch cần sinh thông báo mới
-- (trạng thái hiện tại "nặng" hơn mức đã thông báo, BR-10)
SELECT s.reminder_id, s.user_id, s.vehicle_name, s.service_type_name,
       s.next_due_date, s.next_due_odometer, s.days_left, s.km_left, s.status
FROM v_reminder_status s
JOIN users u ON u.user_id = s.user_id
WHERE s.is_active = TRUE
  AND u.is_active = TRUE
  AND (   (s.status = 'DUE_SOON' AND s.last_notified_level = 'NONE')
       OR (s.status = 'OVERDUE'  AND s.last_notified_level IN ('NONE', 'DUE_SOON')));
-- Với mỗi dòng: INSERT INTO notifications (...) rồi
-- UPDATE reminders SET last_notified_level = :status WHERE reminder_id = :reminder_id;

-- FR-22: số thông báo chưa đọc (biểu tượng chuông)
SELECT COUNT(*) AS unread_count
FROM notifications
WHERE user_id = :user_id AND is_read = FALSE;

-- FR-24: chi phí tháng hiện tại
SELECT COALESCE(SUM(total_cost), 0) AS cost_this_month
FROM v_record_totals
WHERE user_id = :user_id
  AND service_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01');

-- FR-25: chi phí theo tháng trong khoảng thời gian
SELECT DATE_FORMAT(service_date, '%Y-%m') AS month, SUM(total_cost) AS total_cost
FROM v_record_totals
WHERE user_id = :user_id AND service_date BETWEEN :from_date AND :to_date
GROUP BY DATE_FORMAT(service_date, '%Y-%m')
ORDER BY month;

-- FR-25: chi phí theo loại dịch vụ
SELECT st.name AS service_type_name, SUM(i.line_total) AS total_cost
FROM maintenance_items i
JOIN maintenance_records r ON r.record_id = i.record_id
JOIN vehicles v            ON v.vehicle_id = r.vehicle_id
JOIN service_types st      ON st.service_type_id = i.service_type_id
WHERE v.user_id = :user_id AND r.service_date BETWEEN :from_date AND :to_date
GROUP BY st.service_type_id, st.name
ORDER BY total_cost DESC;

-- FR-28: thống kê hệ thống cho quản trị viên
SELECT
    (SELECT COUNT(*) FROM users WHERE role = 'USER')            AS user_count,
    (SELECT COUNT(*) FROM vehicles WHERE is_archived = FALSE)   AS vehicle_count,
    (SELECT COUNT(*) FROM maintenance_records
      WHERE service_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')) AS records_this_month;
