-- =============================================================
-- Vehicle Maintenance Log - Database schema
-- Hệ quản trị: MySQL 8.0+
-- Người phụ trách: Giang (bước 04 - ERD & Database Design)
-- =============================================================

DROP DATABASE IF EXISTS vehicle_maintenance;
CREATE DATABASE vehicle_maintenance
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE vehicle_maintenance;

-- -------------------------------------------------------------
-- Tài khoản (FR-01 -> FR-04, FR-27)
-- -------------------------------------------------------------
CREATE TABLE users (
    user_id                 INT             NOT NULL AUTO_INCREMENT,
    full_name               VARCHAR(100)    NOT NULL,
    email                   VARCHAR(255)    NOT NULL,
    password_hash           VARCHAR(255)    NOT NULL,
    phone                   VARCHAR(20)     NULL,
    role                    ENUM('USER', 'ADMIN') NOT NULL DEFAULT 'USER',
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    email_reminder_enabled  BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT uq_users_email UNIQUE (email)                          -- BR-01
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Xe (FR-05 -> FR-10)
-- -------------------------------------------------------------
CREATE TABLE vehicles (
    vehicle_id          INT             NOT NULL AUTO_INCREMENT,
    user_id             INT             NOT NULL,
    name                VARCHAR(100)    NOT NULL,
    vehicle_type        ENUM('MOTORBIKE', 'CAR', 'OTHER') NOT NULL,
    brand               VARCHAR(50)     NULL,
    model               VARCHAR(50)     NULL,
    manufacture_year    SMALLINT        NULL,
    license_plate       VARCHAR(20)     NULL,
    vin                 VARCHAR(30)     NULL,
    current_odometer    INT             NOT NULL DEFAULT 0,
    purchase_date       DATE            NULL,
    image_url           VARCHAR(500)    NULL,
    is_archived         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (vehicle_id),
    CONSTRAINT fk_vehicles_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT uq_vehicles_user_plate UNIQUE (user_id, license_plate), -- BR-02 (NULL được phép trùng)
    CONSTRAINT ck_vehicles_year CHECK (manufacture_year IS NULL OR manufacture_year BETWEEN 1950 AND 2100),
    CONSTRAINT ck_vehicles_odometer CHECK (current_odometer >= 0),
    INDEX ix_vehicles_user_archived (user_id, is_archived)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Danh mục loại dịch vụ (FR-26)
-- -------------------------------------------------------------
CREATE TABLE service_types (
    service_type_id         INT             NOT NULL AUTO_INCREMENT,
    name                    VARCHAR(100)    NOT NULL,
    description             VARCHAR(255)    NULL,
    applies_to              ENUM('MOTORBIKE', 'CAR', 'ALL') NOT NULL DEFAULT 'ALL',
    default_interval_km     INT             NULL,
    default_interval_months INT             NULL,
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,    -- BR-14
    PRIMARY KEY (service_type_id),
    CONSTRAINT uq_service_types_name UNIQUE (name),
    CONSTRAINT ck_service_types_km CHECK (default_interval_km IS NULL OR default_interval_km > 0),
    CONSTRAINT ck_service_types_months CHECK (default_interval_months IS NULL OR default_interval_months > 0)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Garage hay dùng (FR-16)
-- -------------------------------------------------------------
CREATE TABLE garages (
    garage_id   INT             NOT NULL AUTO_INCREMENT,
    user_id     INT             NOT NULL,
    name        VARCHAR(100)    NOT NULL,
    address     VARCHAR(255)    NULL,
    phone       VARCHAR(20)     NULL,
    note        VARCHAR(255)    NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (garage_id),
    CONSTRAINT fk_garages_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Lần bảo dưỡng (FR-11 -> FR-14)
-- -------------------------------------------------------------
CREATE TABLE maintenance_records (
    record_id       INT             NOT NULL AUTO_INCREMENT,
    vehicle_id      INT             NOT NULL,
    garage_id       INT             NULL,
    service_date    DATE            NOT NULL,                         -- BR-04 kiểm tra ở tầng ứng dụng
    odometer        INT             NOT NULL,
    note            VARCHAR(500)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    CONSTRAINT fk_records_vehicle FOREIGN KEY (vehicle_id)
        REFERENCES vehicles (vehicle_id) ON DELETE RESTRICT,          -- BR-12
    CONSTRAINT fk_records_garage FOREIGN KEY (garage_id)
        REFERENCES garages (garage_id) ON DELETE SET NULL,
    CONSTRAINT ck_records_odometer CHECK (odometer >= 0),
    INDEX ix_records_vehicle_date (vehicle_id, service_date)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Hạng mục trong lần bảo dưỡng (FR-11, FR-13)
-- -------------------------------------------------------------
CREATE TABLE maintenance_items (
    item_id         INT             NOT NULL AUTO_INCREMENT,
    record_id       INT             NOT NULL,
    service_type_id INT             NOT NULL,
    description     VARCHAR(255)    NULL,
    quantity        DECIMAL(8, 2)   NOT NULL DEFAULT 1,
    unit_price      DECIMAL(12, 0)  NOT NULL DEFAULT 0,
    line_total      DECIMAL(14, 0)  AS (ROUND(quantity * unit_price)) STORED, -- BR-06
    PRIMARY KEY (item_id),
    CONSTRAINT fk_items_record FOREIGN KEY (record_id)
        REFERENCES maintenance_records (record_id) ON DELETE CASCADE,
    CONSTRAINT fk_items_service_type FOREIGN KEY (service_type_id)
        REFERENCES service_types (service_type_id) ON DELETE RESTRICT, -- BR-14
    CONSTRAINT ck_items_quantity CHECK (quantity > 0),
    CONSTRAINT ck_items_unit_price CHECK (unit_price >= 0)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Hóa đơn đính kèm (FR-15)
-- -------------------------------------------------------------
CREATE TABLE attachments (
    attachment_id   INT             NOT NULL AUTO_INCREMENT,
    record_id       INT             NOT NULL,
    file_name       VARCHAR(255)    NOT NULL,
    file_path       VARCHAR(500)    NOT NULL,
    mime_type       VARCHAR(50)     NOT NULL,
    file_size_bytes INT             NOT NULL,
    uploaded_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attachment_id),
    CONSTRAINT fk_attachments_record FOREIGN KEY (record_id)
        REFERENCES maintenance_records (record_id) ON DELETE CASCADE,
    CONSTRAINT ck_attachments_mime CHECK (mime_type IN ('image/jpeg', 'image/png', 'application/pdf')),
    CONSTRAINT ck_attachments_size CHECK (file_size_bytes BETWEEN 1 AND 5242880) -- NFR-08
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Nhắc lịch (FR-18 -> FR-20)
-- -------------------------------------------------------------
CREATE TABLE reminders (
    reminder_id             INT         NOT NULL AUTO_INCREMENT,
    vehicle_id              INT         NOT NULL,
    service_type_id         INT         NOT NULL,
    interval_km             INT         NULL,
    interval_months         INT         NULL,
    last_service_date       DATE        NOT NULL,
    last_service_odometer   INT         NOT NULL,
    next_due_date           DATE        NULL,
    next_due_odometer       INT         NULL,
    notify_before_days      INT         NOT NULL DEFAULT 7,
    notify_before_km        INT         NOT NULL DEFAULT 300,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    last_notified_level     ENUM('NONE', 'DUE_SOON', 'OVERDUE') NOT NULL DEFAULT 'NONE', -- BR-10
    created_at              DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (reminder_id),
    CONSTRAINT fk_reminders_vehicle FOREIGN KEY (vehicle_id)
        REFERENCES vehicles (vehicle_id) ON DELETE CASCADE,
    CONSTRAINT fk_reminders_service_type FOREIGN KEY (service_type_id)
        REFERENCES service_types (service_type_id) ON DELETE RESTRICT,
    CONSTRAINT uq_reminders_vehicle_service UNIQUE (vehicle_id, service_type_id), -- BR-11
    CONSTRAINT ck_reminders_interval CHECK (interval_km IS NOT NULL OR interval_months IS NOT NULL), -- BR-07
    CONSTRAINT ck_reminders_km CHECK (interval_km IS NULL OR interval_km > 0),
    CONSTRAINT ck_reminders_months CHECK (interval_months IS NULL OR interval_months > 0),
    CONSTRAINT ck_reminders_notify CHECK (notify_before_days >= 0 AND notify_before_km >= 0),
    INDEX ix_reminders_active_due (is_active, next_due_date)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- Thông báo (FR-21 -> FR-23)
-- -------------------------------------------------------------
CREATE TABLE notifications (
    notification_id INT             NOT NULL AUTO_INCREMENT,
    user_id         INT             NOT NULL,
    reminder_id     INT             NULL,
    type            ENUM('DUE_SOON', 'OVERDUE', 'SYSTEM') NOT NULL,
    title           VARCHAR(150)    NOT NULL,
    message         VARCHAR(500)    NOT NULL,
    is_read         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at         DATETIME        NULL,
    PRIMARY KEY (notification_id),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_reminder FOREIGN KEY (reminder_id)
        REFERENCES reminders (reminder_id) ON DELETE SET NULL,
    INDEX ix_notifications_user_unread (user_id, is_read, created_at)
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- View: tổng chi phí mỗi lần bảo dưỡng (BR-06)
-- -------------------------------------------------------------
CREATE VIEW v_record_totals AS
SELECT
    r.record_id,
    r.vehicle_id,
    v.user_id,
    r.garage_id,
    r.service_date,
    r.odometer,
    r.note,
    COUNT(i.item_id)                AS item_count,
    COALESCE(SUM(i.line_total), 0)  AS total_cost
FROM maintenance_records r
JOIN vehicles v               ON v.vehicle_id = r.vehicle_id
LEFT JOIN maintenance_items i ON i.record_id = r.record_id
GROUP BY r.record_id, r.vehicle_id, v.user_id, r.garage_id, r.service_date, r.odometer, r.note;

-- -------------------------------------------------------------
-- View: trạng thái nhắc lịch (BR-07, BR-09)
--   OVERDUE  : đã qua mốc ngày hoặc mốc km
--   DUE_SOON : còn <= notify_before_days ngày hoặc <= notify_before_km km
--   OK       : còn lại
-- -------------------------------------------------------------
CREATE VIEW v_reminder_status AS
SELECT
    rm.reminder_id,
    rm.vehicle_id,
    v.user_id,
    v.name                                  AS vehicle_name,
    rm.service_type_id,
    st.name                                 AS service_type_name,
    rm.interval_km,
    rm.interval_months,
    rm.next_due_date,
    rm.next_due_odometer,
    v.current_odometer,
    DATEDIFF(rm.next_due_date, CURDATE())   AS days_left,
    rm.next_due_odometer - v.current_odometer AS km_left,
    rm.is_active,
    rm.last_notified_level,
    CASE
        WHEN rm.next_due_date <= CURDATE()
          OR rm.next_due_odometer <= v.current_odometer THEN 'OVERDUE'
        WHEN DATEDIFF(rm.next_due_date, CURDATE()) <= rm.notify_before_days
          OR rm.next_due_odometer - v.current_odometer <= rm.notify_before_km THEN 'DUE_SOON'
        ELSE 'OK'
    END                                     AS status
FROM reminders rm
JOIN vehicles v       ON v.vehicle_id = rm.vehicle_id
JOIN service_types st ON st.service_type_id = rm.service_type_id;
