# Nhật ký chuẩn bị dữ liệu (ETL 4 bước) – Chủ: TV2

> Theo mục 2.2 tài liệu của thầy. Mỗi bước ghi rõ: làm gì, quy tắc, số dòng trước/sau, số dòng bị ảnh hưởng.

**Nguồn & phiên bản:** vnstock phiên bản ___, nguồn dữ liệu ___ ; ngày tải ___ ; người tải ___

| Bước | Việc đã làm | Quy tắc áp dụng | Số dòng trước | Số dòng sau | Dòng bị ảnh hưởng | Ghi chú |
|---|---|---|---|---|---|---|
| 1. Đảm bảo chất lượng | Kiểu dữ liệu: ngày → date, giá → float, % → thập phân | | | | | Các cột đã đổi kiểu: |
| 2. Xác thực | Số phiên mỗi mã; đối chiếu giá 3 ngày ngẫu nhiên với HOSE/CafeF | | | | | Kết quả đối chiếu: |
| 3. Làm sạch | Trùng lặp, giá ≤ 0, thiếu giá (ffill ≤ 5 phiên + cờ), loại mã thiếu lịch sử | | | | | Mã bị loại: |
| 4. Khám phá sơ bộ | Thống kê mô tả, histogram lợi suất, ngoại lai (|r| > 7%, biên độ HOSE) | | | | | Bất thường: |

**Kiểm tra giá điều chỉnh:** sự kiện chia tách/cổ tức đã đối chiếu: ___ → kết luận ___
