"""Backtest cuốn chiếu. Chủ file: TV5.

Quy trình mỗi kỳ (theo config.yaml, mặc định theo quý):
1. Ngày quyết định = phiên cuối kỳ. Cửa sổ ước lượng mở rộng tới 756 phiên KẾT THÚC tại ngày này
   (tối thiểu 252 phiên, thiếu thì báo lỗi).
2. Tỷ trọng mục tiêu: 1/N tính ngay ở đây; chiến lược khác gọi estimators (μ, Σ) → optimizers.
3. Giao dịch tại giá đóng cửa phiên kế tiếp: BÁN trước, MUA sau, số cổ phiếu làm tròn xuống lô 100,
   phí mỗi chiều + thuế khi bán, tiền dư lãi cash_return.
4. Nắm giữ theo SỐ CỔ PHIẾU đến kỳ sau (tỷ trọng tự trôi theo giá); ghi turnover (metrics.turnover).
Đầu ra: lợi suất ngày trước và sau phí, tỷ trọng mục tiêu/thực tế từng kỳ, sổ lệnh, NAV.

Không bao giờ dùng dữ liệu sau ngày quyết định. Tập test chỉ chạy 1 lần sau khi đóng băng.

Giả định cần TV1 duyệt (chưa có trong config.yaml):
- Lần mua đầu tiên (từ 100% tiền mặt) mặc định CÓ tính phí (charge_initial=True);
  Lớp 1 không tính, nên đối chiếu Lớp 1 dùng charge_initial=False.
- Mã ngừng giao dịch (ROS): giữa hai kỳ định giá ở giá đóng cửa cuối cùng (chỉ để tính NAV);
  tại ngày giao dịch kế tiếp bán toàn bộ ở giá đó, có trừ phí + thuế.
- Lợi suất ngày = NAV_t / NAV_{t-1} − 1; phí trừ thẳng vào NAV ngày giao dịch. Lợi suất ngày giao dịch
  đầu tiên = NAV sau giao dịch / vốn ban đầu − 1 (chỉ gồm phí mua lần đầu, = 0 nếu charge_initial=False).
- Bản "gross" = chạy lại cùng logic, VẪN làm tròn lô 100, với fee = tax = 0.
- Cửa sổ ước lượng: giá các phiên [i − 756, i] → tối đa 756 lợi suất ngày; window_len = số lợi suất.
- Kỳ quyết định mà phiên giao dịch kế tiếp nằm sau `end` thì bỏ (không giao dịch ngoài giai đoạn).
- Thiếu tiền do phí: bớt từng lô của lệnh mua có giá trị sau mua vượt mục tiêu nhiều nhất
  (tức thiếu ít nhất), hòa thì theo thứ tự cột của prices.
- cash_return là lãi suất NĂM, cộng dồn theo ngày giao dịch (1 + cash_return) ** (1/252).
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import estimators  # noqa: E402
import metrics  # noqa: E402
import optimizers  # noqa: E402

STRATEGIES = ("equal_weight", "min_variance", "max_sharpe", "risk_parity")
REBALANCE = ("monthly", "quarterly", "semiannual")
# Khóa overrides được phép -> vị trí trong config (phục vụ lưới độ nhạy, không sửa config.yaml)
_OVERRIDE_PATHS = {
    "w_max": ("portfolio", "w_max"),
    "rebalance": ("portfolio", "rebalance"),
    "fee_per_side": ("costs", "fee_per_side"),
    "sell_tax": ("costs", "sell_tax"),
}


def load_inputs(root: Path = ROOT) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Đọc (prices, vnindex close, rf) từ data/processed."""
    P = pd.read_csv(root / "data/processed/prices.csv", index_col=0, parse_dates=True)
    V = pd.read_csv(root / "data/processed/vnindex.csv", index_col=0, parse_dates=True)["close"]
    R = pd.read_csv(root / "data/processed/rf.csv", index_col=0, parse_dates=True)
    return P, V, R


def apply_overrides(config: dict, overrides: dict | None) -> dict:
    """Bản sao config với các tham số đã override. Không bao giờ sửa dict gốc (load() có cache)."""
    cfg = copy.deepcopy(config)
    for key, val in (overrides or {}).items():
        if key == "estimation":
            cfg["estimation"].update(val)
        elif key in _OVERRIDE_PATHS:
            sec, name = _OVERRIDE_PATHS[key]
            cfg[sec][name] = val
        else:
            raise ValueError(f"overrides không hỗ trợ khóa '{key}' "
                             f"(chỉ: {sorted(_OVERRIDE_PATHS) + ['estimation']})")
    return cfg


