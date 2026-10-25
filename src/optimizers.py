"""Bốn chiến lược phân bổ. Chủ file: TV4.

Ràng buộc chung: w >= 0, w <= w_max, tổng = 1.
Phải raise ValueError nếu bài toán vô nghiệm (vd N * w_max < 1), không âm thầm trả kết quả.
Trả về pd.Series tỷ trọng, index = mã cổ phiếu.
"""
import pandas as pd


def check_feasible(n_assets: int, w_max: float) -> None:
    if n_assets * w_max < 1 - 1e-9:
        raise ValueError(f"Vô nghiệm: {n_assets} mã x w_max {w_max} < 100%")


def equal_weight(tickers: list[str]) -> pd.Series:
    """1/N. TODO (TV4)."""
    raise NotImplementedError


def min_variance(cov: pd.DataFrame, w_max: float) -> pd.Series:
    """TODO (TV4)."""
    raise NotImplementedError


def max_sharpe(mu: pd.Series, cov: pd.DataFrame, rf_annual: float, w_max: float) -> pd.Series:
    """TODO (TV4)."""
    raise NotImplementedError


def risk_parity(cov: pd.DataFrame, w_max: float) -> pd.Series:
    """Cân bằng đóng góp rủi ro (equal risk contribution). TODO (TV4)."""
    raise NotImplementedError
