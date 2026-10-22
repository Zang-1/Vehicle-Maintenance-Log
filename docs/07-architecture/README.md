# 07 – Architecture & Class Diagram

**Người phụ trách:** Lâm · **Phiên bản:** 1.0 · **Đầu vào:** [02 Use Case](../02-use-case/), [04 Database](../04-database/erd.md), [08 Implementation Plan](../08-implementation-plan/implementation-plan.md) (mục 1–3)

Tài liệu chốt công nghệ, mô tả kiến trúc phân tầng và các lớp chính của hệ thống. Tên lớp, tên hàm ở đây là tên sẽ dùng trong code (tài liệu 08, mục 2).

## 1. Công nghệ chốt

Giữ nguyên bản đề xuất ở mục 1 tài liệu 08, bổ sung thư viện cụ thể cho từng việc:

| Tầng | Công nghệ | Thư viện chính | Ghi chú |
|---|---|---|---|
| Presentation | ReactJS 18 + Vite | `react-router-dom`, `axios`, `chart.js` + `react-chartjs-2` | SPA, gọi REST API, lưu JWT trong `localStorage` |
| Business + Data Access | Node.js 20 LTS + Express 4 | `jsonwebtoken`, `bcrypt`, `express-validator`, `multer`, `mysql2/promise`, `node-cron`, `dotenv`, `cors` | REST API trả JSON |
| Database | MySQL 8.0 | – | Script ở [tài liệu 04](../04-database/schema.sql) |
| Lưu file | Ổ đĩa server, thư mục `uploads/` | `multer` | Ảnh xe, hóa đơn; không commit lên Git |
| Email (Could) | SMTP | `nodemailer` | Chỉ làm nếu kịp FR-23 |
| Kiểm thử | Jest + Supertest (BE), Vitest + React Testing Library (FE) | – | Như mục 5 tài liệu 08 |

Lý do không dùng ORM (Sequelize, Prisma): schema đã viết sẵn bằng SQL ở tài liệu 04, có view và cột sinh tự động; viết truy vấn tham số hóa bằng `mysql2` vừa đủ chống SQL Injection (NFR-03), vừa ít thứ phải học.

## 2. Sơ đồ kiến trúc phân tầng

```mermaid
flowchart TB
    Browser["Trình duyệt<br/>Chrome / Edge / Firefox"]

    subgraph P["Presentation – ReactJS SPA"]
        direction LR
        Pages["pages/<br/>S01 → S15"]
        Comp["components/ · layouts/<br/>theo Figma"]
        Ctx["contexts/ · hooks/<br/>AuthContext, useNotifications"]
        Api["api/<br/>Axios + gắn JWT"]
    end

    subgraph B["Backend – Node.js + Express"]
        direction TB
        Routes["Routes + Middlewares<br/>auth · requireAdmin · validate · upload · errorHandler"]
        Ctrl["Controllers<br/>nhận request, trả response"]
        Svc["Services – Business layer<br/>quy tắc nghiệp vụ BR-xx, giao dịch"]
        Repo["Repositories – Data Access layer<br/>truy vấn SQL tham số hóa"]
        Job["Jobs<br/>ReminderJob · node-cron 07:00"]
    end

    subgraph D["Database & lưu trữ"]
        direction LR
        DB[("MySQL 8.0<br/>9 bảng + 2 view")]
        Files[("uploads/<br/>ảnh xe, hóa đơn")]
        SMTP["SMTP server<br/>(Could)"]
    end

    Browser --> P
    Api -- "HTTPS · REST/JSON<br/>Authorization: Bearer JWT" --> Routes
    Routes --> Ctrl --> Svc --> Repo --> DB
    Job --> Svc
    Svc -- "lưu / xóa file" --> Files
    Svc -. "gửi email" .-> SMTP

    classDef layer fill:#eef6ff,stroke:#1f6feb,color:#0b2a55
    class Pages,Comp,Ctx,Api,Routes,Ctrl,Svc,Repo,Job layer
```

