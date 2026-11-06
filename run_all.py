"""Chạy toàn bộ bước O từ dữ liệu gốc.

    python run_all.py              # dùng data/raw có sẵn -> làm sạch -> data/processed
    python run_all.py --download   # tải lại dữ liệu thô bằng vnstock trước (cần mạng)
    python run_all.py --backtest validation                 # sau bước O, chạy backtest validation
    python run_all.py --backtest test --i-confirm-freeze    # sau bước O, chạy test (CHỈ MỘT LẦN, sau đóng băng)

Kiểm tra tái lập (T7 07/11): clone repo sang máy sạch, `pip install -r requirements.txt`,
chạy `python run_all.py`, so số trong report với data/processed/etl_log.json.
(Các bước P/T của TV1, TV3... thêm vào đây khi có.)
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="tải lại dữ liệu thô trước khi làm sạch")
    ap.add_argument("--backtest", choices=["validation", "test"],
                    help="sau bước O, chạy src/run_backtests.py cho giai đoạn này (mặc định: không chạy)")
    ap.add_argument("--i-confirm-freeze", action="store_true",
                    help="bắt buộc khi --backtest test: xác nhận thiết kế đã đóng băng")
    args = ap.parse_args()
    if args.backtest == "test" and not args.i_confirm_freeze:  # dừng trước khi đụng vào data/
        ap.error("--backtest test cần cờ --i-confirm-freeze (chỉ chạy một lần, sau khi đóng băng thiết kế)")

    if args.download:
        rc = subprocess.call([sys.executable, str(ROOT / "src" / "data_loader.py"), "--all", "--force"])
        if rc != 0:
            print("Tải dữ liệu có lỗi, dừng.")
            return rc

    import clean
    log = clean.run()
    print(f"[O] Giữ {log['final_shape']['tickers']}/{log['universe_size']} mã, {log['final_shape']['rows']} phiên, "
          f"{log['final_imputed_cells']} ô imputed, {log['final_na_cells']} ô NaN.")
    if log["excluded"]:
        print("[O] Mã bị loại:", {k: v[:60] for k, v in log["excluded"].items()})
    if log["suspect_unadjusted"]:
        print("[O] CẢNH BÁO nghi chưa điều chỉnh giá:", list(log["suspect_unadjusted"]))
    for n in log.get("notes", []):
        print("[O] Ghi chú:", n)
    try:
        import export_phu_luc
        for p in export_phu_luc.run():
            print("[O] Đã xuất", p.relative_to(ROOT))
    except ImportError as e:
        print(f"[O] Bỏ qua xuất .docx/.xlsx ({e}). Cài: python -m pip install python-docx openpyxl")

    if args.backtest:
        cmd = [sys.executable, str(ROOT / "src" / "run_backtests.py"), "--period", args.backtest]
        if args.i_confirm_freeze:
            cmd.append("--i-confirm-freeze")
        return subprocess.call(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
