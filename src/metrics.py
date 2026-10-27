"""Chỉ số hiệu quả DÙNG CHUNG cho cả nhóm. Chủ file: TV3.

Quy ước bắt buộc (khớp config.yaml):
- Đầu vào là chuỗi lợi suất NGÀY dạng thập phân (0.01 = 1%).
- 252 phiên/năm.
- rf: lãi suất phi rủi ro NĂM dạng thập phân, quy đổi sang ngày bằng (1+rf)**(1/252)-1.
Không ai được tự viết lại các hàm này ở file khác.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _clean(r: pd.Series) -> pd.Series:
    """Bỏ NaN (vd. ngày chưa có lợi suất ở đầu chuỗi)."""
    return pd.Series(r).astype(float).dropna()


def _daily_rf(rf_annual, index: pd.Index):
    """rf năm (số hoặc Series theo ngày) -> rf ngày, căn theo index của lợi suất."""
    if isinstance(rf_annual, pd.Series):
        rf_annual = rf_annual.reindex(index).ffill().bfill()
    return (1.0 + rf_annual) ** (1.0 / TRADING_DAYS) - 1.0


def _excess(r: pd.Series, rf_annual) -> pd.Series:
    r = _clean(r)
    return (r - _daily_rf(rf_annual, r.index)).dropna()


def annualized_return(r: pd.Series) -> float:
    """Lợi suất năm hóa hình học: (Π(1+r))**(252/n) - 1."""
    r = _clean(r)
    n = len(r)
    if n == 0:
        return np.nan
    growth = float(np.prod(1.0 + r.to_numpy()))
    if growth <= 0:
        return -1.0
    return growth ** (TRADING_DAYS / n) - 1.0


def annualized_volatility(r: pd.Series) -> float:
    """Độ lệch chuẩn năm hóa: std(r) * sqrt(252). std mẫu (ddof=1)."""
    r = _clean(r)
    if len(r) < 2:
        return np.nan
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def sharpe_ratio(r: pd.Series, rf_annual: float | pd.Series) -> float:
    """(Lợi suất vượt rf trung bình ngày * 252) / (std lợi suất vượt * sqrt(252))."""
    ex = _excess(r, rf_annual)
    if len(ex) < 2:
        return np.nan
    sd = ex.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return np.nan
    return float(ex.mean() * TRADING_DAYS / (sd * np.sqrt(TRADING_DAYS)))


def sortino_ratio(r: pd.Series, rf_annual: float | pd.Series) -> float:
    """Như Sharpe nhưng mẫu số chỉ tính phần lợi suất dưới ngưỡng rf (downside deviation).

    DD ngày = sqrt(mean(min(r - rf_ngày, 0)^2)), chia cho TOÀN BỘ n quan sát
    (ngày không thua rf đóng góp 0), rồi nhân sqrt(252).
    """
    ex = _excess(r, rf_annual)
    if len(ex) < 2:
        return np.nan
    downside = np.minimum(ex.to_numpy(), 0.0)
    dd = np.sqrt(np.mean(downside ** 2)) * np.sqrt(TRADING_DAYS)
    if dd == 0 or np.isnan(dd):
        return np.nan
    return float(ex.mean() * TRADING_DAYS / dd)


def max_drawdown(r: pd.Series) -> float:
    """Mức giảm lớn nhất từ đỉnh xuống đáy của giá trị lũy kế, trả về số âm (vd -0.25)."""
    r = _clean(r)
    if len(r) == 0:
        return np.nan
    wealth = np.concatenate([[1.0], np.cumprod(1.0 + r.to_numpy())])  # gồm điểm xuất phát = 1
    peak = np.maximum.accumulate(wealth)
    return float((wealth / peak - 1.0).min())


def turnover(w_new: pd.Series, w_drifted: pd.Series) -> float:
    """Vòng quay một lần tái cân bằng: 0.5 * Σ|w_new - w_drifted|.

    Mã có ở một bên mà thiếu ở bên kia được coi là trọng số 0.
    """
    w_new = pd.Series(w_new).astype(float)
    w_drifted = pd.Series(w_drifted).astype(float)
    idx = w_new.index.union(w_drifted.index)
    diff = w_new.reindex(idx).fillna(0.0) - w_drifted.reindex(idx).fillna(0.0)
    return float(0.5 * diff.abs().sum())


def summary(r: pd.Series, rf_annual) -> dict:
    """Gom các chỉ số trên thành một dict để in bảng."""
    r = _clean(r)
    return {
        "annual_return": annualized_return(r),
        "annual_volatility": annualized_volatility(r),
        "sharpe": sharpe_ratio(r, rf_annual),
        "sortino": sortino_ratio(r, rf_annual),
        "max_drawdown": max_drawdown(r),
        "n_obs": int(len(r)),
    }
