# Nhật ký ETL

- Cửa sổ dữ liệu: 2018-11-01 → 2026-09-30
- Lịch giao dịch chung (theo VN-Index): 1973 phiên (2018-11-01 → 2026-09-30)
- Vũ trụ ban đầu: 30 mã (VN30 kỳ 01/2020) | giữ lại: 29 mã
- Quy tắc điền thiếu: ffill tối đa 5 phiên + cột cờ `imputed` (file prices_imputed.csv)
- Số ô giá được điền: 4 | ô NaN còn lại: 1029
- VN-Index: nguồn vnindex_manual.csv (1973/1973 phiên khớp lịch); khoảng [659.21, 1927.94] điểm

## Quy tắc làm sạch (4 bước)
1. Chuẩn hóa: tên cột thường, ngày dạng datetime, bỏ ngày trùng (giữ bản cuối), giá ≤ 0 → NaN, nếu trung vị giá < 1.000 thì nhân 1.000 (nghìn đồng → VND).
2. Căn lịch: reindex theo các phiên của VN-Index.
3. Xử lý thiếu: điền giá phiên trước tối đa 5 phiên (chỉ trong khoảng đã niêm yết), gắn cờ imputed; thiếu dài hơn giữ NaN và ghi lại.
4. Kiểm tra cuối: loại mã thiếu lịch sử hoặc thiếu dài trước kỳ quyết định đầu; mã ngừng giao dịch/thiếu dài sau đó được GIỮ (tránh thiên lệch sống sót) và ghi vào events.csv; quét biến động ngày > 7,5% (vượt biên độ ±7%) để nghi ngờ giá chưa điều chỉnh.

## Số dòng trước/sau theo mã
| Mã | Dòng thô | Trùng ngày | Giá ≤0 | Nhân 1000 | Dòng sau căn lịch | Ô điền (imputed) | Trạng thái |
|---|---|---|---|---|---|---|---|
| BID | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| BVH | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| CTD | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| CTG | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| EIB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| FPT | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| GAS | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| HDB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| HPG | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| MBB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| MSN | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| MWG | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| NVL | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| PLX | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| PNJ | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| POW | 1964 | 0 | 0 | có | 1964 | 5 | LOẠI: đoạn thiếu 9 phiên (2018-12-28 → 2019-01-11) trước kỳ quyết định đầu → không đủ giá liên tục (A1) |
| REE | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| ROS | 940 | 0 | 0 | có | 940 | 4 | giữ |
| SAB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| SBT | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| SSI | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| STB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| TCB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VCB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VHM | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VIC | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VJC | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VNM | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VPB | 1973 | 0 | 0 | có | 1973 | 0 | giữ |
| VRE | 1973 | 0 | 0 | có | 1973 | 0 | giữ |

## Mã bị loại và lý do
- **POW**: đoạn thiếu 9 phiên (2018-12-28 → 2019-01-11) trước kỳ quyết định đầu → không đủ giá liên tục (A1)

## Sự kiện giữ lại trong dữ liệu (data/processed/events.csv)
- **ROS** – dung_giao_dich: từ 2022-08-11  (1029 phiên). giữ trong prices.csv, NaN sau ngày cuối; loại ở kỳ tái cân bằng kế tiếp

## Mã nghi chưa điều chỉnh giá (biến động > 7.5%/ngày, vượt biên độ ±7% HOSE) — cần đối chiếu tay
- **ROS**: [('2022-05-04', 0.1609)]

## Lãi suất phi rủi ro (TPCP 10 năm)
- {"rows_source": 2080, "calendar_days": 1973, "na_after_fill": 0, "na_before_first_obs": 0, "rf_annual_min": 0.02038, "rf_annual_max": 0.052140000000000006}

## Ghi chú
- Ô NaN còn lại thuộc các sự kiện trong data/processed/events.csv (mã ngừng giao dịch/thiếu dài sau kỳ quyết định đầu). Backtest (TV5) phải bán/loại các mã này ở kỳ tái cân bằng kế tiếp.

## Ghi chú thủ công (TV2) – không bị ghi đè khi chạy run_all.py

## Ngoại lệ dữ liệu
- POW: thiếu 9 phiên 28/12/2018–11/01/2019 (do chuyển sàn UPCoM → HOSE: giao dịch cuối trên UPCoM 27/12/2018, hủy đăng ký giao dịch UPCoM từ 28/12/2018, niêm yết HOSE từ 14/01/2019 – nguồn: https://vnbusiness.vn/pow-se-niem-yet-tren-hose-tu-1412019.html); không đủ giá liên tục trước kỳ quyết định đầu → loại theo A1.
- ROS: ngừng giao dịch trên HOSE sau 11/08/2022; giữ trong dữ liệu để tránh thiên lệch sống sót (xem events.csv); backtest bán ở kỳ tái cân bằng kế tiếp.
- ROS: biến động +16,1% ngày 04/05/2022 là cộng dồn qua 3 phiên không có giá (27–29/04/2022) trước kỳ nghỉ lễ 30/4–1/5, không phải lỗi điều chỉnh giá.

## Đối chiếu
- Giá đã điều chỉnh: đối chiếu HPG – cổ tức năm 2021 trả 30% bằng cổ phiếu + 5% tiền mặt, ngày ĐKCC 20/06/2022, GDKHQ 17/06/2022 (nguồn: https://doanhnhan.baophapluat.vn/tap-doan-hoa-phat-hpg-chot-quyen-tra-co-tuc-nam-2021-ty-le-35-47265.html). Nếu chưa điều chỉnh, giá ngày GDKHQ phải giảm khoảng 23% (1 − 1/1,3). Giá vnstock: 16/06 = 15.870 đ, 17/06 = 15.690 đ (−1,13%); cả tuần 13–24/06/2022 không có phiên nào giảm quá biên độ 7% → giá ĐÃ điều chỉnh.
- TPCP 10 năm: so 4 ngày (31/12/2019 3,378%; 30/12/2022 5,037%; 30/09/2026 4,581%; 26/10/2026 4,578%) với TradingView (TVC:VN10Y) → khớp (xem data/raw/tpcp10y_SOURCE.md).
- VN-Index: điểm đóng cửa lấy từ Investing (data/raw/vnindex_manual.csv); so 3 ngày (31/12/2019 960,99; 30/12/2022 1.007,09; 30/09/2026 1.768,62) với TradingView (HOSE:VNINDEX) → khớp (xem data/raw/vnindex_manual_SOURCE.md).