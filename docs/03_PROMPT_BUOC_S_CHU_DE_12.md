# 03 – CÁCH DÙNG FILE PROMPT CỦA THẦY (BTN_Prompt.md)

> **Dùng ở đâu:** chỉ ở **bước S, Mốc 1 (hạn T5 29/10)**, người chạy là **TV1**, số liệu do **TV3** cung cấp.
> **Dùng khối nào:** chỉ khối **"Chủ đề 12"** trong `BTN_Prompt.md`. Các chủ đề khác và "Template chung" **không dùng** (template chung chỉ dành cho nhóm tự đề xuất đề tài).

## 1. Prompt này làm ra cái gì?

AI trả về **bảng 6 cột** (Câu hỏi kinh doanh | Câu hỏi phân tích | Câu hỏi thống kê | Loại hình | Dữ liệu cần thu thập thêm | Hành động dự kiến) + câu hỏi quyết định chốt + tự kiểm tra + mức khả thi.
Bảng này **không nộp nguyên xi**. Nhóm sửa lại thành bảng của mình, rồi dùng ở 4 chỗ:

| Đầu ra của prompt | Đưa vào đâu | Ai dùng |
|---|---|---|
| Bảng 6 cột (đã sửa) | Đề cương Mốc 1; report **phần 3 (S)** + **phụ lục D** | TV1 |
| Cột "Dữ liệu cần thu thập thêm" | Danh sách dữ liệu bổ sung + **Sổ giả định** | TV2, TV1 |
| Cột "Hành động dự kiến" | Khung cho **2 khuyến nghị** ở phần 6 và tóm tắt điều hành | TV1, TV5 |
| Prompt + phản hồi nguyên văn + phần giữ/sửa/bỏ | **Nhật ký AI** → phụ lục minh bạch AI | TV1 |

## 2. Các bước (TV1 làm)

1. **Nhận số từ TV3** (`outputs/lop1_facts.csv`): Sharpe và MDD của danh mục 1/N và của VN-Index, giai đoạn 10/2023–09/2026. **Không để AI tự nghĩ số.**
2. **Điền các ô `[__]`** trong bản ở mục 4 bên dưới (bản đã điền sẵn bối cảnh nhóm; chỉ còn ô số).
3. **Dán toàn bộ khối** vào công cụ AI (ChatGPT/Claude/Gemini…), mở cuộc trò chuyện mới.
4. **Kiểm tra phản hồi** theo checklist mục 3.
5. **Lưu vào Nhật ký AI:** ngày, công cụ + phiên bản, prompt nguyên văn, phản hồi nguyên văn (có thể dán link chia sẻ cuộc trò chuyện), rồi ghi từng dòng của bảng: **giữ / sửa / bỏ + lý do**.
6. **Sửa bảng** thành `docs/S_bang_cau_hoi.md`, rồi viết đề cương 1 trang.

## 3. Checklist kiểm tra phản hồi AI

- [ ] Lớp 1 được nhắc lại đúng số nhóm đã điền.
- [ ] Có 5–7 câu hỏi kinh doanh, sắp theo ưu tiên.
- [ ] Mọi câu hỏi thống kê chỉ dùng cột có thật: `time, open, high, low, close, volume`, VN-Index, lãi suất phi rủi ro. Cột nào khác phải nằm ở cột "Dữ liệu cần thu thập thêm".
- [ ] Mỗi câu hỏi thống kê **tính được** bằng một phép tính cụ thể, có đơn vị.
- [ ] Có đủ 4 loại hình: Mô tả, Chẩn đoán, Dự đoán, Đề xuất. Ít nhất một câu Đề xuất trả lời thẳng câu hỏi quyết định.
- [ ] Câu hỏi khớp kịch bản nhóm (1/N, Min Var, Max Sharpe, Risk Parity; backtest quý; test 2022–2026Q3). Câu nào ngoài phạm vi (phái sinh, trái phiếu DN, dự đoán giá từng mã) → bỏ, ghi lý do.
- [ ] AI không đưa con số kết quả. Nếu có → bỏ, ghi vào nhật ký.

## 4. Bản đã điền bối cảnh nhóm (TV1 chỉ điền các ô `[__]`)

Những chỗ nhóm điều chỉnh so với bản gốc của thầy (ghi lại vào Nhật ký AI): định nghĩa "danh mục hiện tại" = 1/N; tỷ trọng tối đa 10%; quy mô và khung thời gian dữ liệu; thêm lô 100 cổ phiếu và phí giao dịch vào ràng buộc. Các phần A, B, Quy tắc, Trình bày **giữ nguyên** như thầy.

