"""Bốn chiến lược phân bổ + đường biên hiệu quả. Chủ file: TV4.

Ràng buộc chung: w >= 0, w <= w_max, tổng = 1 (không bán khống, A5).
Phải raise ValueError nếu bài toán vô nghiệm (vd N * w_max < 1), không âm thầm trả kết quả.
Trả về pd.Series tỷ trọng, index = mã cổ phiếu.

Cách giải (cvxpy, bộ giải CLARABEL, dự phòng OSQP/SCS):
- min_variance: min w'Σw  s.t. ràng buộc chung (bài toán QP lồi).
- max_sharpe:   đổi biến y = κw (Cornuejols & Tütüncü): min y'Σy s.t. (μ − rf)'y = 1, y >= 0,
                Σy = κ, y <= w_max·κ, κ >= 0; w = y/κ. Nếu dưới ràng buộc không danh mục nào có
                lợi suất kỳ vọng vượt rf → raise ValueError (Sharpe tối đa không xác định).
- risk_parity:  đóng góp rủi ro bằng nhau RC_i = w_i(Σw)_i, giải bằng coordinate descent
                (Griveau-Billion, Richard & Roncalli 2013). Nếu có mã vượt w_max: giữ mã đó ở w_max,
                các mã còn lại có RC bằng nhau (lặp tập chạm trần) – xem docstring risk_parity.
- efficient_frontier: min w'Σw s.t. μ'w >= mục tiêu, ràng buộc chung; mục tiêu chạy từ lợi suất
                của Min Variance đến lợi suất lớn nhất đạt được dưới trần w_max.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load  # noqa: E402

TOL = 1e-6          # sai số chấp nhận khi kiểm tra ràng buộc (khớp backtest._validate_weights)
ZERO = 1e-7         # tỷ trọng nhỏ hơn mức này coi là 0 (nhiễu số của bộ giải)
_SOLVERS = ("CLARABEL", "OSQP", "SCS")


def check_feasible(n_assets: int, w_max: float) -> None:
    if n_assets * w_max < 1 - 1e-9:
        raise ValueError(f"Vô nghiệm: {n_assets} mã x w_max {w_max} < 100%")


# --- tiện ích ---------------------------------------------------------------------------------

def _prep_cov(cov: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    cov = pd.DataFrame(cov).astype(float)
    if list(cov.index) != list(cov.columns):
        raise ValueError("Ma trận hiệp phương sai phải có index trùng columns (cùng thứ tự mã)")
    S = cov.to_numpy()
    if not np.isfinite(S).all():
        raise ValueError("Ma trận hiệp phương sai có NaN/inf")
    return 0.5 * (S + S.T), list(cov.columns)


def _solve(prob: cp.Problem, what: str) -> None:
    last = None
    for s in _SOLVERS:
        if s not in cp.installed_solvers():
            continue
        try:
            prob.solve(solver=s)
        except (cp.error.SolverError, cp.error.DCPError) as e:  # thử bộ giải kế tiếp
            last = e
            continue
        if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            return
        if prob.status in (cp.INFEASIBLE, cp.INFEASIBLE_INACCURATE):
            raise ValueError(f"{what}: bài toán vô nghiệm (bộ giải {s})")
        last = prob.status
    raise ValueError(f"{what}: không giải được (trạng thái cuối: {last})")


def _finalize(w: np.ndarray, tickers: list[str], w_max: float, what: str) -> pd.Series:
    """Làm sạch nhiễu số, chuẩn hóa tổng = 1 và KIỂM TRA ràng buộc (không âm thầm sửa sai lớn)."""
    w = np.asarray(w, dtype=float).ravel()
    if not np.isfinite(w).all():
        raise ValueError(f"{what}: nghiệm có NaN/inf")
    if w.min() < -1e-5 or w.max() > w_max + 1e-5:
        raise ValueError(f"{what}: nghiệm vi phạm ràng buộc (min={w.min():.2e}, max={w.max():.6f})")
    w = np.clip(w, 0.0, w_max)
    w[w < ZERO] = 0.0
    w = w / w.sum()
    w = np.minimum(w, w_max)          # chuẩn hóa có thể đẩy mã chạm trần vượt ~1e-7
    w = w / w.sum()
    if w.max() > w_max + TOL or abs(w.sum() - 1) > TOL:
        raise ValueError(f"{what}: không thỏa ràng buộc sau làm sạch (max={w.max():.6f})")
    return pd.Series(w, index=tickers, name="weight")


def _max_return_under_caps(mu: np.ndarray, w_max: float) -> tuple[float, np.ndarray]:
    """max μ'w s.t. 0 <= w <= w_max, Σw = 1 – nghiệm tham lam (dồn w_max vào mã μ cao nhất)."""
    w = np.zeros_like(mu)
    left = 1.0
    for k in np.argsort(-mu):
        w[k] = min(w_max, left)
        left -= w[k]
        if left <= 1e-12:
            break
    return float(mu @ w), w


