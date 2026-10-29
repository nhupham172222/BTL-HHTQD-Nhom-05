# A – GIẢ THUYẾT CHIỀU HƯỚNG (Mốc 3)

> Người soạn: TV3. Người chốt cùng: TV1. Soạn ngày **29/10/2026**, **trước khi có bất kỳ kết quả backtest nào** (lúc soạn, `src/backtest.py`, `src/estimators.py`, `src/optimizers.py` còn là khung; `outputs/` chưa có file kết quả nào ngoài `lop1_facts.csv`).
> Sau 03/11 **không sửa** nội dung bảng này. Nếu muốn đổi, thêm dòng mới ở mục 4 (nhật ký chỉnh sửa), không xóa dòng cũ. Report 5.5 phải đối chiếu từng giả thuyết: **ủng hộ / không ủng hộ / chưa kết luận**.
> *Kết quả là bài tập học thuật, không phải khuyến nghị đầu tư.* Các giả thuyết dưới đây nêu **liên hệ**, không khẳng định nhân quả.

## 1. Khung

- **Biến kết quả:** Sharpe ngoài mẫu **sau phí** trên tập test 2022Q1–2026Q3 (19 quý). Biến phụ: MDD, vòng quay.
- **Quy ước so sánh:** mỗi lần chỉ đổi **một** biến, giữ các biến khác ở mặc định của `config.yaml` (w_max 10%, quý, phí 0,15%/chiều + 0,1% thuế bán, μ CAPM, Σ Ledoit–Wolf).
- **Tính "ủng hộ":** chiều của chênh lệch Sharpe đúng như giả thuyết **và** khoảng bootstrap khối 95% của chênh lệch không chứa 0. Đúng chiều nhưng khoảng chứa 0 → ghi "đúng chiều, chưa đủ bằng chứng".
- **Cảnh báo cỡ mẫu:** 19 quý (~1.150 phiên) là ít; nhiều chênh lệch có thể không có ý nghĩa thống kê. Điều đó cũng là một kết quả cần báo cáo, không phải thất bại.
- **Vũ trụ:** 29 mã (POW loại; ROS ngừng giao dịch từ 11/08/2022 nên vắng mặt ở các kỳ sau đó). Mọi ràng buộc phải thỏa N × w_max ≥ 100% (với w_max = 5%: 28 × 5% = 140%, đạt).

## 2. Bảng giả thuyết cho 6 biến giải thích