```text
VAI TRÒ CỦA AI
Bạn là chuyên gia phân tích kinh doanh, hỗ trợ tôi thực hiện bước S (Specify the question) của mô hình SOAR. Ở bước này chỉ giúp tôi đặt đúng câu hỏi: KHÔNG phân tích dữ liệu, KHÔNG đưa ra số liệu hay kết luận.

BỐI CẢNH
Tôi là Giám đốc đầu tư tại một quỹ mở cổ phiếu (bối cảnh giả định), quy mô giả định 100 tỷ đồng.

LỚP 1) VẤN ĐỀ KINH DOANH – fact đã biết (rộng, có số liệu và mốc so sánh)
“Trong 3 năm qua (10/2023–09/2026), danh mục hiện tại (chia đều 1/N trên [__] mã thuộc VN30 kỳ xem xét 1/2020) có Sharpe [__] và sụt giảm tối đa [__]%, so với VN-Index là [__] và [__]%.”
Nguồn của fact: giá đóng cửa đã điều chỉnh tải bằng vnstock; Sharpe năm hóa (252 phiên, lãi suất phi rủi ro = lợi suất TPCP 10 năm), MDD tính trên giá trị danh mục theo ngày.

QUYẾT ĐỊNH cần đưa ra sau phân tích
“Xác định tỷ trọng mục tiêu cho kỳ tái cân bằng tới.”
KPI đánh giá quyết định: Sharpe; sụt giảm tối đa; vòng quay danh mục.
Ràng buộc: không bán khống; tối đa 10% mỗi mã; thanh khoản tối thiểu (vũ trụ VN30); lô 100 cổ phiếu; phí giao dịch 0,15%/chiều + 0,1% thuế khi bán; tái cân bằng theo quý.

PHẠM VI phân tích
- Chỉ tập trung vào: 15–30 cổ phiếu thanh khoản cao (ví dụ VN30).
- KHÔNG xét đến: phái sinh, trái phiếu doanh nghiệp.

DỮ LIỆU TÔI ĐANG CÓ
- Tên bộ dữ liệu/nguồn: Giá cổ phiếu Việt Nam (vnstock).
- Đơn vị quan sát (mỗi dòng là gì): mã – ngày.
- Quy mô và khung thời gian: [__] mã, giá ngày 01/2017–09/2026 (khoảng 9,75 năm); validation 2020–2021, test 2022Q1–2026Q3.
- Các cột dữ liệu (ghi đúng tên cột): time, open, high, low, close (đã điều chỉnh), volume; VN-Index; lãi suất phi rủi ro.
- Hạn chế đã biết: thiên lệch sống sót; cần kiểm tra điều chỉnh cổ tức và chia tách.

════════════════════════════════════════
PHẦN A — MÔ HÌNH 4 LỚP CÂU HỎI (phễu thu hẹp: Vấn đề kinh doanh → Câu hỏi kinh doanh → Câu hỏi phân tích → Câu hỏi thống kê)
════════════════════════════════════════
Lớp 1 (Vấn đề kinh doanh) là fact đã nêu ở trên: rộng, mơ hồ, chưa phân tích trực tiếp được. Hãy thu hẹp dần qua các lớp 2–4 dưới đây.

LỚP 2) CÂU HỎI KINH DOANH (thu hẹp phạm vi) – đặt 5–7 câu, sắp xếp theo ưu tiên
- Là câu hỏi mở, ngôn ngữ quản lý, KHÔNG gắn số liệu cụ thể; chỉ nằm trong PHẠM VI.
- Mục đích: định hướng điều tra nguyên nhân của VẤN ĐỀ KINH DOANH và phục vụ QUYẾT ĐỊNH ở trên.
- Ưu tiên = mức ảnh hưởng tới QUYẾT ĐỊNH × khả năng trả lời bằng dữ liệu đang có.
- Ví dụ dạng: “[Yếu tố nào] thay đổi nhanh nhất và ở [phạm vi nào]?”

LỚP 3) CÂU HỎI PHÂN TÍCH (gắn với dữ liệu) – tương ứng với mỗi câu hỏi kinh doanh
- Chuyển câu hỏi kinh doanh thành yêu cầu đo lường được.
- Phải gắn cụ thể: tên đơn vị/phạm vi, khoảng thời gian so sánh, chỉ số liên quan (kèm định nghĩa công thức).
- Ví dụ dạng: “[Chỉ số X] tại [đơn vị Y] đã thay đổi bao nhiêu % trong [kỳ A] so với [kỳ B]?”

LỚP 4) CÂU HỎI THỐNG KÊ (đo lường cụ thể) – tương ứng với mỗi câu hỏi phân tích
- Là câu hỏi trả lời trực tiếp được bằng một phép tính cụ thể trên dữ liệu, cho ra một con số với đơn vị đo rõ ràng.
- Ghi rõ: (i) các cột sử dụng, đúng tên; (ii) phép tính/kỹ thuật (tổng, trung bình, tỷ lệ, kiểm định, hồi quy, mô hình dự báo, tối ưu hóa, mô phỏng…); (iii) đơn vị đo của kết quả.
- Ví dụ dạng: “[Chỉ số cụ thể] trung bình/tổng tại [đơn vị Y]: [kỳ A] vs [kỳ B] là bao nhiêu [đơn vị đo]?”

MINH HỌA MỘT CHUỖI 4 LỚP
- Lớp 1 – Vấn đề kinh doanh: “Lợi nhuận quý này giảm 12% so với quý trước.”
- Lớp 2 – Câu hỏi kinh doanh: “Chi phí nào tăng nhanh nhất và ở khu vực nào?”
- Lớp 3 – Câu hỏi phân tích: “Chi phí nguyên liệu tại chi nhánh Đà Nẵng đã tăng bao nhiêu % trong Q3 so với Q2?”
- Lớp 4 – Câu hỏi thống kê: “Giá vốn hàng bán (COGS) trung bình/đơn hàng tại Đà Nẵng: Q2 vs Q3 là bao nhiêu VNĐ?”

PHÂN LOẠI LOẠI HÌNH CÂU HỎI (thuộc tính của mỗi chuỗi câu hỏi, không phải một lớp)
- Gắn mỗi câu hỏi kinh doanh (và chuỗi câu hỏi đi kèm) với một loại hình: Mô tả (điều gì đã xảy ra?) / Chẩn đoán (vì sao?) / Dự đoán (điều gì có thể xảy ra?) / Đề xuất (nên làm gì?).
- Khuyến khích bộ câu hỏi phủ đủ 4 loại hình nhưng không bắt buộc: nếu với QUYẾT ĐỊNH này một loại hình không cần thiết, bỏ qua và nêu lý do. Ít nhất một câu phải trả lời trực tiếp QUYẾT ĐỊNH.
- Ví dụ dạng câu hỏi kinh doanh theo loại hình:
    • Mô tả: “[Yếu tố nào] thay đổi nhanh nhất và ở [phạm vi nào]?”
    • Chẩn đoán: “Vì sao [kết quả] ở [phạm vi nào] lại [tăng/giảm]?”
    • Dự đoán: “[Kết quả] sẽ diễn biến thế nào trong [kỳ tới] nếu [điều kiện] giữ nguyên?”
    • Đề xuất: “Nên [hành động nào] với [đối tượng nào] để đạt [mục tiêu] trong [ràng buộc]?”
- Ví dụ dạng câu hỏi thống kê theo loại hình (ngoài dạng Mô tả ở Lớp 4):
    • Chẩn đoán: “Chênh lệch trung bình [cột X] giữa [nhóm 1] và [nhóm 2] là bao nhiêu [đơn vị đo], p-value của kiểm định [t / chi-bình phương] là bao nhiêu?”
    • Dự đoán: “Mô hình [tên] dùng [các cột] dự báo [cột mục tiêu] cho [kỳ tới] có sai số [MAPE/RMSE/AUC] bao nhiêu trên tập kiểm tra [kỳ C]?”
    • Đề xuất: “Với [ràng buộc], giá trị tối ưu của [biến quyết định] là bao nhiêu và [KPI] tăng thêm bao nhiêu [đơn vị đo] so với hiện trạng?”

════════════════════════════════════════
PHẦN B — HAI YÊU CẦU BỔ SUNG
════════════════════════════════════════

BỔ SUNG 1) DỮ LIỆU CẦN THU THẬP THÊM – kiểm tra từng câu hỏi thống kê
- Nếu dữ liệu đang có đã đủ: ghi “Đủ dữ liệu hiện có”.
- Nếu chưa đủ, chỉ rõ: a. tên trường còn thiếu; b. nguồn có thể thu thập; c. mức ưu tiên (Cao/Trung bình/Thấp); d. nếu không thu thập được (dữ liệu công khai), đề xuất biến thay thế hoặc giả định có căn cứ và cách kiểm tra độ nhạy.
- Ví dụ: “Thiếu giá vốn theo sản phẩm – nguồn: phần mềm kế toán hoặc BCTC doanh nghiệp cùng ngành – ưu tiên Cao – nếu không có: giả định biên gộp theo danh mục, kiểm tra độ nhạy ±5 điểm %.”

BỔ SUNG 2) HÀNH ĐỘNG DỰ KIẾN – cho mỗi câu hỏi kinh doanh
- Viết dạng: “Nếu [chỉ số] [>/<] [ngưỡng] thì [hành động A]; ngược lại [hành động B]”. Nếu chưa biết ngưỡng, ghi ngưỡng là tham số cần xác định và cách xác định.
- Ví dụ: “Nếu tỷ lệ giao trễ ở vùng Y > 15% → mở kho vệ tinh tại Y; ngược lại → giữ mạng lưới hiện tại và điều chỉnh cam kết thời gian giao.”

════════════════════════════════════════
QUY TẮC CHO AI
════════════════════════════════════════
- Không bịa trường dữ liệu: chỉ dùng các cột đã liệt kê; mọi trường khác phải đưa vào cột “Dữ liệu cần thu thập thêm”.
- Không trả lời các câu hỏi, không đưa số liệu giả định như thể là kết quả.
- Nếu bối cảnh hoặc dữ liệu chưa đủ để đặt câu hỏi tốt, nêu điểm thiếu ở đầu câu trả lời, rồi vẫn lập bảng với giả định tạm thời được ghi rõ.

════════════════════════════════════════
YÊU CẦU TRÌNH BÀY
════════════════════════════════════════
- 1. Nhắc lại LỚP 1 (Vấn đề kinh doanh) ở đầu câu trả lời, sau đó lập bảng, mỗi dòng 6 cột: [Câu hỏi kinh doanh (đã sắp ưu tiên) | Câu hỏi phân tích | Câu hỏi thống kê | Loại hình câu hỏi | Dữ liệu cần thu thập thêm (nếu có) | Hành động dự kiến].
- 2. Dưới bảng: (a) CÂU HỎI QUYẾT ĐỊNH CHỐT, viết trong một câu; (b) tự kiểm tra: số câu theo từng loại hình, số câu thống kê “Đủ dữ liệu hiện có”, các câu phải dựa vào giả định; (c) đánh giá mức khả thi của đề tài với dữ liệu hiện có (Cao/Trung bình/Thấp) và lý do.
```

