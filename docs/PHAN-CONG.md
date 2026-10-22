# Phân công công việc – Vehicle Maintenance Log

Nhóm 3 thành viên: **Giang** (nhóm trưởng), **Lâm**, **Khoa**.

Nguyên tắc chia: mỗi người nhận một nhóm bước liên quan với nhau để không phải chờ nhau quá nhiều, và mỗi người đều có cả phần phân tích lẫn phần thiết kế.

| Thành viên | Vai trò chính | Bước phụ trách |
|---|---|---|
| **Giang** | Nhóm trưởng · Phân tích yêu cầu · Dữ liệu · Kế hoạch | 01 Requirements · 04 ERD & Database Design · 08 Implementation Plan |
| **Lâm** | Phân tích nghiệp vụ (UML) · Kiến trúc | 02 Use Case Diagram · 03 Activity Diagram · 07 Architecture & Class Diagram |
| **Khoa** | Thiết kế giao diện (UI/UX) | 05 Wireframe · 06 UI Design trên Figma |

## Chi tiết từng bước

| # | Bước | Người làm | Cần có trước | Sản phẩm nộp (đặt trong thư mục) |
|---|---|---|---|---|
| 01 | Requirements | Giang | – | `docs/01-requirements/requirements.md`: người dùng, mục tiêu, phạm vi, yêu cầu chức năng (FR), phi chức năng (NFR), quy tắc nghiệp vụ (BR) |
| 02 | Use Case Diagram | Lâm | 01 | `docs/02-use-case/`: sơ đồ use case tổng quát + đặc tả các use case chính (tác nhân, tiền/hậu điều kiện, luồng chính, luồng phụ) |
| 03 | Activity Diagram | Lâm | 01, 02 | `docs/03-activity/`: activity diagram cho các luồng chính (đăng nhập, thêm xe, ghi nhận bảo dưỡng, tạo nhắc lịch, xem thống kê) |
| 04 | ERD & Database Design | Giang | 01 | `docs/04-database/`: ERD, từ điển dữ liệu, script SQL tạo bảng + dữ liệu mẫu |
| 05 | Wireframe | Khoa | 01, 02 | `docs/05-wireframe/`: phác thảo bố cục từng màn hình (ảnh xuất ra hoặc link) |
| 06 | UI Design trên Figma | Khoa | 05 | `docs/06-ui-design/`: link Figma, bảng màu, typography, component, ảnh xuất các màn hình |
| 07 | Architecture & Class Diagram | Lâm | 02, 04 | `docs/07-architecture/`: sơ đồ kiến trúc tầng, class diagram, mô tả trách nhiệm từng lớp |
| 08 | Implementation Plan | Giang | 04, 07 | `docs/08-implementation-plan/implementation-plan.md`: chia module, thứ tự code, kế hoạch kiểm thử |

## Thứ tự và mốc thời gian (đề xuất)

```
Tuần 1:  Giang ── 01 Requirements ──────────► (chốt danh sách chức năng cho cả nhóm)
Tuần 2:  Lâm   ── 02 Use Case ── 03 Activity
         Giang ── 04 ERD & Database
         Khoa  ── 05 Wireframe
Tuần 3:  Khoa  ── 06 UI Figma
         Lâm   ── 07 Architecture & Class (dựa trên 04 của Giang)
Tuần 4:  Giang ── 08 Implementation Plan ── cả nhóm review chéo, chốt bản nộp
```

## Quy ước làm việc chung

- **Tên gọi thống nhất:** mọi người dùng chung mã chức năng `FR-xx` trong tài liệu 01 và tên bảng/cột trong tài liệu 04. Use case, wireframe, class diagram ghi rõ đang phục vụ FR nào.
- **Review chéo:** Lâm review 04 và 08 của Giang, Giang review 02–03–07 của Lâm, Khoa đối chiếu 05–06 với 01 và 02.
- **Git:** mỗi người làm trên nhánh riêng (`giang/...`, `lam/...`, `khoa/...`), mở Pull Request vào `main`, có ít nhất 1 người khác duyệt mới merge. Chi tiết ở mục 6 của tài liệu 08.
- **Sơ đồ:** ưu tiên viết bằng Mermaid trong file `.md` (GitHub tự hiển thị). Nếu vẽ bằng draw.io/StarUML thì nộp cả file gốc lẫn ảnh `.png`.
