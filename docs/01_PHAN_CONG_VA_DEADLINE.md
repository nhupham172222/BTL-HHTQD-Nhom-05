# 01 – PHÂN CÔNG, FILE CẦN NỘP VÀ DEADLINE

> Thời gian: **T2 26/10 → CN 08/11/2026**. Hạn chót mỗi mốc là **23:00** ngày ghi.
> Cách nộp: code/dữ liệu → **Pull Request trên GitHub**; tài liệu → **thư mục Drive** đúng chỗ. Xong việc thì báo vào nhóm chat kèm link.
> ⚠️ = chỗ dùng file prompt của thầy (`BTN_Prompt.md`).

---

## 1. Tổng quan vai trò

| TV | Họ tên | Vai | Phần trình bày trong video |
|---|---|---|---|
| TV1 | _(nhóm trưởng)_ | Điều phối + bước S + Sổ giả định + nhật ký AI | Mở đầu (S) và khuyến nghị cuối |
| TV2 | | Dữ liệu (bước O) + kiểm tra tái lập | Dữ liệu |
| TV3 | | Mô tả & chẩn đoán + `metrics.py` dùng chung | Mô tả, chẩn đoán |
| TV4 | | Ước lượng μ, Σ + tối ưu + đường biên | Dự báo, đường biên |
| TV5 | | Backtest + độ nhạy + kiểm định Sharpe | Kết quả backtest |
| TV6 | | Dashboard + ghép report + slide + dựng video | Demo dashboard |

Gợi ý chọn người: người code mạnh nhất → TV5; người hiểu tài chính nhất → TV4; người cẩn thận, giỏi trình bày → TV6.

**Review chéo:** TV4 ↔ TV5 review code của nhau; TV3 soát mọi con số trong report; TV1 duyệt mọi Pull Request.

---

## 2. Chi tiết từng thành viên

### TV1 – Nhóm trưởng, bước S

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| T2 26/10 | Tạo repo, Drive; add thành viên; gửi phân công vào nhóm chat | Repo GitHub, Drive |
| **T5 29/10** | ⚠️ **Chạy prompt bước S** (khối Chủ đề 12) với số Lớp 1 lấy từ TV3 → sửa thành bảng 6 cột → đề cương 1 trang (**Mốc 1**) | `docs/S_bang_cau_hoi.md`; Drive `05_Phu_luc/De_cuong_moc1.docx` |
| T5 29/10 | ⚠️ Ghi **toàn văn prompt + phản hồi AI** + phần giữ/sửa/bỏ vào Nhật ký AI | Drive `05_Phu_luc/Nhat_ky_AI` (Google Sheets) |
| T5 29/10 | Cùng TV3 chốt bảng giả thuyết (**Mốc 3**) | `docs/A_gia_thuyet.md` |
| Liên tục | Giữ **Sổ giả định** khớp với `config.yaml` | Drive `05_Phu_luc/So_gia_dinh` |
| T6 30/10 | Tra **bối cảnh thị trường CK VN 2017–2026** (COVID 2020, giảm mạnh 2022, mức giảm VN-Index), lý do chọn VN30; ghi nguồn từng ý | Google Docs report, phần 1–2 (bản nháp 1 trang) |
| T2 02/11 | Chốt thiết kế (μ, Σ) theo kết quả validation cùng TV4, TV5, thông báo nhóm chat | Nhóm chat, cập nhật `config.yaml` |
| **T5 05/11** | Viết Tóm tắt điều hành (≤1 trang), phần 1, 2, 3, 7, phụ lục AI + đạo đức; đọc duyệt toàn bộ report | Google Docs report |
| **CN 08/11** | Kiểm tra checklist, nộp Drive, chuyển repo public / mời thầy | Thư mục nộp |

> ⚠️ **Cách dùng file của thầy ở bước S:** xem `docs/03_PROMPT_BUOC_S_CHU_DE_12.md`. Tóm tắt: (1) lấy số thật từ TV3 điền vào các ô `[__]`; (2) dán **cả khối** vào AI; (3) kiểm tra AI không bịa cột ngoài `time, open, high, low, close, volume`; (4) lưu nguyên văn vào Nhật ký AI; (5) sửa bảng AI trả về thành bảng của nhóm. **AI không được tạo con số.**