def decision_dates(index: pd.DatetimeIndex, start, end, rebalance: str) -> pd.DatetimeIndex:
    """Phiên cuối mỗi kỳ nằm trong [start, end], cộng phiên cuối của kỳ ngay trước start."""
    if rebalance == "monthly":
        key = index.to_period("M")
    elif rebalance == "quarterly":
        key = index.to_period("Q")
    elif rebalance == "semiannual":
        key = index.year * 2 + (index.month > 6)
    else:
        raise ValueError(f"rebalance '{rebalance}' không hợp lệ, chọn một trong {REBALANCE}")
    last = pd.DatetimeIndex(pd.Series(index, index=index).groupby(key).last().values)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    before = last[last < start]
    inside = last[(last >= start) & (last <= end)]
    return before[-1:].append(inside)


def estimation_start(i: int, window_days: int, min_days: int, index: pd.DatetimeIndex | None = None) -> int:
    """Vị trí đầu cửa sổ: max(0, i − window_days). Cửa sổ giá [start, i] cho i − start lợi suất.

    Không cắt kiểu iloc[i-756:i] (chỉ số âm cắt sai mà không báo lỗi).
    """
    start = max(0, i - window_days)
    n = i - start
    if n < min_days:
        when = f" tại {index[i].date()}" if index is not None else ""
        raise ValueError(f"Cửa sổ ước lượng{when} chỉ có {n} phiên lợi suất, "
                         f"ít hơn tối thiểu {min_days} (periods.min_estimation_window_days)")
    return start


def _validate_weights(w: pd.Series, tickers: list[str], w_max: float, tol: float = 1e-6) -> pd.Series:
    """Kiểm tra đầu ra optimizer: chỉ mã khả dụng, w >= 0, w <= w_max, tổng = 1."""
    w = pd.Series(w, dtype=float)
    extra = w.index.difference(tickers)
    if len(extra):
        raise ValueError(f"Tỷ trọng có mã không khả dụng tại kỳ quyết định: {list(extra)}")
    w = w.reindex(tickers).fillna(0.0)
    if (w < -tol).any() or w.max() > w_max + tol or abs(w.sum() - 1.0) > tol:
        raise ValueError(f"Tỷ trọng vi phạm ràng buộc: min={w.min():.6f}, max={w.max():.6f} "
                         f"(w_max={w_max}), tổng={w.sum():.6f}")
    w = w.clip(lower=0.0)
    return w / w.sum()


