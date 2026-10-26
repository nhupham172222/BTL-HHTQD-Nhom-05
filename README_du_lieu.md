# Đề tài 12 – Bước O (dữ liệu) – TV2

## Chạy lần đầu (Windows)
1. Cài Python 3.12 64-bit (python.org), tick "Add python.exe to PATH".
2. Mở PowerShell trong thư mục này:
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```
3. Tạo file `vnstock_key.txt` ở thư mục này, dán key vnstock vào (không đẩy file này lên git).
4. Tải dữ liệu:
   ```
   python src/data_loader.py --test VCB
   python src/data_loader.py --all
   ```
5. Tải tay từ Investing (Daily, 10/2018–09/2026), chép vào `data/raw/`:
   - lợi suất TPCP 10 năm → `tpcp10y.csv`
   - VN-Index: trước tiên thử `python src/data_loader.py --vnindex` (tự lấy nguồn vnstock khác đủ chính xác);
     nếu báo fail thì tải tay VN-Index Historical Data → `vnindex_manual.csv` (vnstock nguồn VCI chỉ chính xác ±5 điểm)
6. `python run_all.py` -> `data/processed/`, `05_Phu_luc/Nhat_ky_ETL.md/.docx`, `Tu_dien_du_lieu.xlsx`.
   Ghi chú tay (đối chiếu, ngoại lệ) viết vào `05_Phu_luc/ghi_chu_thu_cong.md` – không bị ghi đè.

Mọi giả định (ngày bắt đầu/kết thúc, số phiên điền thiếu...) đọc từ `config.yaml`; không sửa số trong code.
Giai đoạn hiện tại: 2018-11-01 -> 2026-09-30 (A14, giới hạn ~8 năm của key vnstock miễn phí).