### TV2 – Dữ liệu (bước O)

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| T3 27/10 | Tra danh sách **VN30 kỳ xem xét 1/2020** (thông báo HOSE), lưu nguồn; cài môi trường, tải thử 1 mã | `data/raw/vn30_2020.csv` (+ link nguồn) |
| **T4 28/10** | Tải giá ngày 01/2017–09/2026 cho vũ trụ + VN-Index; tải lợi suất TPCP 10 năm; ETL 4 bước; loại mã thiếu lịch sử | `src/data_loader.py`, `src/clean.py`, `data/raw/*.csv`, `data/processed/prices.csv`, `data/processed/rf.csv` |
| **T4 28/10** | Từ điển dữ liệu + Nhật ký ETL (số dòng trước/sau, quy tắc làm sạch, cột cờ `imputed`) | Drive `05_Phu_luc/Tu_dien_du_lieu`, `05_Phu_luc/Nhat_ky_ETL` |
| T5 29/10 | Tìm nguồn cho phí giao dịch, thuế bán, phần bù rủi ro Damodaran → gửi TV1 điền Sổ giả định | Gửi TV1 qua nhóm chat |
| T5 29/10 | ⚠️ Đọc cột **"Dữ liệu cần thu thập thêm"** trong bảng 6 cột của TV1 → bổ sung dữ liệu nếu thiếu | Cập nhật `data/` |
| T4 04/11 | Viết **phần 4 (O)** của report | Google Docs report |
| **T7 07/11** | **Kiểm tra tái lập:** clone repo về máy sạch, chạy `python run_all.py` từ dữ liệu gốc → ra đúng số trong report | Báo kết quả vào nhóm chat |

> Lưu ý: lưu CSV thô **ngay khi tải** (vnstock hay đổi API, giới hạn số lần gọi). Kiểm tra **đơn vị giá** (thường là nghìn đồng) và **giá đã điều chỉnh chưa** bằng cách đối chiếu 1–2 lần chia tách/cổ tức thật. Thiếu giá: điền giá trước đó tối đa 5 phiên + cột cờ; thiếu lâu hơn → ghi lại, loại mã ở kỳ tái cân bằng kế tiếp.

### TV3 – Mô tả, chẩn đoán, metrics dùng chung

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| **T4 28/10** | Viết `src/metrics.py` (theo docstring có sẵn), test trên dữ liệu mẫu | `src/metrics.py` |
| **T5 29/10** | Tính **số liệu Lớp 1**: Sharpe, MDD của 1/N và VN-Index giai đoạn 10/2023–09/2026 → gửi TV1 (⚠️ để điền prompt bước S) | `outputs/lop1_facts.csv` |
| **T5 29/10** | Soạn **giả thuyết chiều hướng** (Mốc 3) cho 6 biến giải thích, viết trước khi có kết quả backtest | `docs/A_gia_thuyet.md` |
| **CN 01/11** | EDA: thống kê từng mã, MDD, heatmap tương quan; chẩn đoán tương quan 2022 vs bình thường (bootstrap); đóng góp rủi ro | `notebooks/01_mo_ta.ipynb`, `notebooks/02_chan_doan.ipynb`, hình trong `outputs/figures/` |
| T4 04/11 | Viết **phần 5: Mô tả + Chẩn đoán** | Google Docs report |
| T5 05/11 | Soát mọi con số trong report khớp file `outputs/` | Comment trong Google Docs |

> Lưu ý: quy ước 252 phiên/năm, Sortino ngưỡng Rf, turnover = ½·Σ|Δw|. Mọi người dùng `metrics.py` của bạn, nên làm xong sớm. Viết "liên hệ", không viết "gây ra".

### TV4 – Ước lượng và tối ưu

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| T5 29/10 | Đọc hiểu CAPM, Ledoit–Wolf, Risk Parity; thử PyPortfolioOpt trên dữ liệu của TV2 | Gửi ghi chú vào nhóm chat |
| **CN 01/11** | `src/estimators.py`: μ (CAPM, lịch sử), Σ (mẫu, Ledoit–Wolf), chỉ dùng dữ liệu trong cửa sổ | `src/estimators.py` |
| **CN 01/11** | `src/optimizers.py`: 1/N, Min Var, Max Sharpe, Risk Parity với ràng buộc w ≥ 0, w ≤ w_max, tổng = 1; báo lỗi nếu vô nghiệm | `src/optimizers.py` |
| **T2 02/11** | Đánh giá sai số dự báo: biến động dự báo vs thực tế quý sau (RMSE), LW vs Σ mẫu; vẽ **đường biên hiệu quả** có ràng buộc | `notebooks/03_du_bao_duong_bien.ipynb`, `outputs/forecast_error.csv`, `outputs/frontier.csv` |
| T3 03/11 | Review code backtest của TV5 | Review trong Pull Request |
| T4 04/11 | Viết **phần 5: Dự báo + phương pháp tối ưu** | Google Docs report |

