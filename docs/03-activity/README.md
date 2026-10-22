# 03 – Activity Diagram

**Người phụ trách:** Tăng Thoại Lâm · **Đầu vào:** [01 Requirements](../01-requirements/requirements.md), [02 Use Case](../02-use-case/)

Cần nộp activity diagram (có swimlane) cho:
1. **Ghi nhận lần bảo dưỡng** (Chủ xe / Server / Database): nhập form → kiểm tra BR-03, BR-04 → transaction (record + items + nâng ODO) → nhắc lịch tự tính lại.
2. **Tạo nhắc lịch** và cách trạng thái Còn hạn / Sắp đến hạn / Quá hạn được tính (BR-07, BR-08).
3. **Chẩn đoán AI** (Chủ xe / Server / Gemini / Database): có nhánh cho từng lỗi ở bảng BR-10, và nhánh lưu `diagnoses` cả khi lỗi.
4. **Từ commit đến production** (Lập trình viên / GitHub / GitHub Actions / Render): mở PR → `check` (ruff, pytest, build) → đỏ thì chặn merge → review → merge → `deploy` gọi deploy hook → Render build và chạy.
