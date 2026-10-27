# Nguồn VN-Index (data/raw/vnindex_manual.csv)

- Chuỗi: VN-Index, điểm đóng cửa, tần suất ngày
- Nguồn: Investing.com – https://www.investing.com/indices/vn-historical-data
- Giai đoạn tải: 01/10/2018 – 30/09/2026 (1.996 dòng)
- Ngày tải: 26/10/2026
- Người tải: TV2
- Đơn vị: điểm (cột Lần cuối / Price)
- Lý do dùng file tải tay: vnstock (nguồn VCI) trả VN-Index theo nghìn điểm, làm tròn 2 chữ số
  (vd 0.91 = 910 ± 5 điểm) làm méo lợi suất ngày; vnstock chỉ dùng cho lịch phiên giao dịch,
  giá trị đóng cửa lấy từ file này.
- Kết quả đối chiếu (TradingView HOSE:VNINDEX, khung ngày, kiểm tra 26/10/2026 – TV2):
  | Ngày       | Investing | TradingView |
  |------------|-----------|-------------|
  | 31/12/2019 | 960,99    | khớp        |
  | 30/12/2022 | 1.007,09  | khớp        |
  | 30/09/2026 | 1.768,62  | khớp        |
  Kết luận: điểm đóng cửa trùng khớp ở cả 3 ngày → chấp nhận dùng Investing làm chuẩn so sánh VN-Index.