**Quy tắc phụ thuộc giữa các tầng**
- Mỗi tầng chỉ gọi tầng ngay dưới nó: Controller → Service → Repository. Controller **không** gọi thẳng Repository; Repository **không** chứa quy tắc nghiệp vụ.
- Service của module này muốn dùng dữ liệu module khác thì gọi **Service** của module đó (ví dụ `MaintenanceService` gọi `VehicleService.getOwnedVehicle`), không gọi Repository của module khác. Đây là các "hợp đồng giữa các module" ở mục 3 tài liệu 08.
- Kiểm tra quyền sở hữu dữ liệu (NFR-02) nằm ở **Service**, vì Service nào cũng nhận `userId` từ `req.user`.
- Giao dịch database do Service mở (`Database.withTransaction`), Repository chỉ nhận `conn` và chạy câu lệnh.

## 3. Luồng xử lý một request

Ví dụ ghi nhận lần bảo dưỡng (UC-12, `POST /api/vehicles/:id/records`) đi qua đủ các tầng và gọi chéo sang module M2, M6:

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant FE as React (S07)
    participant MW as Middlewares
    participant C as MaintenanceController
    participant S as MaintenanceService
    participant VS as VehicleService
    participant RS as ReminderService
    participant R as Repositories
    participant DB as MySQL

    U->>FE: Nhập phiếu, bấm Lưu
    FE->>MW: POST /api/vehicles/1/records (JWT, JSON)
    MW->>MW: auth: giải mã JWT → req.user
    MW->>MW: validate: kiểu dữ liệu, bắt buộc
    MW->>C: create(req, res)
    C->>S: createRecord(userId, vehicleId, dto)
    S->>VS: getOwnedVehicle(userId, vehicleId)
    VS-->>S: vehicle (hoặc NotFoundError → 404)
    S->>S: validateRecord(dto): BR-04, BR-05, BR-06
    S->>DB: BEGIN
    S->>R: recordRepo.create(record, conn)
    S->>R: itemRepo.createMany(recordId, items, conn)
    S->>VS: raiseOdometerIfHigher(vehicleId, odometer, conn)
    S->>RS: onMaintenanceSaved(recordId, conn)
    RS->>R: tìm nhắc lịch trùng loại dịch vụ, cập nhật mốc
    S->>DB: COMMIT
    S-->>C: record + totalCost
    C-->>FE: 201 Created (JSON)
    FE-->>U: Mở chi tiết lần bảo dưỡng
    Note over S,DB: Lỗi ở bất kỳ bước nào → ROLLBACK,<br/>errorHandler trả 400 / 404 / 500
