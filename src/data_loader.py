"""Tải dữ liệu thô. Chủ file: TV2.

Yêu cầu:
- Lưu ngay mọi dữ liệu tải về vào data/raw/ (CSV), không sửa tay file raw.
- Đọc tham số từ config.yaml, không gõ cứng ngày hay mã.
- Ghi lại phiên bản vnstock và nguồn (source) đã dùng vào Nhật ký ETL.
"""
import pandas as pd


def load_config(path: str = "config.yaml") -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def download_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Tải giá ngày (time, open, high, low, close, volume) cho từng mã bằng vnstock.

    Trả về bảng dạng dài: ticker | time | open | high | low | close | volume.
    TODO (TV2): kiểm tra close đã điều chỉnh chưa, đơn vị giá (thường là nghìn đồng).
    """
    raise NotImplementedError


def download_benchmark(start: str, end: str) -> pd.DataFrame:
    """Tải VN-Index cùng giai đoạn. TODO (TV2)."""
    raise NotImplementedError


def load_risk_free() -> pd.DataFrame:
    """Đọc lợi suất TPCP 10 năm (năm, lợi suất dạng thập phân) từ data/raw. TODO (TV2)."""
    raise NotImplementedError
