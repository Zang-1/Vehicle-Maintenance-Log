# 06 – UI Design trên Figma

**Người phụ trách:** Nguyễn Nam Khoa · **Đầu vào:** 05 (Wireframe) · **Trạng thái:** ✅ Xong (chờ review)

## Link Figma

**<DÁN LINK FIGMA VÀO ĐÂY>** (quyền "Anyone with the link can view")

## Nội dung thư mục

| Tệp | Mô tả |
|-----|-------|
| [style-guide.md](style-guide.md) | Bảng màu, font, thang chữ, khoảng cách, bố cục và đoạn CSS biến để dùng cho `base.html` |
| [components.md](components.md) | Danh sách component, biến thể và màn hình sử dụng |
| `exports/` | Ảnh xuất của toàn bộ màn hình (bảng dưới) |

## Nguyên tắc thiết kế

- Thiết kế dựa trên wireframe ở [`05-wireframe`](../05-wireframe/README.md), giữ nguyên mã màn hình S01–S11 và mã `FR-xx`, `BR-xx`.
- Màu trạng thái thống nhất: xanh lá = Còn hạn / LOW, vàng cam = Sắp đến hạn / MEDIUM, đỏ = Quá hạn / HIGH / lỗi. Luôn kèm nhãn chữ.
- Màn hình S10 có đủ 8 trạng thái: ban đầu, đang chờ, thành công và từng lỗi 503, 429, 504, 502, 422 theo bảng BR-10. Khi AI lỗi, nội dung đã nhập được giữ nguyên.
- Dùng được trên điện thoại từ 360 px (NFR-08).

## Ảnh xuất – desktop (1280×800)

| Màn hình | Ảnh |
|----------|-----|
| S01 | [S01-dashboard.png](exports/S01-dashboard.png) |
| S02 | [S02-danh-sach-xe.png](exports/S02-danh-sach-xe.png) |
| S02b | [S02b-xac-nhan-luu-tru.png](exports/S02b-xac-nhan-luu-tru.png) |
| S02c | [S02c-trang-thai-rong.png](exports/S02c-trang-thai-rong.png) |
| S03 | [S03-them-sua-xe.png](exports/S03-them-sua-xe.png) |
| S04 | [S04-chi-tiet-xe-lich-su.png](exports/S04-chi-tiet-xe-lich-su.png) |
| S04b | [S04b-chi-tiet-xe-nhac-lich.png](exports/S04b-chi-tiet-xe-nhac-lich.png) |
| S05 | [S05-ghi-nhan-bao-duong.png](exports/S05-ghi-nhan-bao-duong.png) |
| S06 | [S06-chi-tiet-lan-bao-duong.png](exports/S06-chi-tiet-lan-bao-duong.png) |
| S07 | [S07-tao-nhac-lich.png](exports/S07-tao-nhac-lich.png) |
| S08 | [S08-thong-ke-chi-phi.png](exports/S08-thong-ke-chi-phi.png) |
| S09 | [S09-loai-dich-vu.png](exports/S09-loai-dich-vu.png) |
| S10a | [S10a-chan-doan-ban-dau.png](exports/S10a-chan-doan-ban-dau.png) |
| S10b | [S10b-dang-cho.png](exports/S10b-dang-cho.png) |
| S10c | [S10c-thanh-cong.png](exports/S10c-thanh-cong.png) |
| S10d | [S10d-loi-503-no-key.png](exports/S10d-loi-503-no-key.png) |
| S10e | [S10e-loi-429-rate-limited.png](exports/S10e-loi-429-rate-limited.png) |
| S10f | [S10f-loi-504-timeout.png](exports/S10f-loi-504-timeout.png) |
| S10g | [S10g-loi-502-upstream.png](exports/S10g-loi-502-upstream.png) |
| S10h | [S10h-loi-422-qua-ngan.png](exports/S10h-loi-422-qua-ngan.png) |
| S11 | [S11-lich-su-chan-doan.png](exports/S11-lich-su-chan-doan.png) |

## Ảnh xuất – mobile (360×760)

| Màn hình | Ảnh |
|----------|-----|
| S01 mobile | [M-S01-dashboard.png](exports/M-S01-dashboard.png) |
| S04 mobile | [M-S04-chi-tiet-xe.png](exports/M-S04-chi-tiet-xe.png) |
| S05 mobile | [M-S05-ghi-nhan-bao-duong.png](exports/M-S05-ghi-nhan-bao-duong.png) |
| S10 mobile | [M-S10-chan-doan-ai.png](exports/M-S10-chan-doan-ai.png) |