```

## 4. Class diagram

Class diagram chia làm 7 phần cho dễ đọc. Mỗi module backend có bộ ba **Controller – Service – Repository**, đặt trong `backend/src/modules/<module>/` với tên file `*.controller.js`, `*.service.js`, `*.repository.js`. Mỗi file export **một đối tượng duy nhất** của lớp (ví dụ `module.exports = new VehicleService()`), nên trong code gọi là `vehicleService.getOwnedVehicle(...)` như ở tài liệu 08.

Quy ước kiểu: `number`, `string`, `boolean`, `Date` là kiểu JavaScript; `Promise~T~` là hàm bất đồng bộ trả về `T`; `conn` là kết nối đang trong giao dịch (có thể bỏ trống khi không cần giao dịch).

### 4.1. Entity (mô hình dữ liệu)

Mỗi entity tương ứng một bảng ở tài liệu 04; thuộc tính viết `camelCase` trong JavaScript, Repository đổi sang tên cột `snake_case`. Entity chỉ là đối tượng dữ liệu, không truy cập database.

```mermaid
classDiagram
    direction LR

    class User {
        +userId: number
        +fullName: string
        +email: string
        +passwordHash: string
        +phone: string
        +role: Role
        +isActive: boolean
        +emailReminderEnabled: boolean
        +createdAt: Date
        +updatedAt: Date
    }
    class Vehicle {
        +vehicleId: number
        +userId: number
        +name: string
        +vehicleType: VehicleType
        +brand: string
        +model: string
        +manufactureYear: number
        +licensePlate: string
        +vin: string
        +currentOdometer: number
        +purchaseDate: Date
        +imageUrl: string
        +isArchived: boolean
    }
    class Garage {
        +garageId: number
        +userId: number
        +name: string
        +address: string
        +phone: string
        +note: string
    }
    class ServiceType {
        +serviceTypeId: number
        +name: string
        +description: string
        +appliesTo: AppliesTo
        +defaultIntervalKm: number
        +defaultIntervalMonths: number
        +isActive: boolean
    }
    class MaintenanceRecord {
        +recordId: number
        +vehicleId: number
        +garageId: number
        +serviceDate: Date
        +odometer: number
        +note: string
        +items: MaintenanceItem[]
        +attachments: Attachment[]
        +totalCost: number
    }
    class MaintenanceItem {
        +itemId: number
        +recordId: number
        +serviceTypeId: number
        +description: string
        +quantity: number
        +unitPrice: number
        +lineTotal: number
    }
    class Attachment {
        +attachmentId: number
        +recordId: number
        +fileName: string
        +filePath: string
        +mimeType: string
        +fileSizeBytes: number
        +uploadedAt: Date
    }
    class Reminder {
        +reminderId: number
        +vehicleId: number
        +serviceTypeId: number
        +intervalKm: number
        +intervalMonths: number
        +lastServiceDate: Date
        +lastServiceOdometer: number
        +nextDueDate: Date
        +nextDueOdometer: number
        +notifyBeforeDays: number
        +notifyBeforeKm: number
        +isActive: boolean
        +lastNotifiedLevel: NotifyLevel
        +status: ReminderStatus
    }
    class Notification {
        +notificationId: number
        +userId: number
        +reminderId: number
        +type: NotificationType
        +title: string
        +message: string
        +isRead: boolean
        +createdAt: Date
        +readAt: Date
    }

    class Role {
        <<enumeration>>
        USER
        ADMIN
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
    class NotifyLevel {
        <<enumeration>>
        NONE
        DUE_SOON
        OVERDUE
    }
    class ReminderStatus {
        <<enumeration>>
        OK
        DUE_SOON
        OVERDUE
    }
    class NotificationType {
        <<enumeration>>
        DUE_SOON
        OVERDUE
        SYSTEM
    }

    User "1" --> "0..*" Vehicle : sở hữu
    User "1" --> "0..*" Garage : lưu
    User "1" --> "0..*" Notification : nhận
    Vehicle "1" --> "0..*" MaintenanceRecord : có
    Vehicle "1" --> "0..*" Reminder : có
    Garage "0..1" --> "0..*" MaintenanceRecord : thực hiện tại
    MaintenanceRecord "1" *-- "1..*" MaintenanceItem : gồm
    MaintenanceRecord "1" *-- "0..*" Attachment : đính kèm
    ServiceType "1" --> "0..*" MaintenanceItem : phân loại
    ServiceType "1" --> "0..*" Reminder : áp dụng cho
    Reminder "0..1" --> "0..*" Notification : sinh ra
```

- `MaintenanceRecord.totalCost` lấy từ view `v_record_totals`, không lưu trong bảng (BR-06). `items`, `attachments` chỉ có khi đọc chi tiết.
- `Reminder.status` lấy từ view `v_reminder_status` khi đọc danh sách, hoặc tính bằng `ReminderService.computeStatus` (BR-09). Không lưu trong bảng.
- Quan hệ **hợp thành** (hình thoi đặc) giữa `MaintenanceRecord` với `MaintenanceItem`, `Attachment`: xóa lần bảo dưỡng thì xóa luôn hạng mục và hóa đơn (CASCADE ở tài liệu 04).

### 4.2. Thành phần dùng chung

```mermaid
classDiagram
    direction LR

    class Database {
        -pool: Pool
        +query(sql, params, conn) Promise~Row[]~
        +withTransaction(fn) Promise~T~
    }
    class AuthMiddleware {
        +auth(req, res, next) void
        +requireAdmin(req, res, next) void
    }
    class ValidateMiddleware {
        +validate(rules) Middleware
    }
    class UploadMiddleware {
        +vehicleImage Middleware
        +invoiceFiles Middleware
    }
    class ErrorHandler {
        +handle(err, req, res, next) void
    }
    class FileStorage {
        +save(file, folder) Promise~string~
        +remove(filePath) Promise~void~
    }
    class AppError {
        +statusCode: number
        +code: string
        +message: string
        +details: object
    }
    class ValidationError {
        statusCode = 400
    }
    class UnauthorizedError {
        statusCode = 401
    }
    class ForbiddenError {
        statusCode = 403
    }
    class NotFoundError {
        statusCode = 404
    }
    class ConflictError {
        statusCode = 409
    }

    AppError <|-- ValidationError
    AppError <|-- UnauthorizedError
    AppError <|-- ForbiddenError
    AppError <|-- NotFoundError
    AppError <|-- ConflictError
    ErrorHandler ..> AppError : đổi thành HTTP status
    AuthMiddleware ..> UnauthorizedError : ném
    AuthMiddleware ..> ForbiddenError : ném
```

### 4.3. Tài khoản và quản trị người dùng (M1, M8)

```mermaid
classDiagram
    direction LR

    class AuthController {
        +register(req, res)
        +login(req, res)
    }
    class UserController {
        +getMe(req, res)
        +updateMe(req, res)
        +changePassword(req, res)
    }
    class AdminController {
        +listUsers(req, res)
        +setUserStatus(req, res)
        +getSystemStatistics(req, res)
    }
    class AuthService {
        +register(dto) Promise~User~
        +login(email, password) Promise~AuthResult~
        +verifyToken(token) TokenPayload
        -signToken(user) string
    }
    class UserService {
        +getProfile(userId) Promise~User~
        +updateProfile(userId, dto) Promise~User~
        +changePassword(userId, oldPassword, newPassword) Promise~void~
    }
    class AdminService {
        +listUsers(query) Promise~Page~
        +setUserStatus(adminId, userId, isActive) Promise~void~
        +getSystemStatistics(year) Promise~SystemStats~
    }
    class UserRepository {
        +findById(userId) Promise~User~
        +findByEmail(email) Promise~User~
        +create(data) Promise~number~
        +update(userId, data) Promise~void~
        +updatePassword(userId, hash) Promise~void~
        +search(keyword, page, size) Promise~Page~
        +setActive(userId, isActive) Promise~void~
        +countSystemByMonth(year) Promise~Row[]~
    }

    AuthController --> AuthService
    UserController --> UserService
    AdminController --> AdminService
    AuthService --> UserRepository
    UserService --> UserRepository
    AdminService --> UserRepository
```

### 4.4. Xe và garage (M2, M3)

```mermaid
classDiagram
    direction LR

    class VehicleController {
        +list(req, res)
        +create(req, res)
        +getById(req, res)
        +update(req, res)
        +remove(req, res)
        +updateOdometer(req, res)
        +setArchived(req, res)
    }
    class VehicleService {
        +listVehicles(userId, includeArchived) Promise~Vehicle[]~
        +getOwnedVehicle(userId, vehicleId) Promise~Vehicle~
        +createVehicle(userId, dto, imageFile) Promise~Vehicle~
        +updateVehicle(userId, vehicleId, dto, imageFile) Promise~Vehicle~
        +updateOdometer(userId, vehicleId, odometer) Promise~Vehicle~
        +raiseOdometerIfHigher(vehicleId, odometer, conn) Promise~void~
        +setArchived(userId, vehicleId, archived) Promise~void~
        +deleteVehicle(userId, vehicleId) Promise~void~
        -checkPlateUnique(userId, plate, excludeId) Promise~void~
    }
    class VehicleRepository {
        +findByUser(userId, includeArchived) Promise~Vehicle[]~
        +findById(vehicleId) Promise~Vehicle~
        +existsPlate(userId, plate, excludeId) Promise~boolean~
        +create(data) Promise~number~
        +update(vehicleId, data) Promise~void~
        +updateOdometer(vehicleId, odometer, conn) Promise~void~
        +setArchived(vehicleId, archived) Promise~void~
        +delete(vehicleId) Promise~void~
        +countRecords(vehicleId) Promise~number~
    }
    class FileStorage {
        <<dùng chung>>
    }

    class GarageController {
        +list(req, res)
        +create(req, res)
        +update(req, res)
        +remove(req, res)
    }
    class GarageService {
        +listGarages(userId) Promise~Garage[]~
        +getOwnedGarage(userId, garageId) Promise~Garage~
        +createGarage(userId, dto) Promise~Garage~
        +updateGarage(userId, garageId, dto) Promise~Garage~
        +deleteGarage(userId, garageId) Promise~void~
    }
    class GarageRepository {
        +findByUser(userId) Promise~Garage[]~
        +findById(garageId) Promise~Garage~
        +create(data) Promise~number~
        +update(garageId, data) Promise~void~
        +delete(garageId) Promise~void~
    }

    VehicleController --> VehicleService
    VehicleService --> VehicleRepository
    VehicleService --> FileStorage : ảnh xe
    GarageController --> GarageService
    GarageService --> GarageRepository
```

### 4.5. Lịch sử bảo dưỡng (M4)

Các lớp có nhãn `«M2»`, `«M3»`, `«M6»` thuộc module khác, chỉ vẽ để thể hiện M4 gọi sang (chi tiết ở 4.4 và 4.6).

```mermaid
classDiagram
    direction LR

    class MaintenanceController {
        +listByVehicle(req, res)
        +create(req, res)
        +getById(req, res)
        +update(req, res)
        +remove(req, res)
        +exportCsv(req, res)
        +uploadAttachments(req, res)
        +removeAttachment(req, res)
    }
    class MaintenanceService {
        +listRecords(userId, vehicleId, filter) Promise~MaintenanceRecord[]~
        +getRecordDetail(userId, recordId) Promise~MaintenanceRecord~
        +createRecord(userId, vehicleId, dto) Promise~MaintenanceRecord~
        +updateRecord(userId, recordId, dto) Promise~MaintenanceRecord~
        +deleteRecord(userId, recordId) Promise~void~
        +exportCsv(userId, vehicleId) Promise~string~
        +addAttachments(userId, recordId, files) Promise~Attachment[]~
        +deleteAttachment(userId, attachmentId) Promise~void~
        -getOwnedRecord(userId, recordId) Promise~MaintenanceRecord~
        -validateRecord(dto) void
    }
    class MaintenanceRecordRepository {
        +findByVehicle(vehicleId, filter) Promise~MaintenanceRecord[]~
        +findById(recordId) Promise~MaintenanceRecord~
        +create(data, conn) Promise~number~
        +update(recordId, data, conn) Promise~void~
        +delete(recordId, conn) Promise~void~
        +findLatestByServiceType(vehicleId, serviceTypeId, conn) Promise~MaintenanceRecord~
    }
    class MaintenanceItemRepository {
        +findByRecord(recordId) Promise~MaintenanceItem[]~
        +createMany(recordId, items, conn) Promise~void~
        +deleteByRecord(recordId, conn) Promise~void~
        +findServiceTypeIds(recordId, conn) Promise~number[]~
    }
    class AttachmentRepository {
        +findByRecord(recordId) Promise~Attachment[]~
        +findById(attachmentId) Promise~Attachment~
        +create(data) Promise~number~
        +delete(attachmentId) Promise~void~
    }
    class VehicleService {
        <<M2>>
    }
    class GarageService {
        <<M3>>
    }
    class ReminderService {
        <<M6>>
    }
    class FileStorage {
        <<dùng chung>>
    }

    MaintenanceController --> MaintenanceService
    MaintenanceService --> MaintenanceRecordRepository
    MaintenanceService --> MaintenanceItemRepository
    MaintenanceService --> AttachmentRepository
    MaintenanceService --> VehicleService : getOwnedVehicle, raiseOdometerIfHigher
    MaintenanceService --> GarageService : getOwnedGarage
    MaintenanceService --> ReminderService : onMaintenanceSaved, onMaintenanceDeleted
    MaintenanceService --> FileStorage : hóa đơn
```

### 4.6. Loại dịch vụ, nhắc lịch, thông báo (M5, M6)

```mermaid
classDiagram
    direction LR

    class ServiceTypeController {
        +listActive(req, res)
        +adminList(req, res)
        +create(req, res)
        +update(req, res)
    }
    class ServiceTypeService {
        +listActive(vehicleType) Promise~ServiceType[]~
        +listAll(query) Promise~ServiceType[]~
        +getById(serviceTypeId) Promise~ServiceType~
        +create(dto) Promise~ServiceType~
        +update(serviceTypeId, dto) Promise~ServiceType~
    }
    class ServiceTypeRepository {
        +findActive(vehicleType) Promise~ServiceType[]~
        +findAll(query) Promise~ServiceType[]~
        +findById(serviceTypeId) Promise~ServiceType~
        +existsName(name, excludeId) Promise~boolean~
        +create(data) Promise~number~
        +update(serviceTypeId, data) Promise~void~
    }

    class ReminderController {
        +listByVehicle(req, res)
        +create(req, res)
        +update(req, res)
        +remove(req, res)
    }
    class ReminderService {
        +listReminders(userId, vehicleId) Promise~Reminder[]~
        +createReminder(userId, vehicleId, dto) Promise~Reminder~
        +updateReminder(userId, reminderId, dto) Promise~Reminder~
        +deleteReminder(userId, reminderId) Promise~void~
        +onMaintenanceSaved(recordId, conn, previousServiceTypeIds) Promise~void~
        +onMaintenanceDeleted(vehicleId, serviceTypeIds, conn) Promise~void~
        +computeNextDue(lastDate, lastOdometer, intervalMonths, intervalKm) DueMark
        +computeStatus(reminder, currentOdometer, today) ReminderStatus
        -recalculate(vehicleId, serviceTypeIds, conn) Promise~void~
    }
    class ReminderRepository {
        +findByVehicle(vehicleId) Promise~Reminder[]~
        +findById(reminderId) Promise~Reminder~
        +findByVehicleAndServiceTypes(vehicleId, serviceTypeIds, conn) Promise~Reminder[]~
        +create(data) Promise~number~
        +update(reminderId, data, conn) Promise~void~
        +delete(reminderId) Promise~void~
        +findActiveForScan() Promise~Reminder[]~
        +setNotifiedLevel(reminderId, level, conn) Promise~void~
    }
    class ReminderJob {
        +schedule() void
        +run() Promise~JobResult~
    }
    class NotificationController {
        +list(req, res)
        +unreadCount(req, res)
        +markRead(req, res)
        +markAllRead(req, res)
    }
    class NotificationService {
        +listNotifications(userId, page) Promise~Page~
        +countUnread(userId) Promise~number~
        +markRead(userId, notificationId) Promise~void~
        +markAllRead(userId) Promise~void~
        +createForReminder(reminder, level, conn) Promise~Notification~
    }
    class NotificationRepository {
        +findByUser(userId, page) Promise~Page~
        +countUnread(userId) Promise~number~
        +create(data, conn) Promise~number~
        +markRead(userId, notificationId) Promise~void~
        +markAllRead(userId) Promise~void~
    }
    class EmailService {
        +sendReminderEmail(user, notification) Promise~void~
    }
    class VehicleService {
        <<M2>>
    }

    ServiceTypeController --> ServiceTypeService
    ServiceTypeService --> ServiceTypeRepository
    ReminderController --> ReminderService
    ReminderService --> ReminderRepository
    ReminderService --> ServiceTypeService : chu kỳ mặc định
    ReminderService --> VehicleService : getOwnedVehicle
    ReminderJob --> ReminderService : computeStatus
    ReminderJob --> ReminderRepository : findActiveForScan, setNotifiedLevel
    ReminderJob --> NotificationService : createForReminder
    ReminderJob ..> EmailService : nếu bật email
    NotificationController --> NotificationService
    NotificationService --> NotificationRepository
```

### 4.7. Dashboard và thống kê (M7)

```mermaid
classDiagram
    direction LR

    class StatisticsController {
        +dashboard(req, res)
        +costs(req, res)
    }
    class StatisticsService {
        +getDashboard(userId) Promise~Dashboard~
        +getCosts(userId, from, to, groupBy, vehicleId) Promise~CostSeries~
    }
    class StatisticsRepository {
        +countVehicles(userId) Promise~number~
        +sumCost(userId, from, to) Promise~number~
        +recentRecords(userId, limit) Promise~MaintenanceRecord[]~
        +dueReminders(userId) Promise~Reminder[]~
        +costsByMonth(userId, from, to, vehicleId) Promise~Row[]~
        +costsByVehicle(userId, from, to) Promise~Row[]~
        +costsByServiceType(userId, from, to, vehicleId) Promise~Row[]~
    }
    class VehicleService {
        <<M2>>
    }

    StatisticsController --> StatisticsService
    StatisticsService --> StatisticsRepository
    StatisticsService --> VehicleService : getOwnedVehicle khi lọc xe
```

## 5. Trách nhiệm từng lớp

### 5.1. Theo tầng

| Tầng | Thành phần | Được làm | Không được làm |
|---|---|---|---|
| Presentation | `pages`, `components`, `layouts` | Hiển thị, kiểm tra dữ liệu sơ bộ trên form (NFR-03), gọi `api/` | Gọi thẳng `axios` trong component; tự tính quy tắc nghiệp vụ thay server |
| Presentation | `api/*` | Gọi REST API, tự gắn header `Authorization`, chuyển lỗi 401 về trang đăng nhập | |
| Presentation | `AuthContext` | Giữ JWT và thông tin người dùng, cung cấp `login`, `logout` cho toàn app | |
| Route | `*.routes.js` | Khai báo URL, gắn middleware (`auth`, `requireAdmin`, `validate`, `upload`) | Chứa logic |
| Controller | `*Controller` | Lấy `req.user.userId`, `req.params`, `req.body`; gọi một hàm Service; trả HTTP status + JSON | Truy vấn database; kiểm tra quy tắc nghiệp vụ |
| Business | `*Service` | Quy tắc nghiệp vụ BR-xx, kiểm tra quyền sở hữu, mở giao dịch, gọi Service module khác; ném `AppError` | Đọc `req`/`res`; viết SQL |
| Data Access | `*Repository` | Một hàm = một (hoặc vài) câu SQL tham số hóa; đổi cột `snake_case` ↔ thuộc tính `camelCase` | Quy tắc nghiệp vụ; gọi Repository khác |
| Job | `ReminderJob` | Lên lịch bằng `node-cron`, chạy quét nhắc lịch | Viết SQL trực tiếp |

### 5.2. Theo lớp

| Lớp | Module | Trách nhiệm chính | FR / BR |
|---|---|---|---|
| `Database` | dùng chung | Tạo pool kết nối `mysql2`, `query` với tham số, `withTransaction` (BEGIN/COMMIT/ROLLBACK) | NFR-03 |
| `AuthMiddleware` | dùng chung (M1) | `auth`: đọc Bearer token, gắn `req.user = { userId, role }`, kiểm tra tài khoản chưa bị khóa. `requireAdmin`: chặn nếu `role ≠ ADMIN` | NFR-02, BR-13 |
| `ValidateMiddleware` | dùng chung | Kiểm tra kiểu, bắt buộc, độ dài theo luật `express-validator`; lỗi → 400 kèm tên trường | NFR-03, NFR-06 |
| `UploadMiddleware` | dùng chung | Cấu hình `multer`: chỉ JPG/PNG/PDF, tối đa 5 MB/file | NFR-08 |
| `ErrorHandler` | dùng chung | Đổi `AppError` thành HTTP status + JSON `{ code, message, details }`; lỗi lạ → 500, ghi log | NFR-06 |
| `AppError` và lớp con | dùng chung | Phân loại lỗi: 400 dữ liệu sai, 401 chưa đăng nhập, 403 không có quyền, 404 không tìm thấy hoặc không phải của mình, 409 trùng | NFR-02 |
| `FileStorage` | dùng chung | Đặt tên file duy nhất, lưu vào `uploads/`, xóa file vật lý | FR-05, FR-15 |
| `AuthService` | M1 | Đăng ký (kiểm tra email trùng, băm bcrypt), đăng nhập, ký/giải mã JWT | FR-01, FR-02, BR-01, BR-13, NFR-01 |
| `UserService` | M1 | Xem/sửa hồ sơ, đổi mật khẩu (kiểm tra mật khẩu cũ) | FR-04 |
| `AdminService` | M8 | Tìm kiếm, khóa/mở khóa người dùng (không tự khóa mình), thống kê hệ thống | FR-27, FR-28, BR-13 |
| `VehicleService` | M2 | CRUD xe, `getOwnedVehicle` cho module khác, cập nhật ODO không giảm, `raiseOdometerIfHigher` khi ghi nhận bảo dưỡng, lưu trữ, chỉ xóa hẳn xe chưa có lịch sử | FR-05 → FR-10, BR-02, BR-03, BR-12 |
| `GarageService` | M3 | CRUD garage của người dùng, `getOwnedGarage` | FR-16 |
| `MaintenanceService` | M4 | Ghi nhận/sửa/xóa lần bảo dưỡng trong một giao dịch, kiểm tra ngày, hạng mục, chi phí; gọi M2 nâng ODO, gọi M6 tính lại mốc; lịch sử có lọc; hóa đơn; xuất CSV | FR-11 → FR-15, FR-17, BR-03 → BR-06 |
| `ServiceTypeService` | M5 | Danh mục loại dịch vụ, chỉ ngừng dùng chứ không xóa | FR-26, BR-14 |
| `ReminderService` | M6 | CRUD nhắc lịch, tính mốc đến hạn, tính trạng thái, tính lại mốc khi lịch sử bảo dưỡng thay đổi | FR-18 → FR-20, BR-07 → BR-09, BR-11 |
| `ReminderJob` | M6 | 07:00 hằng ngày quét nhắc lịch, sinh thông báo không trùng, gửi email nếu bật | FR-21, FR-23, BR-10 |
| `NotificationService` | M6 | Danh sách, đếm chưa đọc, đánh dấu đã đọc, tạo thông báo cho nhắc lịch | FR-21, FR-22 |
| `EmailService` | M6 | Gửi email qua SMTP | FR-23 (Could) |
| `StatisticsService` | M7 | Số liệu Dashboard, chi phí theo tháng / xe / loại dịch vụ | FR-24, FR-25 |
| `*Repository` | từng module | Truy vấn bảng tương ứng ở tài liệu 04; `StatisticsRepository` đọc từ view `v_record_totals`, `v_reminder_status` | – |

Các hàm thuần (không chạm database) chứa quy tắc nghiệp vụ, ưu tiên viết unit test trước (mục 5.1 tài liệu 08): `ReminderService.computeNextDue`, `ReminderService.computeStatus`, `MaintenanceService.validateRecord`.

## 6. Cấu trúc thư mục backend theo class diagram

```
backend/src/
├── config/database.js              # Database
├── middlewares/
│   ├── auth.js                     # AuthMiddleware (auth, requireAdmin)
│   ├── validate.js                 # ValidateMiddleware
│   ├── upload.js                   # UploadMiddleware
│   └── errorHandler.js             # ErrorHandler
├── utils/
│   ├── errors.js                   # AppError và các lớp con
│   └── fileStorage.js              # FileStorage
├── modules/
│   ├── auth/                       # AuthController, AuthService
│   ├── users/                      # UserController, UserService, UserRepository
│   ├── admin/                      # AdminController, AdminService
│   ├── vehicles/                   # VehicleController, VehicleService, VehicleRepository
│   ├── garages/                    # GarageController, GarageService, GarageRepository
│   ├── maintenance/                # MaintenanceController, MaintenanceService,
│   │                               # MaintenanceRecordRepository, MaintenanceItemRepository, AttachmentRepository
│   ├── service-types/              # ServiceTypeController, ServiceTypeService, ServiceTypeRepository
│   ├── reminders/                  # ReminderController, ReminderService, ReminderRepository
│   ├── notifications/              # NotificationController, NotificationService, NotificationRepository, EmailService
│   └── statistics/                 # StatisticsController, StatisticsService, StatisticsRepository
├── jobs/reminder.job.js            # ReminderJob
└── app.js
```

So với mục 2 tài liệu 08: thêm thư mục `modules/admin/` cho M8 và `utils/` cho lỗi, lưu file. Phần còn lại giữ nguyên.

## 7. Ghi chú cho tài liệu 08

Đề xuất Giang cập nhật tài liệu 08 sau khi nhóm duyệt tài liệu này:

1. **Mục 1:** công nghệ giữ nguyên, có thể dẫn sang mục 1 tài liệu này cho danh sách thư viện.
2. **Mục 2:** thêm `modules/admin/` và `utils/` như mục 6 ở trên.
3. **Hợp đồng M6 → M4 (mục 3):** đổi thành
   - `reminderService.onMaintenanceSaved(recordId, conn, previousServiceTypeIds = [])`: gọi trong cùng giao dịch của M4 (`conn`). Khi **sửa** lần bảo dưỡng, M4 truyền thêm danh sách loại dịch vụ cũ để M6 tính lại cả nhắc lịch của loại bị bỏ khỏi phiếu.
   - Thêm `reminderService.onMaintenanceDeleted(vehicleId, serviceTypeIds, conn)`: khi **xóa** lần bảo dưỡng, mốc phải quay về lần làm gần nhất còn lại (UC-21 ở tài liệu 02).
   - Cả hai hàm đều tính lại theo lần làm **gần nhất** của loại dịch vụ đó (ngày lớn nhất), không mặc định lần vừa lưu là mới nhất, vì người dùng có thể ghi bù lần bảo dưỡng cũ.
4. **Hợp đồng M2 → M4:** thêm `vehicleService.raiseOdometerIfHigher(vehicleId, odometer, conn)` để M4 nâng ODO xe trong cùng giao dịch (BR-03).
5. **Tiến trình nhắc lịch:** bỏ qua xe đã lưu trữ và tài khoản bị khóa (`ReminderRepository.findActiveForScan`).
