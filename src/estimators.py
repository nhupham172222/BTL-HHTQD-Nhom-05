"""Ước lượng lợi suất kỳ vọng μ và hiệp phương sai Σ. Chủ file: TV4.

Nguyên tắc: hàm chỉ nhận dữ liệu TRONG cửa sổ ước lượng (đã cắt sẵn đến ngày quyết định,
backtest.estimation_start: start = max(0, i − 756), báo lỗi nếu < 252 phiên).
Mọi kết quả trả về ở thang NĂM (nhân 252, đọc từ config.yaml).

Quy ước:
- μ "capm":       μ_i = rf + β_i · MRP. β_i = Cov(r_i, r_m) / Var(r_m) hồi quy lợi suất NGÀY của mã
                  với VN-Index trên các ngày chung trong cửa sổ (trừ rf ngày là hằng số trong cửa sổ
                  nên không làm đổi β). MRP = estimation.market_risk_premium (A12).
- μ "historical": trung bình cộng lợi suất ngày × 252 (thang số học, khớp với Σ × 252).
- Σ "sample":     hiệp phương sai mẫu (ddof = 1) × 252.
- Σ "ledoit_wolf": Ledoit & Wolf (2004), co về ma trận đơn vị nhân phương sai trung bình
                  (sklearn.covariance.LedoitWolf; giống PyPortfolioOpt "constant_variance"), × 252.
Không dùng dữ liệu ngoài cửa sổ; hàm không tự đọc file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load  # noqa: E402

MU_METHODS = ("capm", "historical")
COV_METHODS = ("ledoit_wolf", "sample")


def _days_per_year() -> int:
    return int(load()["conventions"]["trading_days_per_year"])


def _check_window(returns_window: pd.DataFrame) -> pd.DataFrame:
    R = pd.DataFrame(returns_window).astype(float)
    if R.shape[1] == 0:
        raise ValueError("Cửa sổ ước lượng không có mã nào")
    if R.isna().any().any():
        bad = list(R.columns[R.isna().any()])
        raise ValueError(f"Cửa sổ ước lượng có NaN ở các mã {bad} – backtest phải loại mã thiếu giá trước")
    if len(R) < 2:
        raise ValueError("Cửa sổ ước lượng cần ít nhất 2 phiên")
    return R


def betas(returns_window: pd.DataFrame, market_window: pd.Series) -> pd.Series:
    """β của từng mã với VN-Index trên các ngày chung trong cửa sổ (OLS có hệ số chặn)."""
    R = _check_window(returns_window)
    m = pd.Series(market_window, dtype=float)
    df = R.join(m.rename("__mkt__"), how="inner").dropna()
    if len(df) < 2:
        raise ValueError("Không đủ ngày chung giữa lợi suất cổ phiếu và VN-Index trong cửa sổ")
    mk = df.pop("__mkt__")
    var_m = mk.var(ddof=1)
    if not np.isfinite(var_m) or var_m <= 0:
        raise ValueError("Phương sai VN-Index trong cửa sổ bằng 0 – không tính được β")
    cov_im = df.apply(lambda col: col.cov(mk))
    return (cov_im / var_m).rename("beta")


def expected_returns(returns_window: pd.DataFrame, market_window: pd.Series,
                     method: str, rf_annual: float, mrp: float | None = None) -> pd.Series:
    """Lợi suất kỳ vọng NĂM của từng mã.

    method = "capm":       μ_i = rf + β_i · MRP (β hồi quy với VN-Index trong cửa sổ)
    method = "historical": trung bình lợi suất ngày · 252.
    rf_annual: rf tại ngày quyết định (backtest truyền rf_annual của ngày đó).
    """
    R = _check_window(returns_window)
    if method == "capm":
        if mrp is None:
            raise ValueError("CAPM cần market_risk_premium (estimation.market_risk_premium trong config.yaml)")
        b = betas(R, market_window)
        mu = float(rf_annual) + b * float(mrp)
    elif method == "historical":
        mu = R.mean() * _days_per_year()
    else:
        raise ValueError(f"expected_returns: method '{method}' không hợp lệ, chọn một trong {MU_METHODS}")
    return mu.reindex(R.columns).astype(float).rename("mu")


def covariance(returns_window: pd.DataFrame, method: str) -> pd.DataFrame:
    """Ma trận hiệp phương sai NĂM. method = "ledoit_wolf" | "sample"."""
    R = _check_window(returns_window)
    k = _days_per_year()
    if method == "sample":
        S = R.cov(ddof=1).to_numpy()
    elif method == "ledoit_wolf":
        S = LedoitWolf(assume_centered=False).fit(R.to_numpy()).covariance_
    else:
        raise ValueError(f"covariance: method '{method}' không hợp lệ, chọn một trong {COV_METHODS}")
    S = 0.5 * (S + S.T) * k  # ép đối xứng tuyệt đối trước khi đưa vào bộ giải
    return pd.DataFrame(S, index=R.columns, columns=R.columns)


def shrinkage_intensity(returns_window: pd.DataFrame) -> float:
    """Hệ số co δ ∈ [0, 1] của Ledoit–Wolf trong cửa sổ (0 = Σ mẫu, 1 = mục tiêu). Để báo cáo."""
    R = _check_window(returns_window)
    return float(LedoitWolf(assume_centered=False).fit(R.to_numpy()).shrinkage_)
