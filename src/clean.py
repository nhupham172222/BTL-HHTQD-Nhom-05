"""Làm sạch dữ liệu theo ETL 4 bước. Chủ file: TV2.

Mỗi bước ghi số dòng trước/sau để đưa vào Nhật ký ETL.
1. Đảm bảo chất lượng: kiểu dữ liệu (ngày, số), đơn vị.
2. Xác thực: số phiên mỗi mã, đối chiếu vài giá với nguồn công bố.
3. Làm sạch: trùng lặp, giá <= 0, thiếu giá (ffill tối đa max_ffill_days + cột cờ imputed).
4. Khám phá sơ bộ: thống kê tóm tắt, ngoại lai lợi suất.

Đầu ra: data/processed/prices.csv (bảng rộng: time x ticker, giá đóng cửa),
        data/processed/imputed_flags.csv, data/processed/rf.csv
"""
import pandas as pd


def clean_prices(raw: pd.DataFrame, max_ffill_days: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Trả về (prices_wide, imputed_flags, etl_log). TODO (TV2)."""
    raise NotImplementedError
