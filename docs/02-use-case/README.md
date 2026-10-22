# 02 – Use Case Diagram

**Người phụ trách:** Tăng Thoại Lâm · **Đầu vào:** [01 Requirements](../01-requirements/requirements.md)

Cần nộp:
- Sơ đồ use case tổng quát. Tác nhân: **Chủ xe** và **Google Gemini API** (hệ thống ngoài). Bản demo không có đăng nhập nên không có tác nhân Khách hay Quản trị viên (xem mục 1.4 tài liệu 01).
- Nhóm use case: Quản lý xe · Ghi nhận bảo dưỡng · Loại dịch vụ · Nhắc lịch · Dashboard/Thống kê · Chẩn đoán AI.
- Đặc tả các use case chính: tên, tác nhân, tiền điều kiện, hậu điều kiện, luồng chính, luồng thay thế/ngoại lệ, mã `FR-xx`.
- Use case **Chẩn đoán AI** phải có luồng ngoại lệ cho 4 lỗi ở bảng BR-10 (thiếu key, 429, timeout, lỗi Gemini).
