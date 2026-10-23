# Style guide – Vehicle Maintenance Log

## 1. Màu sắc

| Token | Mã màu | Dùng cho |
|-------|--------|----------|
| `--color-primary` | `#2563EB` | Nút chính, liên kết, mục menu đang chọn |
| `--color-sidebar` | `#0F172A` | Nền menu bên trái |
| `--color-bg` | `#F4F6FA` | Nền trang |
| `--color-surface` | `#FFFFFF` | Thẻ (card), bảng, ô nhập |
| `--color-border` | `#E2E8F0` | Đường kẻ, viền thẻ |
| `--color-border-input` | `#CBD5E1` | Viền ô nhập |
| `--color-text` | `#0F172A` | Chữ chính |
| `--color-muted` | `#64748B` | Chữ phụ, nhãn |
| `--color-ok` / `--color-ok-bg` | `#15803D` / `#DCFCE7` | Còn hạn, mức LOW |
| `--color-warn` / `--color-warn-bg` | `#B45309` / `#FEF3C7` | Sắp đến hạn, mức MEDIUM |
| `--color-bad` / `--color-bad-bg` | `#B91C1C` / `#FEE2E2` | Quá hạn, mức HIGH, lỗi, nút xóa |
| `--color-head` | `#F1F5F9` | Nền hàng tiêu đề bảng, khối ghi chú |

Trạng thái luôn có nhãn chữ đi kèm màu để người khó phân biệt màu vẫn đọc được.

## 2. Chữ

- Font: **Be Vietnam Pro** (dự phòng: Inter, Arial, sans-serif). Cả hai hỗ trợ đầy đủ dấu tiếng Việt. Bản ảnh xuất trong thư mục `exports/` dùng Liberation Sans (metrics giống Arial) để render, khi làm trong Figma/CSS có thể thay bằng Be Vietnam Pro.
- Thang chữ: tiêu đề trang 24 bold · tiêu đề thẻ 15 bold · nội dung 13–14 · nhãn trường 12 bold · chú thích 11.

## 3. Khoảng cách và hình khối

- Lưới 8 px: khoảng cách 8 / 16 / 24 / 32.
- Bo góc: thẻ 8 px, nút và ô nhập 6 px, badge dạng viên thuốc.
- Viền 1 px, không dùng đổ bóng nặng.
- Vùng bấm tối thiểu cao 36 px (nút) và 38 px (ô nhập) để dùng được trên điện thoại.

## 4. Bố cục

- Desktop 1280 px: menu trái rộng 232 px, nội dung có lề 32 px.
- Mobile từ 360 px: thanh tiêu đề trên, thanh điều hướng 5 mục ở dưới, nội dung một cột, bảng chuyển thành danh sách thẻ.

## 5. Gợi ý chuyển sang CSS (cho `base.html` và CSS của M6)

```css
:root {
  --color-primary: #2563EB;   --color-sidebar: #0F172A;
  --color-bg: #F4F6FA;        --color-surface: #FFFFFF;
  --color-border: #E2E8F0;    --color-border-input: #CBD5E1;
  --color-text: #0F172A;      --color-muted: #64748B;
  --color-ok: #15803D;   --color-ok-bg: #DCFCE7;
  --color-warn: #B45309; --color-warn-bg: #FEF3C7;
  --color-bad: #B91C1C;  --color-bad-bg: #FEE2E2;
  --color-head: #F1F5F9;
  --radius-card: 8px; --radius-control: 6px;
  --space-1: 8px; --space-2: 16px; --space-3: 24px; --space-4: 32px;
  --font: "Be Vietnam Pro", Inter, Arial, sans-serif;
}
```
