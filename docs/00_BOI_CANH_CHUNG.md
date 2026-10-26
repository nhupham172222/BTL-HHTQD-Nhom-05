# 00 – BỐI CẢNH CHUNG CỦA NHÓM (đọc trước tiên)

> Môn Hệ Hỗ trợ Quyết định & Trí tuệ Kinh doanh – GV Nguyễn Ngọc Bình Phương
> **Chủ đề 12: Tối ưu hóa danh mục đầu tư cổ phiếu Việt Nam** (Portfolio Optimization & Backtesting)
> Đây là kịch bản đã chốt. Muốn đổi bất kỳ dòng nào → mở Issue trên GitHub, nhóm trưởng (TV1) duyệt rồi mới đổi, và đổi đồng thời ở `config.yaml` + Sổ giả định.

---

## 1. Đề tài trong một câu

Dùng dữ liệu giá cổ phiếu Việt Nam để so sánh 4 cách chia vốn (1/N, Min Variance, Max Sharpe, Risk Parity) bằng **backtest ngoài mẫu sau phí**, rồi đề xuất tỷ trọng cho kỳ tái cân bằng tới.

**Câu hỏi quyết định (dùng nguyên văn trong report, slide, video):**
> Giám đốc đầu tư cần quyết định tỷ trọng mục tiêu cho 15–30 mã thanh khoản cao ở kỳ tái cân bằng tới, để tối đa Sharpe ngoài mẫu sau phí, trong ràng buộc không bán khống, tỷ trọng tối đa mỗi mã và lô 100 cổ phiếu.

**Câu bắt buộc ở report, slide, dashboard:** *Kết quả là bài tập học thuật, không phải khuyến nghị đầu tư.*

---

## 2. Các quyết định đã chốt

| Hạng mục | Quyết định | Ghi chú |
|---|---|---|
| Vai của nhóm | Bộ phận phân tích của một **quỹ mở cổ phiếu (giả định)**, báo cáo cho Giám đốc đầu tư | Theo file thầy |
| KPI | Chính: **Sharpe ngoài mẫu sau phí**. Phụ: lợi suất năm hóa, độ lệch chuẩn, Sortino, MDD, vòng quay | Theo file thầy |
| Vũ trụ cổ phiếu | Danh sách **VN30 kỳ xem xét tháng 1/2020**, chỉ giữ mã có đủ giá từ **11/2018** (số mã chốt theo Nhật ký ETL) | Chọn bằng thông tin có trước giai đoạn kiểm tra → tránh thiên lệch sống sót. *Sửa đổi 26/10: xem mục 6* |
| Dữ liệu | Giá ngày **01/11/2018 → 30/09/2026** + VN-Index + lợi suất TPCP 10 năm | Nguồn: vnstock (cấp miễn phí, tối đa 2.920 ngày lịch sử); TPCP: HNX/nguồn công khai. *Sửa đổi 26/10: xem mục 6* |
| Cửa sổ ước lượng | **Mở rộng tới 3 năm rồi trượt**: dùng toàn bộ dữ liệu có sẵn, tối thiểu 252 phiên, tối đa 756 phiên | Validation: cửa sổ tăng dần (~290 → 756 phiên). Test: luôn đủ 756 phiên như thiết kế gốc. *Sửa đổi 26/10: xem mục 6* |
| Validation | **2020Q1 – 2021Q4**: chỉ dùng để chọn thiết kế (cách ước lượng μ, Σ) | Ghi số phiên của cửa sổ mỗi kỳ (`window_len`) vào `validation_results.csv` |
| Test | **2022Q1 – 2026Q3** (19 quý): chạy **một lần** sau khi đóng băng thiết kế | Có khủng hoảng 2022 |
| Tái cân bằng | Theo **quý**. Tính tỷ trọng bằng dữ liệu đến phiên cuối quý; giao dịch tại giá đóng cửa **phiên đầu quý sau** | Tránh rò rỉ dữ liệu |
| Quy mô quỹ | **100 tỷ đồng**; làm tròn xuống lô 100 cổ phiếu; tiền dư lãi 0 | Giả định thận trọng |
| Tỷ trọng tối đa | **10%/mã**; độ nhạy 5%, 10%, 15%, 20% | Luôn kiểm tra N × w_max ≥ 100% |
| Bán khống | Không (w ≥ 0, tổng = 100%) | |
| Phí giao dịch | **0,15%/chiều + 0,1% thuế khi bán**; độ nhạy 0,10–0,40%/chiều | Giả định – TV2 tìm nguồn |
| Lãi suất phi rủi ro | Lợi suất **TPCP 10 năm**, bình quân theo năm; độ nhạy ±1 điểm % | |
| Lợi suất kỳ vọng μ | **CAPM** (mặc định) so với trung bình lịch sử, chọn trên validation | Phần bù rủi ro: Damodaran |
| Hiệp phương sai Σ | **Ledoit–Wolf** (mặc định) so với Σ mẫu, chọn trên validation | |
| Chiến lược | 1/N, Min Variance, Max Sharpe, Risk Parity; chuẩn so sánh VN-Index | 1/N và VN-Index là baseline |
| "Danh mục hiện tại" (Lớp 1) | **1/N trên vũ trụ**, 3 năm gần nhất 10/2023–09/2026 | Để điền fact Lớp 1 |
| Biến cho mốc 1 & 3 | Biến kết quả: **Sharpe ngoài mẫu**. Biến giải thích: chiến lược, w_max, cách ước lượng Σ, cách ước lượng μ, phí, tần suất tái cân bằng | Đã hỏi thầy xác nhận: ☐ |
| Quy ước tính | 252 phiên/năm; Sortino dùng ngưỡng Rf; turnover = ½·Σ\|w_mới − w_trôi\| | Dùng chung `src/metrics.py` |
| Công cụ | Python 3.11–3.12, **64-bit** (vnstock 5.x, pandas, PyPortfolioOpt, cvxpy, scikit-learn) + **Power BI** | vnstock 5.x cài bằng `pip install --extra-index-url https://vnstocks.com/api/packages vnstock` (không có trên PyPI) |