def compute_target_weights(strategy: str, ret_window: pd.DataFrame, mkt_window: pd.Series,
                           rf_at_decision: float, tickers, cfg: dict) -> pd.Series:
    """Tỷ trọng mục tiêu tại ngày quyết định, chỉ dùng dữ liệu trong cửa sổ.

    ret_window: lợi suất ngày của `tickers` trong cửa sổ; mkt_window: lợi suất VN-Index cùng các ngày.
    rf_at_decision: rf_annual tại ngày quyết định (KHÔNG dùng rf_annual_avg_year: chứa giá trị tương lai).
    cfg: config đã áp overrides (w_max ở portfolio, phương pháp ở estimation).
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Chiến lược '{strategy}' không hợp lệ, chọn một trong {STRATEGIES}")
    tickers = list(tickers)
    w_max = cfg["portfolio"]["w_max"]
    optimizers.check_feasible(len(tickers), w_max)
    if strategy == "equal_weight":
        w = pd.Series(1.0 / len(tickers), index=tickers)
    else:
        est = cfg["estimation"]
        R = ret_window[tickers]
        cov = estimators.covariance(R, est["covariance"])
        if strategy == "min_variance":
            w = optimizers.min_variance(cov, w_max)
        elif strategy == "risk_parity":
            w = optimizers.risk_parity(cov, w_max)
        else:
            mu = estimators.expected_returns(R, mkt_window, est["expected_returns"],
                                             rf_at_decision, est.get("market_risk_premium"))
            w = optimizers.max_sharpe(mu, cov, rf_at_decision, w_max)
    return _validate_weights(w, tickers, w_max)


def _rebalance(shares: np.ndarray, cash: float, p: np.ndarray, w_target: np.ndarray,
               lot: int, fee: float, tax: float):
    """Một lần giao dịch tại giá p. Trả (shares mới, cash mới, sell, buy, w_drift, nav_pre)."""
    held = np.where(shares > 0, shares * p, 0.0)
    nav_pre = held.sum() + cash
    w_drift = held / nav_pre
    tgt_val = w_target * nav_pre
    tgt = np.zeros_like(shares)
    pos = w_target > 0
    tgt[pos] = np.floor(tgt_val[pos] / p[pos] / lot).astype(np.int64) * lot

    sell = np.maximum(shares - tgt, 0)
    buy = np.maximum(tgt - shares, 0)
    cash = cash + float((sell * p)[sell > 0].sum()) * (1.0 - fee - tax)

    # Thiếu tiền do phí: bớt từng lô, ưu tiên mã sau mua thiếu mục tiêu ít nhất (hòa: theo thứ tự cột)
    cost = np.where(buy > 0, buy * p, 0.0) * (1.0 + fee)
    while cost.sum() > cash:
        gap = np.where(buy > 0, (shares + buy) * p - tgt_val, -np.inf)
        k = int(np.argmax(gap))
        buy[k] -= lot
        cost[k] = buy[k] * p[k] * (1.0 + fee)
    cash = cash - cost.sum()
    return shares - sell + buy, cash, sell, buy, w_drift, nav_pre


def _simulate(prices: pd.DataFrame, schedule: list[tuple], targets: dict, end: pd.Timestamp,
              nav0: float, lot: int, fee: float, tax: float, cash_return: float,
              charge_initial: bool, days_per_year: int) -> dict:
    """Mô phỏng theo số cổ phiếu từ ngày giao dịch đầu tiên đến `end`."""
    tickers = prices.columns
    px = prices.ffill()  # mã ngừng giao dịch: định giá ở giá đóng cửa cuối cùng
    days = prices.index[(prices.index >= schedule[0][1]) & (prices.index <= end)]
    px_arr = px.loc[days].to_numpy(dtype=float)
    trade_at = {t: (k, d) for k, (d, t) in enumerate(schedule)}
    growth = (1.0 + cash_return) ** (1.0 / days_per_year)

    shares = np.zeros(len(tickers), dtype=np.int64)
    cash = float(nav0)
    nav = np.empty(len(days))
    cash_s = np.empty(len(days))
    trades, holdings, w_act, turn, cash_w = [], {}, {}, {}, {}
    for j, t in enumerate(days):
        p = px_arr[j]
        if j > 0:
            cash *= growth
        if t in trade_at:
            k, d = trade_at[t]
            f, x = (0.0, 0.0) if (k == 0 and not charge_initial) else (fee, tax)
            w_t = targets[d].reindex(tickers).fillna(0.0).to_numpy()
            shares, cash, sell, buy, w_drift, _ = _rebalance(shares, cash, p, w_t, lot, f, x)
            for side, q, rate in (("sell", sell, x), ("buy", buy, 0.0)):
                for c in np.flatnonzero(q):
                    val = float(q[c] * p[c])
                    trades.append((t, tickers[c], side, int(q[c]), float(p[c]), val, val * f, val * rate))
            held = np.where(shares > 0, shares * p, 0.0)
            nav_post = held.sum() + cash
            w_act[d] = pd.Series(held / nav_post, index=tickers)
            turn[d] = metrics.turnover(w_act[d], pd.Series(w_drift, index=tickers))
            cash_w[d] = cash / nav_post
            holdings[d] = pd.Series(shares.copy(), index=tickers)
        nav[j] = np.where(shares > 0, shares * p, 0.0).sum() + cash
        cash_s[j] = cash

    nav = pd.Series(nav, index=days, name="nav")
    ret = nav / nav.shift(1) - 1.0
    ret.iloc[0] = nav.iloc[0] / nav0 - 1.0
    return {
        "returns": ret.rename("return"),
        "nav": nav,
        "cash": pd.Series(cash_s, index=days, name="cash"),
        "trades": pd.DataFrame(trades, columns=["date", "ticker", "side", "shares", "price",
                                                "value", "fee", "tax"]),
        "holdings": pd.DataFrame(holdings).T,
        "weights_actual": pd.DataFrame(w_act).T,
        "turnover": pd.Series(turn, name="turnover"),
        "cash_weight": pd.Series(cash_w, name="cash_weight"),
    }


def run_backtest(prices: pd.DataFrame, benchmark: pd.Series, rf: pd.DataFrame,
                 strategy: str, config: dict, start: str, end: str,
                 overrides: dict | None = None, charge_initial: bool = True) -> dict:
    """Backtest một chiến lược trên [start, end].

    prices: giá đóng cửa VND (NaN = không có giá); benchmark: VN-Index close (Series hoặc DataFrame có cột
    close); rf: rf.csv (dùng rf_annual tại ngày quyết định); config: dict từ config.load().
    overrides: {"w_max", "rebalance", "fee_per_side", "sell_tax", "estimation": {...}}.
    Các Series/DataFrame theo kỳ có index = ngày quyết định; `schedule` cho ngày giao dịch tương ứng.
    """
    cfg = apply_overrides(config, overrides)
    per, port, costs = cfg["periods"], cfg["portfolio"], cfg["costs"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark["close"]
    idx = prices.index
    bench = benchmark.reindex(idx)
    rf_annual = rf["rf_annual"]
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    schedule = []
    for d in decision_dates(idx, start, end, port["rebalance"]):
        i = idx.get_loc(d)
        if i + 1 < len(idx) and idx[i + 1] <= end:
            schedule.append((d, idx[i + 1]))
    if not schedule:
        raise ValueError(f"Không có kỳ giao dịch nào trong [{start.date()}, {end.date()}]")

    targets, window_len = {}, {}
    for d, _ in schedule:
        i = idx.get_loc(d)
        s = estimation_start(i, per["estimation_window_days"], per["min_estimation_window_days"], idx)
        win = prices.iloc[s:i + 1]
        tickers = win.columns[win.notna().all()]  # có giá tại d và không NaN trong cửa sổ
        ret_w = win[tickers].pct_change(fill_method=None).iloc[1:]
        mkt_w = bench.iloc[s:i + 1].pct_change(fill_method=None).iloc[1:]
        rf_d = float(rf_annual.loc[:d].iloc[-1])
        w = compute_target_weights(strategy, ret_w, mkt_w, rf_d, tickers, cfg)
        targets[d] = w.reindex(prices.columns, fill_value=0.0)
        window_len[d] = len(ret_w)

    sim = dict(prices=prices, schedule=schedule, targets=targets, end=end, nav0=port["nav_vnd"],
               lot=port["lot_size"], cash_return=port["cash_return"],
               days_per_year=cfg["conventions"]["trading_days_per_year"])
    net = _simulate(**sim, fee=costs["fee_per_side"], tax=costs["sell_tax"], charge_initial=charge_initial)
    gross = _simulate(**sim, fee=0.0, tax=0.0, charge_initial=charge_initial)

    weights = pd.DataFrame(targets).T
    meta = {
        "strategy": strategy, "start": str(start.date()), "end": str(end.date()),
        "w_max": port["w_max"], "rebalance": port["rebalance"],
        "fee_per_side": costs["fee_per_side"], "sell_tax": costs["sell_tax"],
        "estimation": dict(cfg["estimation"]), "lot_size": port["lot_size"], "nav_vnd": port["nav_vnd"],
        "cash_return": port["cash_return"], "charge_initial": charge_initial,
        "estimation_window_days": per["estimation_window_days"],
        "min_estimation_window_days": per["min_estimation_window_days"],
        "overrides": dict(overrides or {}),
    }
    return {
        "returns_gross": gross["returns"].rename("returns_gross"),
        "returns_net": net["returns"].rename("returns_net"),
        "weights": weights,
        "weights_actual": net["weights_actual"],
        "turnover": net["turnover"],
        "n_holdings": (net["holdings"] > 0).sum(axis=1).rename("n_holdings"),
        "window_len": pd.Series(window_len, name="window_len"),
        "cash_weight": net["cash_weight"],
        "trades": net["trades"],
        "nav": net["nav"],
        "cash": net["cash"],
        "holdings": net["holdings"],
        "schedule": pd.DataFrame(schedule, columns=["decision_date", "trade_date"]),
        "meta": meta,
    }


def summarize(result: dict, rf: pd.DataFrame) -> pd.DataFrame:
    """Bảng chỉ số trước/sau phí (metrics.summary với rf_annual_avg_year, khớp Lớp 1).

    turnover_mean bỏ kỳ đầu (xây danh mục từ 100% tiền mặt), giống cách Lớp 1 đếm số lần tái cân bằng.
    turnover_mean, n_holdings_mean lấy từ bản sau phí. cost_pct_nav0 = tổng phí + thuế / vốn ban đầu.
    """
    rf_y = rf["rf_annual_avg_year"]
    trades = result["trades"]
    cost = float(trades["fee"].sum() + trades["tax"].sum()) / result["meta"]["nav_vnd"]
    rows = {name: metrics.summary(result[key], rf_y)
            for name, key in (("truoc_phi", "returns_gross"), ("sau_phi", "returns_net"))}
    df = pd.DataFrame(rows).T
    df["turnover_mean"] = float(result["turnover"].iloc[1:].mean())
    df["n_holdings_mean"] = float(result["n_holdings"].mean())
    df["cost_pct_nav0"] = [0.0, cost]
    df.index.name = "bien_the"
    return df
