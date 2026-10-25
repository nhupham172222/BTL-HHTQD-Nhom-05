"""Ước lượng lợi suất kỳ vọng μ và hiệp phương sai Σ. Chủ file: TV4.

Nguyên tắc: hàm chỉ nhận dữ liệu TRONG cửa sổ ước lượng (đã cắt sẵn đến ngày quyết định).
Mọi kết quả trả về ở thang NĂM (nhân 252).
"""
import pandas as pd


def expected_returns(returns_window: pd.DataFrame, market_window: pd.Series,
                     method: str, rf_annual: float, mrp: float | None = None) -> pd.Series:
    """method = "capm": μ_i = rf + β_i * MRP (β hồi quy với VN-Index trong cửa sổ)
       method = "historical": trung bình lợi suất ngày * 252.  TODO (TV4)."""
    raise NotImplementedError


def covariance(returns_window: pd.DataFrame, method: str) -> pd.DataFrame:
    """method = "ledoit_wolf" | "sample", thang năm. TODO (TV4)."""
    raise NotImplementedError
