# Nguồn lợi suất TPCP 10 năm (data/raw/tpcp10y.csv)

- Chuỗi: Lợi suất trái phiếu chính phủ Việt Nam kỳ hạn 10 năm, tần suất ngày
- Nguồn: Investing.com – https://www.investing.com/rates-bonds/vietnam-10-year-bond-yield-historical-data (file tải từ giao diện tiếng Việt: cột Ngày, Lần cuối)
- Giai đoạn tải: 01/10/2018 – 30/09/2026 (2.080 dòng)
- Ngày tải: 26/10/2026
- Người tải: TV2
- Đơn vị: % / năm (cột Lần cuối); clean.py chia 100 -> rf_annual
- Ghi chú: Investing là nguồn tổng hợp thứ cấp; đối chiếu vài ngày với TradingView (TVC:VN10Y) hoặc Trading Economics.
- Kết quả đối chiếu (TradingView TVC:VN10Y, khung ngày, kiểm tra 26/10/2026 – TV2):
  | Ngày       | Investing | TradingView |
  |------------|-----------|-------------|
  | 31/12/2019 | 3,378%    | khớp        |
  | 30/12/2022 | 5,037%    | khớp        |
  | 30/09/2026 | 4,581%    | khớp        |

  Kết luận: giá trị đóng cửa trùng khớp ở cả 3 ngày → chấp nhận dùng Investing làm nguồn lãi suất phi rủi ro.