---

## 3. Bốn cấp độ phân tích (làm đủ cả 4)

| Cấp độ | Việc cụ thể | Đầu ra phải đạt (theo file thầy) | Người |
|---|---|---|---|
| Mô tả | Lợi suất, biến động, MDD từng mã; heatmap tương quan; số liệu Lớp 1 | Bảng KPI, biểu đồ | TV3 |
| Chẩn đoán | Tương quan trung bình **2022 vs bình thường** (kiểm định bootstrap); đóng góp rủi ro từng mã | Giả thuyết được kiểm định; ghi rõ **liên hệ ≠ nhân quả** | TV3 |
| Dự báo | Ước lượng μ (CAPM), Σ (Ledoit–Wolf). Đánh giá: biến động dự báo vs biến động thực tế quý sau, so baseline Σ mẫu | Có baseline, ngoài mẫu, báo cáo sai số (RMSE) | TV4 |
| Đề xuất | Đường biên hiệu quả; backtest 4 chiến lược sau phí; kiểm định chênh lệch Sharpe; lưới độ nhạy; **tỷ trọng đề xuất Q4/2026** | Quy tắc quyết định, có độ nhạy, có kế hoạch kiểm chứng | TV4, TV5 |

---

## 4. Tài liệu gốc và nơi dùng

| Tài liệu | Có ở đâu | Dùng để làm gì |
|---|---|---|
| `BTN_ChuDe.pdf` (hướng dẫn của thầy) | Drive, thư mục `00_Tai_lieu_thay` | Đọc mục 1–4, **Chủ đề 12 (trang 30–32)**, Phụ lục A–D |
| `BTN_Prompt.md` (prompt của thầy) | Drive + `docs/03_PROMPT_BUOC_S_CHU_DE_12.md` | ⚠️ **Chỉ dùng khối Chủ đề 12, cho bước S (mốc 1).** Xem hướng dẫn trong file 03 |
| Kịch bản này | `docs/00_BOI_CANH_CHUNG.md` | Nguồn sự thật duy nhất về các quyết định |
| Phân công | `docs/01_PHAN_CONG_VA_DEADLINE.md` | Ai làm gì, hạn nào, nộp file gì |

---

## 5. Điểm chưa rõ và phương án mặc định

Nếu hỏi được thầy thì theo thầy. Nếu không, nhóm **áp dụng mặc định dưới đây** và ghi rõ cách hiểu trong report (mục 5.1) để thầy thấy nhóm đã cân nhắc.

| Điểm chưa rõ | Mặc định của nhóm | Ghi ở đâu |
|---|---|---|
| Hạn từng mốc | Theo lịch nhóm, nộp đủ trước **08/11** | — |
| "Biến kết quả + ≥5 biến giải thích" | Biến kết quả: Sharpe ngoài mẫu. 6 biến giải thích: chiến lược, w_max, cách ước lượng Σ, cách ước lượng μ, phí, tần suất tái cân bằng | Đề cương Mốc 1, report 5.1 |
| Dấu "…" trong yêu cầu nộp | Nộp thêm mọi thứ file thầy yêu cầu: tóm tắt điều hành, dashboard, Sổ giả định, từ điển dữ liệu, nhật ký ETL, nhật ký AI, slide | Thư mục nộp |
| Link GitHub | **Public** trước khi nộp (thầy mở được không cần đăng nhập) | `GitHub_link.txt` |
| Giai đoạn dữ liệu (file thầy để trống `[__] năm`) | 11/2018–09/2026 (~8 năm), do giới hạn nguồn | Prompt bước S, report 4 và 5.1, phần 7 (hạn chế) |

---

## 6. Lịch sử thay đổi

| Ngày | Thay đổi | Lý do | Người đề xuất / duyệt | Ảnh hưởng |
|---|---|---|---|---|
| 26/10/2026 | Dữ liệu từ 01/2017 → **01/11/2018**; tiêu chí vũ trụ "đủ giá từ 01/2017" → "đủ giá từ 11/2018"; cửa sổ ước lượng trượt cố định 756 phiên → **mở rộng tới 756 phiên** (tối thiểu 252) | vnstock cấp miễn phí chỉ cho tối đa 2.920 ngày lịch sử giá ngày (~từ cuối 10/2018); file thầy không quy định mốc thời gian | TV2 / TV1: ☐ | **Test 2022Q1–2026Q3, Lớp 1, tái cân bằng quý, phí, w_max, chiến lược: không đổi.** TV4: `estimators.py` cắt cửa sổ `start = max(0, i − 756)`, báo lỗi nếu < 252 phiên. TV5: đọc `min_window` từ config, ghi `window_len`. TV3: giai đoạn "bình thường" khi chẩn đoán = 11/2018–12/2021. TV1: cập nhật `config.yaml` + Sổ giả định. |

**Câu ghi trong report (mục 5.1 và phần 7):**
> Do giới hạn của nguồn dữ liệu (vnstock cấp miễn phí: tối đa 2.920 ngày lịch sử), giai đoạn dữ liệu bắt đầu từ 01/11/2018. Giai đoạn validation (2020–2021) dùng cửa sổ ước lượng mở rộng (tối thiểu 252, tối đa 756 phiên); giai đoạn test (2022Q1–2026Q3) giữ cửa sổ trượt 3 năm như thiết kế.