> Lưu ý: Max Sharpe dễ dồn vào vài mã → ghi số mã có tỷ trọng > 0 mỗi kỳ. Không dùng dữ liệu sau thời điểm quyết định.

### TV5 – Backtest và độ nhạy

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| **T6 30/10** | `src/backtest.py` chạy được với 1/N: tái cân bằng quý, phí, thuế, lô 100, tiền dư, trôi tỷ trọng | `src/backtest.py` |
| **T2 02/11** | Chạy đủ 4 chiến lược trên **validation 2020–2021** với các phương án μ, Σ → bảng để chốt thiết kế | `outputs/validation_results.csv` |
| **T3 03/11** | 🔒 **ĐÓNG BĂNG SỐ LIỆU:** chạy **test 2022–2026Q3 một lần**; lưới độ nhạy (w_max × tần suất × phí × Rf); kiểm định chênh lệch Sharpe (bootstrap khối); tỷ trọng đề xuất Q4/2026; xuất CSV cho dashboard | `run_all.py`, `outputs/test_results.csv`, `outputs/sensitivity_grid.csv`, `outputs/weights_Q4_2026.csv`, `outputs/equity_curves.csv` |
| T4 04/11 | Viết **phần 5: Đề xuất** + số liệu cho phần 6 | Google Docs report |

> Lưu ý: **không dùng tập test để chọn bất cứ thứ gì**; lưới độ nhạy trên test chỉ để báo cáo độ vững. Báo cáo cả trước và sau phí. Mỗi file output ghi kèm tên config đã chạy.

### TV6 – Dashboard, report, slide, video

| Hạn | Việc | File nộp / nơi để |
|---|---|---|
| **T4 28/10** | Tạo cấu trúc Drive; tạo Google Docs report theo khung `docs/04_KHUNG_REPORT_VA_VIDEO.md` | Drive |
| T6 30/10 | Phác dashboard Power BI bằng dữ liệu tạm (ghi rõ "dữ liệu tạm") | `.pbix` nháp |
| **T4 04/11** | Dashboard hoàn chỉnh 3 trang từ CSV đã đóng băng: tổng quan, so sánh chiến lược, **what-if** | Drive `04_Dashboard/Dashboard_NhomXX.pbix` + `anh_chup_dashboard.pdf` |
| T4 04/11 | Viết **phần 6 (R)**: thông điệp chính, ảnh dashboard | Google Docs report |
| T4 04/11 | Gom **Tài liệu tham khảo**: Richardson & Watson (2023), nguồn dữ liệu, nguồn giả định (TV1, TV2 gửi link) | Google Docs report, mục Tài liệu tham khảo |
| **T5 05/11** | Ghép report, định dạng thống nhất; slide 10 phút; kịch bản video | Google Docs, slide |
| **T7 07/11** | Dựng video, xuất `.mp4`; xuất report Word + PDF | Drive `01_Video/`, `02_Report/` |

> Lưu ý: Power BI **không chạy tối ưu trực tiếp**. What-if = chọn tham số (slicer) để **lọc lưới kịch bản TV5 đã tính sẵn**; ghi rõ điều này trên dashboard. Bắt buộc có: đường biên hiệu quả, lợi suất lũy kế vs VN-Index và 1/N, ≥1 tham số what-if.

---

## 3. Lịch tổng (cả nhóm nhìn bảng này)