| # | Biến giải thích (các mức) | Giả thuyết chiều hướng về Sharpe ngoài mẫu sau phí | Cơ sở (lý thuyết / thực nghiệm đã biết) | Cách kiểm tra | Kết quả nào thì bác bỏ giả thuyết |
|---|---|---|---|---|---|
| H1 | **Chiến lược** (1/N, Min Variance, Max Sharpe, Risk Parity) | (a) Min Variance và Risk Parity **không thấp hơn** 1/N, nhờ MDD và biến động thấp hơn trong giai đoạn giảm 2022. (b) Max Sharpe **không cao hơn** 1/N một cách ổn định và có vòng quay cao nhất. Thứ tự dự kiến: Risk Parity ≈ Min Variance ≥ 1/N ≥ Max Sharpe. | Sai số ước lượng μ lớn hơn nhiều so với sai số ước lượng Σ nên chiến lược dựa vào μ thường mất lợi thế ngoài mẫu; 1/N thường khó thắng (DeMiguel, Garlappi & Uppal, 2009). Min Variance và Risk Parity chỉ cần Σ. | Bảng Sharpe sau phí theo chiến lược; kiểm định chênh lệch Sharpe bằng bootstrap khối (từng cặp với 1/N). | (a) bị bác bỏ nếu Sharpe của Min Variance **và** Risk Parity đều thấp hơn 1/N với khoảng bootstrap không chứa 0. (b) bị bác bỏ nếu Max Sharpe cao hơn 1/N ở khoảng bootstrap không chứa 0. |
| H2 | **Tỷ trọng tối đa w_max** (5%, 10%, 15%, 20%) | Với Max Sharpe: tăng w_max làm Sharpe ngoài mẫu **giảm** (tập trung vào vài mã). Với Min Variance: Sharpe **tăng nhẹ rồi bão hòa**. Với 1/N và Risk Parity: **gần như không đổi** (ràng buộc ít khi chạm). | Ràng buộc trên w_max đóng vai trò chính quy hóa, hạn chế danh mục ôm vài mã có ước lượng đẹp do nhiễu. | Lưới độ nhạy theo w_max, ghi thêm số mã có w > 0 mỗi kỳ. | Bị bác bỏ nếu Max Sharpe có Sharpe **tăng đơn điệu** theo w_max với chênh lệch khác 0 có ý nghĩa; hoặc 1/N đổi Sharpe (1/N không chạm ràng buộc, nếu đổi là lỗi code). |
| H3 | **Cách ước lượng Σ** (Ledoit–Wolf so với Σ mẫu) | Ledoit–Wolf cho Sharpe ngoài mẫu **cao hơn hoặc bằng** Σ mẫu với Min Variance và Max Sharpe; **RMSE biến động dự báo thấp hơn**. Với 1/N: không ảnh hưởng. Với Risk Parity: ảnh hưởng nhỏ. | Σ mẫu nhiễu khi số mã so với số quan sát không nhỏ (29 mã; 252–756 phiên); co về mục tiêu có cấu trúc giảm sai số (Ledoit & Wolf, 2004). Khác biệt lớn nhất ở kỳ validation (cửa sổ ngắn). | RMSE dự báo (TV4) và Sharpe ngoài mẫu theo từng Σ, cùng μ cùng w_max. | Bị bác bỏ nếu RMSE của Ledoit–Wolf **cao hơn** Σ mẫu và Sharpe cũng thấp hơn ở Min Variance. |
| H4 | **Cách ước lượng μ** (CAPM so với trung bình lịch sử) | μ theo CAPM cho Max Sharpe Sharpe ngoài mẫu **cao hơn hoặc bằng** μ trung bình lịch sử. μ **không ảnh hưởng** Min Variance, Risk Parity, 1/N (không dùng μ). | Trung bình lịch sử ngắn rất nhiễu và bám theo giai đoạn đã qua; CAPM ép μ theo beta nên ổn định hơn. Hạn chế: CAPM phụ thuộc phần bù rủi ro (A12) và beta ước lượng. | So Max Sharpe với hai cách μ, giữ Σ và w_max cố định. | Bị bác bỏ nếu Max Sharpe với μ lịch sử cao hơn μ CAPM có ý nghĩa; hoặc nếu μ làm đổi kết quả Min Variance/Risk Parity/1/N (là lỗi code). |
| H5 | **Phí giao dịch** (0,10%, 0,15%, 0,25%, 0,40% mỗi chiều) | Phí tăng → Sharpe sau phí **giảm đơn điệu**. Mức giảm xếp theo vòng quay: Max Sharpe > Min Variance > Risk Parity > 1/N. Xếp hạng các chiến lược **có thể đổi chỗ** ở phí cao. | Chi phí tỷ lệ với vòng quay; 1/N chỉ trôi tỷ trọng theo giá nên vòng quay thấp nhất. | Lưới độ nhạy theo phí; so Sharpe trước và sau phí. | Bị bác bỏ nếu Sharpe sau phí không giảm khi phí tăng (nghi lỗi tính phí), hoặc nếu chiến lược vòng quay thấp hơn lại mất nhiều hơn. |
| H6 | **Tần suất tái cân bằng** (tháng, quý, nửa năm) | Tăng tần suất → vòng quay và phí **tăng**; Sharpe **sau phí** không tăng đáng kể (không đổi hoặc giảm), đặc biệt với Max Sharpe. Trước phí: gần như không đổi. | Ước lượng μ, Σ đổi chậm hơn nhịp tái cân bằng hằng tháng; thêm giao dịch chủ yếu thêm chi phí. | Lưới độ nhạy theo tần suất; vòng quay trung bình mỗi năm. | Bị bác bỏ nếu tái cân bằng theo tháng cho Sharpe sau phí **cao hơn** theo quý, khoảng bootstrap không chứa 0. |

## 3. Giả thuyết cho cấp độ Chẩn đoán (kiểm định riêng, TV3)

| # | Giả thuyết | Kiểm định | Bác bỏ khi |
|---|---|---|---|
| H7 | Tương quan đôi trung bình giữa các mã trong **2022** **cao hơn** giai đoạn "bình thường" (11/2018–12/2021, định nghĩa theo `00_BOI_CANH_CHUNG.md` mục 6). Ý nghĩa quản trị: lợi ích đa dạng hóa giảm khi thị trường giảm mạnh. | Bootstrap theo khối trên chênh lệch tương quan trung bình (2022 trừ bình thường); báo khoảng 95%. | Khoảng 95% của chênh lệch chứa 0 hoặc âm. |

Ghi chú diễn giải: viết "có liên hệ với", không viết "gây ra". Giai đoạn 2022 chỉ là **một** giai đoạn, nên không khái quát hóa thành quy luật.

## 4. Nhật ký chỉnh sửa (chỉ thêm dòng, không xóa)

| Ngày | Người | Thay đổi | Lý do |
|---|---|---|---|
| 29/10/2026 | TV3 | Soạn bản đầu H1–H7 | Mốc 3. Chờ TV1 xem và chốt. |

## 5. Nguồn lý thuyết (để TV6 đưa vào Tài liệu tham khảo; kiểm tra lại thông tin trích dẫn trước khi nộp)

- DeMiguel, V., Garlappi, L., Uppal, R. (2009). *Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?* Review of Financial Studies, 22(5).
- Ledoit, O., Wolf, M. (2004). *A well-conditioned estimator for large-dimensional covariance matrices.* Journal of Multivariate Analysis, 88(2).
