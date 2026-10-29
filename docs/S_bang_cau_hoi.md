# Bước S – Bảng 4 lớp câu hỏi (Mốc 1)

> Người phụ trách: TV1. Số Lớp 1 lấy từ `outputs/lop1_facts.csv` (TV3). Phí, thuế, ERP theo `config.yaml`.

## 1. Lớp 1 – Vấn đề kinh doanh (số thật)

Trong 3 năm gần nhất (03/10/2023–30/09/2026, 745 phiên), danh mục hiện tại – chia đều 1/N trên 28 mã thuộc VN30 kỳ 01/2020, cân bằng lại hằng quý – có **Sharpe 0,734** và **sụt giảm tối đa (MDD) −19,34%** (sau phí), trong khi VN-Index đạt **Sharpe 0,686, MDD −18,11%**. Danh mục hơn thị trường một chút về Sharpe nhưng sụt giảm sâu hơn.

**Quyết định cần đưa ra:** có đổi quy tắc phân bổ tỷ trọng hay không, và tỷ trọng mục tiêu cho kỳ cân bằng Q4/2026 là bao nhiêu.

## 2. Bảng câu hỏi (6 câu, sắp theo ưu tiên)

| # | Câu hỏi kinh doanh | Câu hỏi phân tích | Câu hỏi thống kê | Loại hình | Dữ liệu cần thêm | Hành động dự kiến |
|---|---|---|---|---|---|---|
| 1 | Quy tắc phân bổ nào cho Sharpe sau phí tốt hơn 1/N trên dữ liệu chưa thấy? | Trên test 2022Q1–2026Q3 (1.179 phiên, 19 quý), cân bằng quý, so 4 chiến lược: 1/N, Min Variance, Max Sharpe, Risk Parity; tham số chọn trên validation 2020–2021; tính sau phí/thuế, lô 100 | Sharpe sau phí (không thứ nguyên) của từng chiến lược và chênh lệch so với 1/N; kiểm định bootstrap theo khối, khoảng tin cậy 95%. Cột dùng: `close`, rf, VN-Index. Kỹ thuật: backtest walk-forward + bootstrap | Đề xuất | Không – dữ liệu hiện có đủ (phụ thuộc giả định vũ trụ cố định, xem A1) | Nếu Sharpe sau phí vượt 1/N và chênh lệch có ý nghĩa (khoảng tin cậy không chứa 0) thì đề xuất chuyển; ngược lại giữ 1/N |
| 2 | Tỷ trọng mục tiêu Q4/2026 là gì và có đáng giao dịch sau chi phí không? | Với chiến lược thắng ở câu 1, tính vector tỷ trọng từ dữ liệu đến 30/09/2026, số cổ phiếu mua/bán theo lô 100 và vòng quay | Tỷ trọng wᵢ (%) từng mã; vòng quay (½Σ\|Δw\|) và chi phí giao dịch (điểm % NAV) so với giữ 1/N. Cột: `close`, `volume`. Kỹ thuật: tối ưu có ràng buộc | Đề xuất | Số lượng nắm giữ hiện tại (nếu có); nếu thiếu thì giả định đang ở đúng 1/N | Nếu lợi ích kỳ vọng > chi phí giao dịch thì thực hiện tái cân bằng; ngược lại giữ danh mục |
| 3 | Vì sao 1/N chỉ hơn VN-Index chút ít mà sụt sâu hơn? | Trong 10/2023–09/2026, mã/nhóm nào đóng góp nhiều nhất vào giai đoạn sụt giảm sâu nhất; beta so với VN-Index; tương quan 2022 so với giai đoạn bình thường | Đóng góp vào MDD (điểm %), beta (OLS), tương quan đôi trung bình giai đoạn 2022 vs còn lại và kiểm định chênh lệch (p-value). Cột: `close`. Kỹ thuật: phân rã đóng góp, OLS, kiểm định | Chẩn đoán | Ngành của từng mã (nguồn: HOSE/vnstock; ưu tiên TB); nếu thiếu thì gom cụm theo tương quan | Nếu một nhóm đóng góp lớn vào MDD thì cân nhắc trần theo nhóm; ngược lại giữ cấu hình |
| 4 | Rủi ro/kỳ vọng sinh lời quý tới có đủ tin cậy để dùng làm đầu vào tối ưu không? | Ước lượng Σ (mẫu vs Ledoit–Wolf) và μ (CAPM vs lịch sử) nào dự báo tốt hơn baseline trên test, cửa sổ mở rộng 252 đến 756 phiên | Sai số dự báo (RMSE, điểm % biến động năm) của Σ; so μ với lợi suất thực hiện; khác biệt so baseline có ý nghĩa không. Cột: `close`. Kỹ thuật: dự báo cửa sổ mở rộng | Dự đoán | Không | Nếu Ledoit–Wolf cho sai số thấp hơn mẫu thì dùng làm đầu vào; ngược lại dùng Σ mẫu |
| 5 | Lợi ích đa dạng hóa của 28 mã có đổi theo thời kỳ không? | Tương quan trung bình và tỷ lệ phương sai giải thích bởi thành phần chính thứ nhất theo quý; quý stress so với quý thường | Tương quan đôi trung bình (không thứ nguyên) và % phương sai PC1 theo quý. Cột: `close`. Kỹ thuật: ma trận tương quan, PCA | Mô tả | Không | Nếu tương quan tăng mạnh ở giai đoạn stress thì cảnh báo trong khuyến nghị; ngược lại không điều chỉnh |
| 6 | Quy mô quỹ 100 tỷ có thực thi được không, chi phí giao dịch ăn mòn bao nhiêu? | Khối lượng cần giao dịch mỗi kỳ chiếm bao nhiêu % thanh khoản trung bình ngày (ADV 20 phiên) từng mã; phí + thuế ăn mòn bao nhiêu điểm % lợi suất năm | % ADV theo mã và kỳ; chi phí giao dịch (điểm %/năm) của 1/N và chiến lược thắng; lưới độ nhạy phí (config). Cột: `close`, `volume`. Kỹ thuật: tính trực tiếp | Mô tả | Trượt giá, giá trần/sàn (thiếu; nguồn: dữ liệu khớp lệnh; ưu tiên Thấp); nếu thiếu thì độ nhạy phí | Nếu mã nào vượt ngưỡng % ADV thì chia lệnh nhiều phiên; ngược lại thực hiện một phiên |

## 3. Câu hỏi quyết định (chốt)

Với ràng buộc và chi phí trong `config.yaml`, tái cân bằng hằng quý, **chiến lược nào trong 4 chiến lược cho Sharpe sau phí cao hơn 1/N trên tập test một cách có ý nghĩa thống kê, mà MDD không tệ hơn 1/N; và tỷ trọng mục tiêu Q4/2026 của chiến lược đó là bao nhiêu?**

## 4. Tự kiểm tra và khả thi

- Đủ 4 loại hình: Đề xuất (1, 2), Chẩn đoán (3), Dự đoán (4), Mô tả (5, 6).
- Câu 1, 2, 4, 5 tính được hoàn toàn từ dữ liệu hiện có; câu 3, 6 cần dữ liệu bổ sung nhỏ, có phương án thay thế.
- **Khả thi: Cao, có điều kiện.** Rủi ro: tập test chỉ 19 quý nên sức mạnh thống kê hạn chế; vũ trụ cố định theo VN30 01/2020 gây thiên lệch sống sót thì nêu ở Hạn chế và kèm độ nhạy.
