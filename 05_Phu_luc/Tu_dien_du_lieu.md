# Từ điển dữ liệu (bước O)

Đề tài 12 – Tối ưu hóa danh mục cổ phiếu Việt Nam. Người phụ trách: TV2. Cập nhật lần cuối: 26/10/2026

## 1. Tổng quan
| Mục | Giá trị |
|---|---|
| Vũ trụ | 30 mã VN30 kỳ xem xét 01/2020 (hiệu lực 03/02/2020 – 31/07/2020) |
| Giai đoạn | 01/11/2018 – 30/09/2026, tần suất ngày (A14: giới hạn vnstock miễn phí 2.920 ngày) |
| Nguồn giá | vnstock (nguồn VCI), lấy ngày 26/10/2026; phiên bản vnstock: 5.2.0 |
| Nguồn VN-Index | Lịch giao dịch: vnstock (VNINDEX). Điểm đóng cửa: Investing.com (https://www.investing.com/indices/vn-historical-data), tải 26/10/2026, file `vnindex_manual.csv` – vì vnstock chỉ cho 2 chữ số theo nghìn điểm (±5 điểm). Đối chiếu TradingView: khớp |
| Nguồn lãi suất | Lợi suất TPCP 10 năm: Investing.com (https://www.investing.com/rates-bonds/vietnam-10-year-bond-yield-historical-data), tải 26/10/2026; đối chiếu TradingView: khớp; chi tiết: data/raw/tpcp10y_SOURCE.md |
| Điều chỉnh giá | Có. Đối chiếu HPG: cổ tức 30% cổ phiếu, GDKHQ 17/06/2022 – giá vnstock chỉ −1,13% (chưa điều chỉnh sẽ giảm ~23%) |

## 2. Các file

### data/raw/
| File | Mô tả | Cột |
|---|---|---|
| `vn30_2020.csv` | Danh sách 30 mã VN30 kỳ 01/2020 | stt, ticker, free_float_pct, effective_from, effective_to, source |
| `px_<MÃ>.csv` | Giá thô từng mã, đúng như vnstock trả về | time, open, high, low, close, volume |
| `vnindex.csv` | VN-Index thô từ vnstock (dùng làm lịch giao dịch) | time, open, high, low, close (nghìn điểm), volume |
| `vnindex_manual.csv` | VN-Index đóng cửa tải tay (Investing), dùng thay giá trị vnstock vì vnstock chỉ chính xác ±5 điểm | Date, Price (điểm) |
| `tpcp10y.csv` | Lợi suất TPCP 10 năm thô | date, yield_pct |

### data/processed/
| File | Mô tả | Cột / cấu trúc |
|---|---|---|
| `prices.csv` | Giá đóng cửa đã làm sạch | `date` + 1 cột/mã (VND/cổ phiếu) |
| `prices_imputed.csv` | Cờ điền thiếu, cùng kích thước prices.csv | 1 = giá được điền từ phiên trước, 0 = giá thật |
| `vnindex.csv` | VN-Index đóng cửa (benchmark) | date, close (điểm) |
| `rf.csv` | Lãi suất phi rủi ro | date, rf_annual (số thập phân, 0.045 = 4,5%/năm), rf_daily = (1+rf_annual)^(1/252) − 1, rf_annual_avg_year (bình quân năm dương lịch – A9, chỉ dùng tính Sharpe/Sortino) |
| `events.csv` | Mã ngừng giao dịch / thiếu giá dài **sau** kỳ quyết định đầu (giữ trong prices.csv để tránh thiên lệch sống sót) | ticker, event (`dung_giao_dich`/`thieu_dai`), start, end, sessions, last_close, note |
| `etl_log.json` | Số liệu thô của nhật ký ETL | — |

### 05_Phu_luc/
| File | Mô tả | Ghi chú |
|---|---|---|
| `Nhat_ky_ETL.md` / `.docx` | Nhật ký ETL | Sinh tự động mỗi lần chạy run_all.py |
| `ghi_chu_thu_cong.md` | Ghi chú tay: ngoại lệ, kết quả đối chiếu | Không bị ghi đè; được gộp vào Nhật ký |
| `Tu_dien_du_lieu.md` / `.xlsx` | Từ điển dữ liệu | Sửa file .md; .xlsx sinh tự động |

## 3. Định nghĩa biến
| Biến | Đơn vị | Ý nghĩa | Ghi chú |
|---|---|---|---|
| date | YYYY-MM-DD | Phiên giao dịch HOSE | Lịch chung = các phiên của VN-Index |
| close | VND/cổ phiếu | Giá đóng cửa đã điều chỉnh | vnstock trả nghìn đồng → `clean.py` nhân 1.000 |
| imputed | 0/1 | Ô giá được điền từ phiên trước | Tối đa 5 phiên liên tiếp |
| rf_annual | /năm, thập phân | Lợi suất TPCP 10 năm | Lấy giá trị gần nhất không nhìn trước tương lai |
| rf_daily | /phiên | Quy đổi 252 phiên/năm | Dùng cho Sharpe/backtest |
| rf_annual_avg_year | /năm, thập phân | Trung bình rf_annual trong năm dương lịch (A9) | Không dùng khi ra quyết định tại t (nhìn trước tương lai); dùng rf_annual tại t cho CAPM |

## 4. Quy tắc xử lý
- Điền thiếu: giá phiên trước, tối đa 5 phiên, có cờ `imputed`. Thiếu dài hơn: giữ NaN, ghi vào Nhật ký ETL, loại mã ở kỳ tái cân bằng kế tiếp.
- Mã thiếu lịch sử (dữ liệu bắt đầu sau 11/11/2018) bị loại khỏi vũ trụ. Danh sách mã loại: xem Nhật ký ETL.
- Không điền trước ngày niêm yết, không điền sau ngày dữ liệu kết thúc.
- Mã ngừng giao dịch/hủy niêm yết sau kỳ quyết định đầu (01/2020) **không bị loại khỏi file**: giữ giá tới ngày cuối, sau đó NaN, ghi vào `events.csv`; backtest bán/loại ở kỳ tái cân bằng kế tiếp.
- Mã có đoạn thiếu > 5 phiên trước kỳ quyết định đầu bị loại (không đủ giá liên tục – A1).

## 5. Hạn chế đã biết (ghi thẳng vào report)
- **Survivorship bias**: vũ trụ cố định theo danh sách VN30 01/2020 → mã sau này bị loại khỏi VN30 vẫn có mặt, mã mới vào VN30 sau 2020 không có mặt. Kết quả backtest trước 2020 có look-ahead về thành phần rổ.
- Nguồn giá bên thứ ba (vnstock), không phải dữ liệu trực tiếp HOSE.
- Giá điều chỉnh có thể sai lệch so với giá giao dịch thực tế; cần đối chiếu mẫu (ghi ở mục 1).