def risk_contributions(w: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Tỷ lệ đóng góp rủi ro (tổng = 1): w_i(Σw)_i / w'Σw. Dùng cho báo cáo và kiểm tra."""
    S, tickers = _prep_cov(cov)
    x = pd.Series(w, dtype=float).reindex(tickers).fillna(0.0).to_numpy()
    rc = x * (S @ x)
    return pd.Series(rc / rc.sum(), index=tickers, name="risk_contribution")


def n_positive(w: pd.Series, tol: float = 1e-4) -> int:
    """Số mã có tỷ trọng > tol (theo dõi mức tập trung của Max Sharpe mỗi kỳ)."""
    return int((pd.Series(w, dtype=float) > tol).sum())


def portfolio_stats(w: pd.Series, mu: pd.Series | None, cov: pd.DataFrame,
                    rf_annual: float | None = None) -> dict:
    """Lợi suất kỳ vọng, độ lệch chuẩn, Sharpe (thang năm) của danh mục w theo μ, Σ đã ước lượng."""
    S, tickers = _prep_cov(cov)
    x = pd.Series(w, dtype=float).reindex(tickers).fillna(0.0).to_numpy()
    vol = float(np.sqrt(max(x @ S @ x, 0.0)))
    ret = float(pd.Series(mu).reindex(tickers).to_numpy() @ x) if mu is not None else np.nan
    sharpe = (ret - rf_annual) / vol if (rf_annual is not None and vol > 0) else np.nan
    return {"exp_return": ret, "volatility": vol, "sharpe": sharpe, "n_positive": n_positive(w)}


# --- bốn chiến lược ---------------------------------------------------------------------------

def equal_weight(tickers: list[str]) -> pd.Series:
    """1/N trên các mã khả dụng tại ngày quyết định (không phụ thuộc w_max khi N·w_max >= 1)."""
    tickers = list(tickers)
    if not tickers:
        raise ValueError("equal_weight: danh sách mã rỗng")
    return pd.Series(1.0 / len(tickers), index=tickers, name="weight")


def min_variance(cov: pd.DataFrame, w_max: float) -> pd.Series:
    """Danh mục phương sai nhỏ nhất, long-only, chặn trên w_max."""
    S, tickers = _prep_cov(cov)
    n = len(tickers)
    check_feasible(n, w_max)
    w = cp.Variable(n)
    prob = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(S))),
                      [cp.sum(w) == 1, w >= 0, w <= w_max])
    _solve(prob, "min_variance")
    return _finalize(w.value, tickers, w_max, "min_variance")


def max_sharpe(mu: pd.Series, cov: pd.DataFrame, rf_annual: float, w_max: float) -> pd.Series:
    """Danh mục tiếp tuyến (Sharpe kỳ vọng lớn nhất) long-only, chặn trên w_max."""
    S, tickers = _prep_cov(cov)
    n = len(tickers)
    check_feasible(n, w_max)
    m = pd.Series(mu, dtype=float).reindex(tickers)
    if m.isna().any():
        raise ValueError(f"max_sharpe: thiếu μ cho các mã {list(m.index[m.isna()])}")
    ex = m.to_numpy() - float(rf_annual)
    best, _ = _max_return_under_caps(ex, w_max)
    if best <= 1e-10:
        msg = ("max_sharpe: không có danh mục nào (dưới ràng buộc w_max) có lợi suất kỳ vọng "
               f"vượt rf = {rf_annual:.4f} – Sharpe tối đa không xác định")
        rule = load()["estimation"].get("max_sharpe_if_no_excess", "raise")
        if rule == "min_variance":
            warnings.warn(msg + " → dùng Min Variance (estimation.max_sharpe_if_no_excess)")
            return min_variance(cov, w_max)
        if rule != "raise":
            raise ValueError(f"estimation.max_sharpe_if_no_excess = '{rule}' không hợp lệ "
                             "(chọn 'raise' hoặc 'min_variance')")
        raise ValueError(msg + ". Muốn thay bằng Min Variance: TV1 thêm "
                         "estimation.max_sharpe_if_no_excess: \"min_variance\" vào config.yaml")
    y = cp.Variable(n)
    kappa = cp.Variable()
    prob = cp.Problem(cp.Minimize(cp.quad_form(y, cp.psd_wrap(S))),
                      [ex @ y == 1, y >= 0, cp.sum(y) == kappa, y <= w_max * kappa, kappa >= 0])
    _solve(prob, "max_sharpe")
    if kappa.value is None or kappa.value <= 0:
        raise ValueError("max_sharpe: nghiệm suy biến (κ <= 0)")
    return _finalize(y.value / kappa.value, tickers, w_max, "max_sharpe")