## 5. Bản gốc của thầy (đối chiếu, không sửa)

```text
VAI TRÒ CỦA AI
Bạn là chuyên gia phân tích kinh doanh, hỗ trợ tôi thực hiện bước S (Specify the question) của mô hình SOAR. Ở bước này chỉ giúp tôi đặt đúng câu hỏi: KHÔNG phân tích dữ liệu, KHÔNG đưa ra số liệu hay kết luận.

BỐI CẢNH
Tôi là Giám đốc đầu tư tại một quỹ mở cổ phiếu (bối cảnh giả định).

LỚP 1) VẤN ĐỀ KINH DOANH – fact đã biết (rộng, có số liệu và mốc so sánh)
“Trong 3 năm qua, danh mục hiện tại có Sharpe [__] và sụt giảm tối đa [__]%, so với VN-Index là [__] và [__]%.”
Nguồn của fact: giá đóng cửa đã điều chỉnh tải bằng vnstock.

QUYẾT ĐỊNH cần đưa ra sau phân tích
“Xác định tỷ trọng mục tiêu cho kỳ tái cân bằng tới.”
KPI đánh giá quyết định: Sharpe; sụt giảm tối đa; vòng quay danh mục.
Ràng buộc: không bán khống; tối đa [__]% mỗi mã; thanh khoản tối thiểu.

PHẠM VI phân tích
- Chỉ tập trung vào: 15–30 cổ phiếu thanh khoản cao (ví dụ VN30).
- KHÔNG xét đến: phái sinh, trái phiếu doanh nghiệp.

DỮ LIỆU TÔI ĐANG CÓ
- Tên bộ dữ liệu/nguồn: Giá cổ phiếu Việt Nam (vnstock).
- Đơn vị quan sát (mỗi dòng là gì): mã – ngày.
- Quy mô và khung thời gian: [__] năm.
- Các cột dữ liệu (ghi đúng tên cột): time, open, high, low, close (đã điều chỉnh), volume; VN-Index; lãi suất phi rủi ro.
- Hạn chế đã biết: thiên lệch sống sót; cần kiểm tra điều chỉnh cổ tức và chia tách.

════════════════════════════════════════
PHẦN A — MÔ HÌNH 4 LỚP CÂU HỎI (phễu thu hẹp: Vấn đề kinh doanh → Câu hỏi kinh doanh → Câu hỏi phân tích → Câu hỏi thống kê)
════════════════════════════════════════
Lớp 1 (Vấn đề kinh doanh) là fact đã nêu ở trên: rộng, mơ hồ, chưa phân tích trực tiếp được. Hãy thu hẹp dần qua các lớp 2–4 dưới đây.

LỚP 2) CÂU HỎI KINH DOANH (thu hẹp phạm vi) – đặt 5–7 câu, sắp xếp theo ưu tiên
- Là câu hỏi mở, ngôn ngữ quản lý, KHÔNG gắn số liệu cụ thể; chỉ nằm trong PHẠM VI.
- Mục đích: định hướng điều tra nguyên nhân của VẤN ĐỀ KINH DOANH và phục vụ QUYẾT ĐỊNH ở trên.
- Ưu tiên = mức ảnh hưởng tới QUYẾT ĐỊNH × khả năng trả lời bằng dữ liệu đang có.
- Ví dụ dạng: “[Yếu tố nào] thay đổi nhanh nhất và ở [phạm vi nào]?”

LỚP 3) CÂU HỎI PHÂN TÍCH (gắn với dữ liệu) – tương ứng với mỗi câu hỏi kinh doanh
- Chuyển câu hỏi kinh doanh thành yêu cầu đo lường được.
- Phải gắn cụ thể: tên đơn vị/phạm vi, khoảng thời gian so sánh, chỉ số liên quan (kèm định nghĩa công thức).
- Ví dụ dạng: “[Chỉ số X] tại [đơn vị Y] đã thay đổi bao nhiêu % trong [kỳ A] so với [kỳ B]?”

LỚP 4) CÂU HỎI THỐNG KÊ (đo lường cụ thể) – tương ứng với mỗi câu hỏi phân tích
- Là câu hỏi trả lời trực tiếp được bằng một phép tính cụ thể trên dữ liệu, cho ra một con số với đơn vị đo rõ ràng.
- Ghi rõ: (i) các cột sử dụng, đúng tên; (ii) phép tính/kỹ thuật (tổng, trung bình, tỷ lệ, kiểm định, hồi quy, mô hình dự báo, tối ưu hóa, mô phỏng…); (iii) đơn vị đo của kết quả.
- Ví dụ dạng: “[Chỉ số cụ thể] trung bình/tổng tại [đơn vị Y]: [kỳ A] vs [kỳ B] là bao nhiêu [đơn vị đo]?”

MINH HỌA MỘT CHUỖI 4 LỚP
- Lớp 1 – Vấn đề kinh doanh: “Lợi nhuận quý này giảm 12% so với quý trước.”
- Lớp 2 – Câu hỏi kinh doanh: “Chi phí nào tăng nhanh nhất và ở khu vực nào?”
- Lớp 3 – Câu hỏi phân tích: “Chi phí nguyên liệu tại chi nhánh Đà Nẵng đã tăng bao nhiêu % trong Q3 so với Q2?”
- Lớp 4 – Câu hỏi thống kê: “Giá vốn hàng bán (COGS) trung bình/đơn hàng tại Đà Nẵng: Q2 vs Q3 là bao nhiêu VNĐ?”

PHÂN LOẠI LOẠI HÌNH CÂU HỎI (thuộc tính của mỗi chuỗi câu hỏi, không phải một lớp)
- Gắn mỗi câu hỏi kinh doanh (và chuỗi câu hỏi đi kèm) với một loại hình: Mô tả (điều gì đã xảy ra?) / Chẩn đoán (vì sao?) / Dự đoán (điều gì có thể xảy ra?) / Đề xuất (nên làm gì?).
- Khuyến khích bộ câu hỏi phủ đủ 4 loại hình nhưng không bắt buộc: nếu với QUYẾT ĐỊNH này một loại hình không cần thiết, bỏ qua và nêu lý do. Ít nhất một câu phải trả lời trực tiếp QUYẾT ĐỊNH.
- Ví dụ dạng câu hỏi kinh doanh theo loại hình:
    • Mô tả: “[Yếu tố nào] thay đổi nhanh nhất và ở [phạm vi nào]?”
    • Chẩn đoán: “Vì sao [kết quả] ở [phạm vi nào] lại [tăng/giảm]?”
    • Dự đoán: “[Kết quả] sẽ diễn biến thế nào trong [kỳ tới] nếu [điều kiện] giữ nguyên?”
    • Đề xuất: “Nên [hành động nào] với [đối tượng nào] để đạt [mục tiêu] trong [ràng buộc]?”
- Ví dụ dạng câu hỏi thống kê theo loại hình (ngoài dạng Mô tả ở Lớp 4):
    • Chẩn đoán: “Chênh lệch trung bình [cột X] giữa [nhóm 1] và [nhóm 2] là bao nhiêu [đơn vị đo], p-value của kiểm định [t / chi-bình phương] là bao nhiêu?”
    • Dự đoán: “Mô hình [tên] dùng [các cột] dự báo [cột mục tiêu] cho [kỳ tới] có sai số [MAPE/RMSE/AUC] bao nhiêu trên tập kiểm tra [kỳ C]?”
    • Đề xuất: “Với [ràng buộc], giá trị tối ưu của [biến quyết định] là bao nhiêu và [KPI] tăng thêm bao nhiêu [đơn vị đo] so với hiện trạng?”

════════════════════════════════════════
PHẦN B — HAI YÊU CẦU BỔ SUNG
════════════════════════════════════════

BỔ SUNG 1) DỮ LIỆU CẦN THU THẬP THÊM – kiểm tra từng câu hỏi thống kê
- Nếu dữ liệu đang có đã đủ: ghi “Đủ dữ liệu hiện có”.
- Nếu chưa đủ, chỉ rõ: a. tên trường còn thiếu; b. nguồn có thể thu thập; c. mức ưu tiên (Cao/Trung bình/Thấp); d. nếu không thu thập được (dữ liệu công khai), đề xuất biến thay thế hoặc giả định có căn cứ và cách kiểm tra độ nhạy.
- Ví dụ: “Thiếu giá vốn theo sản phẩm – nguồn: phần mềm kế toán hoặc BCTC doanh nghiệp cùng ngành – ưu tiên Cao – nếu không có: giả định biên gộp theo danh mục, kiểm tra độ nhạy ±5 điểm %.”

BỔ SUNG 2) HÀNH ĐỘNG DỰ KIẾN – cho mỗi câu hỏi kinh doanh
- Viết dạng: “Nếu [chỉ số] [>/<] [ngưỡng] thì [hành động A]; ngược lại [hành động B]”. Nếu chưa biết ngưỡng, ghi ngưỡng là tham số cần xác định và cách xác định.
- Ví dụ: “Nếu tỷ lệ giao trễ ở vùng Y > 15% → mở kho vệ tinh tại Y; ngược lại → giữ mạng lưới hiện tại và điều chỉnh cam kết thời gian giao.”

════════════════════════════════════════
QUY TẮC CHO AI
════════════════════════════════════════
- Không bịa trường dữ liệu: chỉ dùng các cột đã liệt kê; mọi trường khác phải đưa vào cột “Dữ liệu cần thu thập thêm”.
- Không trả lời các câu hỏi, không đưa số liệu giả định như thể là kết quả.
- Nếu bối cảnh hoặc dữ liệu chưa đủ để đặt câu hỏi tốt, nêu điểm thiếu ở đầu câu trả lời, rồi vẫn lập bảng với giả định tạm thời được ghi rõ.

════════════════════════════════════════
YÊU CẦU TRÌNH BÀY
════════════════════════════════════════
- 1. Nhắc lại LỚP 1 (Vấn đề kinh doanh) ở đầu câu trả lời, sau đó lập bảng, mỗi dòng 6 cột: [Câu hỏi kinh doanh (đã sắp ưu tiên) | Câu hỏi phân tích | Câu hỏi thống kê | Loại hình câu hỏi | Dữ liệu cần thu thập thêm (nếu có) | Hành động dự kiến].
- 2. Dưới bảng: (a) CÂU HỎI QUYẾT ĐỊNH CHỐT, viết trong một câu; (b) tự kiểm tra: số câu theo từng loại hình, số câu thống kê “Đủ dữ liệu hiện có”, các câu phải dựa vào giả định; (c) đánh giá mức khả thi của đề tài với dữ liệu hiện có (Cao/Trung bình/Thấp) và lý do.
```