| Ngày | Mốc | Ai |
|---|---|---|
| T2 26/10 | Repo, Drive; mọi người nhận vai, cài GitHub Desktop + Python | TV1, cả nhóm |
| T4 28/10 | Dữ liệu sạch, từ điển, nhật ký ETL; `metrics.py`; khung report | TV2, TV3, TV6 |
| **T5 29/10** | **Mốc 1 (S):** số Lớp 1, ⚠️ prompt bước S, bảng 6 cột, đề cương, nhật ký AI. **Mốc 3:** giả thuyết | TV1, TV3 |
| T6 30/10 | Backtest chạy với 1/N | TV5 |
| CN 01/11 | Mô tả + chẩn đoán xong; estimators + optimizers xong | TV3, TV4 |
| T2 02/11 | Validation xong → **chốt thiết kế** | TV5, TV4, TV1 |
| **T3 03/11** | 🔒 **ĐÓNG BĂNG SỐ LIỆU** (sau mốc này không sửa mô hình) | TV5 |
| T4 04/11 | Dashboard xong; **mọi người nộp phần viết report** | TV6, cả nhóm |
| T5 05/11 | Report hoàn chỉnh, tóm tắt điều hành, slide, kịch bản; review chéo | TV1, TV6, TV3 |
| **T6 06/11** | **Quay video** | Cả nhóm |
| T7 07/11 | Dựng video, xuất Word/PDF, kiểm tra tái lập | TV6, TV2 |
| **CN 08/11** | **Nộp bài** | TV1 |

---

## 4. Lưu ý chung (bắt buộc)

1. **Nguồn sự thật:** giả định chỉ nằm ở `config.yaml` (code) và Sổ giả định (report). Muốn đổi → nhắn TV1 trong nhóm chat, TV1 duyệt. Không gõ cứng con số trong code.
2. **Nhật ký AI:** ai dùng AI (viết code, sửa văn, hỏi khái niệm…) phải ghi **ngay** vào Google Sheets `Nhat_ky_AI`: ngày, người, công cụ, mục đích, prompt, tóm tắt phản hồi, giữ/sửa/bỏ + lý do. Không ghi bù cuối kỳ.
3. **Mọi con số trong report** phải truy ra được file trong `outputs/`.
4. **Không sửa mô hình sau 03/11.** Phát hiện lỗi → báo TV1, quyết định chung.
5. Notebook để khám phá; logic chính phải nằm trong `src/` để `run_all.py` chạy lại được.
6. Không đẩy lên GitHub: mật khẩu, token, file > 50MB, file `.pbix`, video.
7. Xong việc nào → báo nhóm chat + link PR/file. Trễ hạn → báo trước ít nhất 12 tiếng.

---

## 5. Video (~10 phút, tất cả lộ mặt)

| Thời lượng | Người | Nội dung |
|---|---|---|
| 0:00–1:30 | TV1 | Bối cảnh, vai trò, câu hỏi quyết định, chuỗi 4 lớp |
| 1:30–3:00 | TV2 | Nguồn dữ liệu, ETL, giả định chính |
| 3:00–4:30 | TV3 | Mô tả, chẩn đoán, giả thuyết |
| 4:30–6:00 | TV4 | Ước lượng μ, Σ, đường biên hiệu quả |
| 6:00–7:45 | TV5 | Kết quả backtest, so baseline, độ nhạy |
| 7:45–9:15 | TV6 | Demo dashboard what-if |
| 9:15–10:00 | TV1 | 2 khuyến nghị, hạn chế, kết luận |

Yêu cầu: camera thấy mặt (góc nhỏ khi chiếu slide), mic rõ, nền yên tĩnh, xuất `.mp4` 1080p. Mỗi người tự quay phần mình gửi TV6 trước **12:00 T7 07/11** nếu không quay chung.

---

## 6. Thư mục nộp cuối cùng (Drive)

```
261HHTQD_NhomXX/
├── 01_Video/        Video_NhomXX.mp4
├── 02_Report/       Report_NhomXX.docx, Report_NhomXX.pdf
├── 03_Data/         raw/, processed/, output/      (bản sao từ repo)
├── 04_Dashboard/    Dashboard_NhomXX.pbix, anh_chup_dashboard.pdf
├── 05_Phu_luc/      So_gia_dinh.xlsx, Tu_dien_du_lieu.xlsx, Nhat_ky_ETL.docx, Nhat_ky_AI.xlsx, De_cuong_moc1.docx
└── GitHub_link.txt
```

Ngoài ra trên Drive có thư mục làm việc `00_Tai_lieu_thay/` (PDF + prompt của thầy) – **xóa hoặc chuyển ra ngoài trước khi nộp**.
