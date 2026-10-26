# Ghi chú thủ công (TV2) – không bị ghi đè khi chạy run_all.py

## Ngoại lệ dữ liệu
- POW: thiếu 9 phiên 28/12/2018–11/01/2019 (do chuyển sàn UPCoM → HOSE: giao dịch cuối trên UPCoM 27/12/2018, hủy đăng ký giao dịch UPCoM từ 28/12/2018, niêm yết HOSE từ 14/01/2019 – nguồn: https://vnbusiness.vn/pow-se-niem-yet-tren-hose-tu-1412019.html); không đủ giá liên tục trước kỳ quyết định đầu → loại theo A1.
- ROS: ngừng giao dịch trên HOSE sau 11/08/2022; giữ trong dữ liệu để tránh thiên lệch sống sót (xem events.csv); backtest bán ở kỳ tái cân bằng kế tiếp.
- ROS: biến động +16,1% ngày 04/05/2022 là cộng dồn qua 3 phiên không có giá (27–29/04/2022) trước kỳ nghỉ lễ 30/4–1/5, không phải lỗi điều chỉnh giá.

## Đối chiếu
- Giá đã điều chỉnh: đối chiếu HPG – cổ tức năm 2021 trả 30% bằng cổ phiếu + 5% tiền mặt, ngày ĐKCC 20/06/2022, GDKHQ 17/06/2022 (nguồn: https://doanhnhan.baophapluat.vn/tap-doan-hoa-phat-hpg-chot-quyen-tra-co-tuc-nam-2021-ty-le-35-47265.html). Nếu chưa điều chỉnh, giá ngày GDKHQ phải giảm khoảng 23% (1 − 1/1,3). Giá vnstock: 16/06 = 15.870 đ, 17/06 = 15.690 đ (−1,13%); cả tuần 13–24/06/2022 không có phiên nào giảm quá biên độ 7% → giá ĐÃ điều chỉnh.
- TPCP 10 năm: so 4 ngày (31/12/2019 3,378%; 30/12/2022 5,037%; 30/09/2026 4,581%; 26/10/2026 4,578%) với TradingView (TVC:VN10Y) → khớp (xem data/raw/tpcp10y_SOURCE.md).
- VN-Index: điểm đóng cửa lấy từ Investing (data/raw/vnindex_manual.csv); so 3 ngày (31/12/2019 960,99; 30/12/2022 1.007,09; 30/09/2026 1.768,62) với TradingView (HOSE:VNINDEX) → khớp (xem data/raw/vnindex_manual_SOURCE.md).