def _rb_ccd(S: np.ndarray, c: np.ndarray, lam: float, y: np.ndarray,
            tol: float = 1e-13, max_sweeps: int = 10_000) -> np.ndarray:
    """Giải y_i·[(S y)_i + c_i] = lam với mọi i (y > 0) bằng coordinate descent tuần hoàn
    (Griveau-Billion, Richard & Roncalli 2013): mỗi bước giải nghiệm dương của phương trình bậc hai."""
    d = np.diag(S)
    y = y.copy()
    for _ in range(max_sweeps):
        y_old = y.copy()
        for i in range(len(y)):
            b = S[i] @ y - d[i] * y[i] + c[i]
            y[i] = (-b + np.sqrt(b * b + 4.0 * d[i] * lam)) / (2.0 * d[i])
        if np.max(np.abs(y - y_old)) <= tol * max(1.0, np.max(y)):
            return y
    warnings.warn("risk_parity: coordinate descent chưa hội tụ")
    return y


def risk_parity(cov: pd.DataFrame, w_max: float) -> pd.Series:
    """Cân bằng đóng góp rủi ro (equal risk contribution), long-only, chặn trên w_max.

    Không chạm trần: RC_i = w_i(Σw)_i bằng nhau cho mọi mã (nghiệm duy nhất, Spinu 2013).
    Có mã chạm trần: tập C các mã giữ ở w_max, các mã còn lại F có RC bằng nhau và tổng tỷ trọng
    1 − |C|·w_max (tìm hệ số RC chung bằng chia đôi). Mã nào của F vượt w_max thì chuyển sang C,
    lặp đến khi không còn mã vượt. Mã chạm trần có RC nhỏ hơn các mã còn lại.
    """
    S, tickers = _prep_cov(cov)
    n = len(tickers)
    check_feasible(n, w_max)
    if np.any(np.diag(S) <= 0):
        raise ValueError("risk_parity: có mã phương sai <= 0")
    capped = np.zeros(n, dtype=bool)
    w = np.full(n, 1.0 / n)
    for _ in range(n):
        F = ~capped
        wc = np.where(capped, w_max, 0.0)
        budget = 1.0 - capped.sum() * w_max
        S_FF = S[np.ix_(F, F)]
        c = S[np.ix_(F, capped)] @ wc[capped] if capped.any() else np.zeros(F.sum())
        y = np.full(F.sum(), budget / F.sum())
        if not capped.any():                      # bất biến theo thang: giải 1 lần rồi chuẩn hóa
            y = _rb_ccd(S_FF, c, 1.0, y)
            y = y / y.sum()
        else:                                     # chia đôi hệ số RC chung để Σy = budget
            lo, hi = 0.0, float(y @ S_FF @ y + y @ c) / F.sum()
            while _rb_ccd(S_FF, c, hi, y).sum() < budget:
                hi *= 2.0
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                y = _rb_ccd(S_FF, c, mid, y)
                if y.sum() < budget:
                    lo = mid
                else:
                    hi = mid
                if hi - lo <= 1e-15 * max(hi, 1e-30):
                    break
            y = y * budget / y.sum()
        w = wc.copy()
        w[F] = y
        over = F & (w > w_max + 1e-12)
        if not over.any():
            break
        capped |= over
    return _finalize(w, tickers, w_max, "risk_parity")


# --- đường biên hiệu quả ------------------------------------------------------------------------

def efficient_frontier(mu: pd.Series, cov: pd.DataFrame, w_max: float, n_points: int = 40,
                       rf_annual: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đường biên hiệu quả CÓ RÀNG BUỘC (w >= 0, w <= w_max, Σw = 1).

    Trả (points, weights):
      points:  mỗi dòng một điểm – target_return, exp_return, volatility, sharpe, n_positive
      weights: tỷ trọng của từng điểm (index = số thứ tự điểm, cột = mã)
    """
    S, tickers = _prep_cov(cov)
    n = len(tickers)
    check_feasible(n, w_max)
    m = pd.Series(mu, dtype=float).reindex(tickers)
    if m.isna().any():
        raise ValueError(f"efficient_frontier: thiếu μ cho các mã {list(m.index[m.isna()])}")
    mv = m.to_numpy()
    r_lo = float(mv @ min_variance(cov, w_max).to_numpy())
    r_hi, _ = _max_return_under_caps(mv, w_max)
    targets = np.linspace(r_lo, r_hi, n_points)

    w = cp.Variable(n)
    tgt = cp.Parameter()
    prob = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(S))),
                      [cp.sum(w) == 1, w >= 0, w <= w_max, mv @ w >= tgt])
    rows, ws = [], []
    for k, t in enumerate(targets):
        # điểm cuối đúng bằng lợi suất tối đa: lùi một chút để tránh vô nghiệm do sai số số học
        tgt.value = float(t) - (1e-9 if k == len(targets) - 1 else 0.0)
        _solve(prob, f"efficient_frontier (điểm {k})")
        wk = _finalize(w.value, tickers, w_max, f"efficient_frontier (điểm {k})")
        st = portfolio_stats(wk, m, cov, rf_annual)
        rows.append({"point": k, "target_return": float(t), **st})
        ws.append(wk.rename(k))
    return pd.DataFrame(rows).set_index("point"), pd.DataFrame(ws)
