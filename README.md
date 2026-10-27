# Tối ưu hóa danh mục đầu tư cổ phiếu Việt Nam – Nhóm 05

Bài tập nhóm môn **Hệ Hỗ trợ Quyết định & Trí tuệ Kinh doanh** (HK 261, HCMUT) – Chủ đề 12.
So sánh 4 chiến lược phân bổ (1/N, Min Variance, Max Sharpe, Risk Parity) bằng backtest cuốn chiếu ngoài mẫu, có phí giao dịch, trên cổ phiếu VN30.

> **Kết quả là bài tập học thuật, không phải khuyến nghị đầu tư.**

## Đọc trước
1. [`docs/00_BOI_CANH_CHUNG.md`](docs/00_BOI_CANH_CHUNG.md) – kịch bản và quyết định đã chốt
2. [`docs/01_PHAN_CONG_VA_DEADLINE.md`](docs/01_PHAN_CONG_VA_DEADLINE.md) – ai làm gì, hạn nào
3. [`docs/02_HUONG_DAN_GITHUB.md`](docs/02_HUONG_DAN_GITHUB.md) – cách dùng GitHub
4. [`docs/03_PROMPT_BUOC_S_CHU_DE_12.md`](docs/03_PROMPT_BUOC_S_CHU_DE_12.md) – cách dùng prompt của thầy (bước S)
5. [`docs/04_KHUNG_REPORT_VA_VIDEO.md`](docs/04_KHUNG_REPORT_VA_VIDEO.md) – khung report, slide, video

## Cấu trúc
```
config.yaml          Mọi giả định và tham số (chỉ TV1 sửa)
run_all.py           Chạy toàn bộ pipeline từ dữ liệu gốc (TV5)
src/
  data_loader.py     Tải dữ liệu (TV2)
  clean.py           Làm sạch, ETL (TV2)
  metrics.py         Chỉ số hiệu quả dùng chung (TV3)
  estimators.py      Ước lượng μ, Σ (TV4)
  optimizers.py      4 chiến lược tối ưu (TV4)
  backtest.py        Backtest cuốn chiếu (TV5)
data/raw/            Dữ liệu tải về, không sửa tay
data/processed/      Dữ liệu sau làm sạch
notebooks/           Khám phá, vẽ hình
outputs/             Kết quả (CSV, hình) – nguồn cho report và dashboard
templates/           Mẫu Sổ giả định, Nhật ký AI, Từ điển dữ liệu, Nhật ký ETL (đưa lên Drive)
```

## Chạy lại kết quả
```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_all.py               # dùng dữ liệu trong data/raw, ghi kết quả ra outputs/
```
_(TV5 cập nhật mục này khi pipeline hoàn chỉnh: thời gian chạy, file đầu ra, cách tải lại dữ liệu.)_

## Thành viên
| TV | Họ tên | MSSV | Vai |
|---|---|---|---|
| TV1 | | | Nhóm trưởng, bước S |
| TV2 | | | Dữ liệu |
| TV3 | | | Mô tả, chẩn đoán |
| TV4 | | | Ước lượng, tối ưu |
| TV5 | | | Backtest |
| TV6 | | | Dashboard, report |
