"""Tải dữ liệu thô (bước O) bằng vnstock và lưu CSV ngay khi tải.

Cách dùng (từ thư mục gốc repo):
    pip install -U vnstock pandas numpy
    python src/data_loader.py --test VCB          # tải thử 1 mã (việc T3 27/10)
    python src/data_loader.py --all               # tải 30 mã + VN-Index (việc T4 28/10)
    python src/data_loader.py --all --force       # tải lại, ghi đè file cũ

Lưu ý:
- Free tier vnstock giới hạn ~10 lượt/phút (khách, không đăng nhập; tối đa 300 lượt/ngày) -> mặc định nghỉ 7 giây giữa các lần gọi.
  Nếu có API key (60 lượt/phút) thì giảm --pause.
- vnstock hay đổi API. Nếu lỗi import/cột khác, sửa duy nhất hàm `fetch_one` bên dưới.
- Lãi suất TPCP 10 năm: vnstock không có sẵn -> tải tay (xem README_TPCP trong docstring
  của `check_tpcp_file`) và lưu thành data/raw/tpcp10y.csv.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

sys.path.insert(0, str(ROOT / "src"))
from config import load as _load_cfg  # noqa: E402

_CFG = _load_cfg()
START = str(_CFG["data"]["start"])   # A14 – lấy từ config.yaml
END = str(_CFG["data"]["end"])
SOURCE = "VCI"          # đổi sang "KBS"/"TCBS" nếu VCI lỗi
INDEX_SYMBOL = _CFG["data"]["benchmark"]
KEEP_COLS = ["time", "open", "high", "low", "close", "volume"]


def load_universe(path: Path = RAW / "vn30_2020.csv") -> list[str]:
    return pd.read_csv(path)["ticker"].astype(str).str.strip().str.upper().tolist()


_LOGGED_IN = False


def login_once() -> None:
    """Đăng nhập vnstock bằng key trong file vnstock_key.txt (thư mục gốc) hoặc biến VNSTOCK_API_KEY."""
    global _LOGGED_IN
    if _LOGGED_IN:
        return
    key = os.environ.get("VNSTOCK_API_KEY", "").strip()
    key_file = ROOT / "vnstock_key.txt"
    if not key and key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
    if key:
        import vnstock
        vnstock.login(key)
        print("Đã đăng nhập vnstock bằng key.")
    else:
        print("CHÚ Ý: chưa có key (vnstock_key.txt) -> cấp Khách, chỉ lấy được 365 ngày.")
    _LOGGED_IN = True


def fetch_one(symbol: str, start: str = START, end: str = END, source: str = SOURCE) -> pd.DataFrame:
    """Gọi vnstock cho 1 mã. Chỉ hàm này phụ thuộc API của vnstock."""
    login_once()
    from vnstock import Quote  # import trễ để file vẫn import được khi chưa cài vnstock

    df = Quote(symbol=symbol, source=source).history(start=start, end=end, interval="1D")
    if df is None or len(df) == 0:
        raise ValueError(f"vnstock trả về rỗng cho {symbol}")
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    missing = [c for c in KEEP_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{symbol}: thiếu cột {missing}; cột hiện có: {list(df.columns)}")
    return df[KEEP_COLS]


def download(symbol: str, out_path: Path, force: bool = False, retries: int = 3, pause: float = 7.0) -> str:
    """Tải 1 mã và lưu CSV thô. Trả về 'ok' / 'skip' / 'fail: ...'."""
    if out_path.exists() and not force:
        return "skip"
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            df = fetch_one(symbol)
            df.to_csv(out_path, index=False)
            return f"ok ({len(df)} dòng, {df['time'].astype(str).min()} -> {df['time'].astype(str).max()})"
        except Exception as e:  # noqa: BLE001 - muốn bắt mọi lỗi mạng/API để retry
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(pause * attempt)  # lùi dần khi bị giới hạn lượt gọi
    return f"fail: {last_err}"


def check_tpcp_file(path: Path = RAW / "tpcp10y.csv") -> str:
    """Kiểm tra file lợi suất TPCP 10 năm đã được tải tay chưa.

    README_TPCP: tải lịch sử lợi suất trái phiếu chính phủ VN kỳ hạn 10 năm (ngày, theo data.start–data.end trong config.yaml)
    từ một nguồn có thể trích dẫn (HNX, hoặc Investing.com 'Vietnam 10-Year Bond Yield' -> Historical Data).
    Lưu thành data/raw/tpcp10y.csv với 2 cột: date,yield_pct   (vd: 2018-11-01,4.85)
    Ghi nguồn + ngày tải vào data/raw/tpcp10y_SOURCE.md.
    (clean.py cũng nhận file export của Investing.com với cột Date, Price.)
    """
    if path.exists():
        return f"OK: tìm thấy {path.name} ({sum(1 for _ in open(path, encoding='utf-8')) - 1} dòng)"
    return f"THIẾU: chưa có {path}. Xem hướng dẫn trong docstring check_tpcp_file()."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", metavar="SYMBOL", help="tải thử 1 mã, vd VCB")
    ap.add_argument("--all", action="store_true", help="tải 30 mã VN30-2020 + VN-Index")
    ap.add_argument("--force", action="store_true", help="tải lại, ghi đè CSV cũ")
    ap.add_argument("--pause", type=float, default=7.0, help="giây nghỉ giữa các lần gọi")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    if args.test:
        sym = args.test.upper()
        print(sym, download(sym, RAW / f"px_{sym}.csv", force=True, pause=args.pause))
        return 0

    if args.all:
        results = {}
        for sym in load_universe() + [INDEX_SYMBOL]:
            name = "vnindex.csv" if sym == INDEX_SYMBOL else f"px_{sym}.csv"
            res = download(sym, RAW / name, force=args.force, pause=args.pause)
            results[sym] = res
            print(f"{sym:8s} {res}", flush=True)
            if res.startswith("ok"):
                time.sleep(args.pause)
        print("\n" + check_tpcp_file())
        fails = [s for s, r in results.items() if r.startswith("fail")]
        if fails:
            print(f"\nLỖI {len(fails)} mã: {fails}. Chạy lại lệnh (mã đã tải sẽ được bỏ qua).")
            return 1
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())


def load_config(path: str = "config.yaml") -> dict:
    """Theo khung của nhóm: đọc config.yaml (tìm ở thư mục hiện tại rồi thư mục gốc repo)."""
    import yaml
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        p = ROOT / path
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)
