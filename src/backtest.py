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
- Kỳ Max Sharpe không có danh mục nào có μ vượt rf: dùng Min Variance (A15, optimizers.max_sharpe);
  kỳ đó có cờ `fallback` = True, `summarize` báo tổng số kỳ ở cột n_fallback.
- rf_shift (lưới độ nhạy): dịch cả rf tại ngày quyết định (Max Sharpe, CAPM) và rf báo cáo (Sharpe, Sortino).
- Bootstrap chênh lệch Sharpe: khối chồng lấn dài 21 phiên, 2.000 mẫu (đối số hàm, chưa có trong config).
- Đường NAV (equity_curve) chuẩn hóa = 1 tại ngày giao dịch đầu, nên phí mua lần đầu KHÔNG hiện trên đường net
  (lợi suất ngày đầu vẫn được tính trong Sharpe và các chỉ số khác).
"""
from __future__ import annotations

import copy
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import estimators  # noqa: E402
import metrics  # noqa: E402
import optimizers  # noqa: E402
from config import load  # noqa: E402

STRATEGIES = ("equal_weight", "min_variance", "max_sharpe", "risk_parity")
REBALANCE = ("monthly", "quarterly", "semiannual")
# Khóa overrides được phép -> vị trí trong config (phục vụ lưới độ nhạy, không sửa config.yaml)
_OVERRIDE_PATHS = {
    "w_max": ("portfolio", "w_max"),
    "rebalance": ("portfolio", "rebalance"),
    "fee_per_side": ("costs", "fee_per_side"),
    "sell_tax": ("costs", "sell_tax"),
    "rf_shift": ("risk_free", "rf_shift"),
}
VERDICTS = ("ung_ho", "dung_chieu_chua_du_bang_chung", "khong_ung_ho")


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
                           rf_at_decision: float, tickers, cfg: dict, return_info: bool = False):
    """Tỷ trọng mục tiêu tại ngày quyết định, chỉ dùng dữ liệu trong cửa sổ.

    ret_window: lợi suất ngày của `tickers` trong cửa sổ; mkt_window: lợi suất VN-Index cùng các ngày.
    rf_at_decision: rf_annual tại ngày quyết định (KHÔNG dùng rf_annual_avg_year: chứa giá trị tương lai).
    cfg: config đã áp overrides (w_max ở portfolio, phương pháp ở estimation).
    return_info=True: trả (w, {"fallback": bool}); fallback = kỳ này Max Sharpe phải dùng Min Variance (A15).
    Cảnh báo khác của bộ giải được phát lại nguyên trạng; cảnh báo fallback chỉ được giữ lại khi đã trả qua cờ.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Chiến lược '{strategy}' không hợp lệ, chọn một trong {STRATEGIES}")
    tickers = list(tickers)
    w_max = cfg["portfolio"]["w_max"]
    optimizers.check_feasible(len(tickers), w_max)
    fallback = False
    if strategy == "equal_weight":
        w = pd.Series(1.0 / len(tickers), index=tickers)
    else:
        est = cfg["estimation"]
        R = ret_window[tickers]
        # "always": cờ fallback không được phụ thuộc bộ lọc cảnh báo bên ngoài (vd python -W ignore)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cov = estimators.covariance(R, est["covariance"])
            if strategy == "min_variance":
                w = optimizers.min_variance(cov, w_max)
            elif strategy == "risk_parity":
                w = optimizers.risk_parity(cov, w_max)
            else:
                mu = estimators.expected_returns(R, mkt_window, est["expected_returns"],
                                                 rf_at_decision, est.get("market_risk_premium"))
                w = optimizers.max_sharpe(mu, cov, rf_at_decision, w_max)
        for item in caught:
            is_fallback = "Min Variance" in str(item.message)
            fallback = fallback or is_fallback
            if not (is_fallback and return_info):
                warnings.warn_explicit(item.message, item.category, item.filename, item.lineno)
    w = _validate_weights(w, tickers, w_max)
    return (w, {"fallback": fallback}) if return_info else w


def _rf_shift(cfg: dict) -> float:
    return float(cfg.get("risk_free", {}).get("rf_shift", 0.0))


def _close(benchmark) -> pd.Series:
    return benchmark["close"] if isinstance(benchmark, pd.DataFrame) else benchmark


def _target_at(prices: pd.DataFrame, bench: pd.Series, rf_annual: pd.Series, strategy: str,
               cfg: dict, d: pd.Timestamp) -> tuple[pd.Series, dict]:
    """Tỷ trọng mục tiêu tại ngày quyết định d – nơi DUY NHẤT cắt cửa sổ, lọc mã và chọn rf.

    bench đã reindex theo prices.index. Trả (w trên mọi cột của prices, info).
    """
    per, idx = cfg["periods"], prices.index
    i = idx.get_loc(d)
    s = estimation_start(i, per["estimation_window_days"], per["min_estimation_window_days"], idx)
    win = prices.iloc[s:i + 1]
    tickers = win.columns[win.notna().all()]  # có giá tại d và không NaN trong cửa sổ
    ret_w = win[tickers].pct_change(fill_method=None).iloc[1:]
    mkt_w = bench.iloc[s:i + 1].pct_change(fill_method=None).iloc[1:]
    rf_d = float(rf_annual.loc[:d].iloc[-1]) + _rf_shift(cfg)
    w, info = compute_target_weights(strategy, ret_w, mkt_w, rf_d, tickers, cfg, return_info=True)
    return w.reindex(prices.columns, fill_value=0.0), {
        "window_len": len(ret_w), "fallback": info["fallback"], "tickers": list(tickers), "rf_at_decision": rf_d,
    }


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
    overrides: {"w_max", "rebalance", "fee_per_side", "sell_tax", "rf_shift", "estimation": {...}}.
    Các Series/DataFrame theo kỳ có index = ngày quyết định; `schedule` cho ngày giao dịch tương ứng.
    """
    cfg = apply_overrides(config, overrides)
    per, port, costs = cfg["periods"], cfg["portfolio"], cfg["costs"]
    idx = prices.index
    bench = _close(benchmark).reindex(idx)
    rf_annual = rf["rf_annual"]
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    schedule = []
    for d in decision_dates(idx, start, end, port["rebalance"]):
        i = idx.get_loc(d)
        if i + 1 < len(idx) and idx[i + 1] <= end:
            schedule.append((d, idx[i + 1]))
    if not schedule:
        raise ValueError(f"Không có kỳ giao dịch nào trong [{start.date()}, {end.date()}]")

    targets, window_len, fallback = {}, {}, {}
    for d, _ in schedule:
        targets[d], info = _target_at(prices, bench, rf_annual, strategy, cfg, d)
        window_len[d] = info["window_len"]
        fallback[d] = info["fallback"]

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
        "cash_return": port["cash_return"], "charge_initial": charge_initial, "rf_shift": _rf_shift(cfg),
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
        "fallback": pd.Series(fallback, name="fallback", dtype=bool),
        "cash_weight": net["cash_weight"],
        "trades": net["trades"],
        "nav": net["nav"],
        "cash": net["cash"],
        "holdings": net["holdings"],
        "schedule": pd.DataFrame(schedule, columns=["decision_date", "trade_date"]),
        "meta": meta,
    }


def summarize(result: dict, rf: pd.DataFrame) -> pd.DataFrame:
    """Bảng chỉ số trước/sau phí (metrics.summary với rf_annual_avg_year + rf_shift của meta, khớp Lớp 1).

    turnover_mean bỏ kỳ đầu (xây danh mục từ 100% tiền mặt), giống cách Lớp 1 đếm số lần tái cân bằng.
    turnover_mean, n_holdings_mean lấy từ bản sau phí. cost_pct_nav0 = tổng phí + thuế / vốn ban đầu.
    """
    rf_y = rf["rf_annual_avg_year"] + result["meta"].get("rf_shift", 0.0)
    trades = result["trades"]
    cost = float(trades["fee"].sum() + trades["tax"].sum()) / result["meta"]["nav_vnd"]
    rows = {name: metrics.summary(result[key], rf_y)
            for name, key in (("truoc_phi", "returns_gross"), ("sau_phi", "returns_net"))}
    df = pd.DataFrame(rows).T
    df["turnover_mean"] = float(result["turnover"].iloc[1:].mean())
    df["n_holdings_mean"] = float(result["n_holdings"].mean())
    df["cost_pct_nav0"] = [0.0, cost]
    df["n_fallback"] = int(result["fallback"].sum())
    df.index.name = "bien_the"
    return df


def target_weights_at(prices: pd.DataFrame, benchmark, rf: pd.DataFrame, strategy: str, config: dict,
                      decision_date, overrides: dict | None = None,
                      current_weights: pd.Series | None = None) -> dict:
    """Tỷ trọng mục tiêu và số cổ phiếu tại một ngày quyết định (dùng cho đề xuất Q4/2026).

    Cửa sổ, lọc mã và rf giống hệt run_backtest (cùng _target_at). decision_date phải là phiên có trong
    prices.index. Không dùng dữ liệu sau decision_date.

    Số cổ phiếu tính theo giá đóng cửa TẠI decision_date (giá 30/09/2026 khi đề xuất Q4/2026) vì dữ liệu dừng
    tại đó; giao dịch thật diễn ra ở phiên đầu Q4/2026 nên số lượng và giá thực tế sẽ khác.
    NAV = portfolio.nav_vnd, làm tròn xuống lô, không trừ chi phí khỏi NAV trước khi tính số cổ phiếu.

    current_weights: danh mục đang giữ để ước tính turnover và chi phí (mặc định 1/N đúng trên các mã khả dụng,
    không làm tròn lô). Mã đang giữ mà không còn khả dụng được coi là bán hết.
    cost_pct_nav (thập phân, 0.001 = 0,1% NAV) = Σ mua × fee + Σ bán × (fee + tax), tính trên weights_actual.

    Trả dict: weights, shares, weights_actual, prices (Series trên mọi cột của prices; mã không khả dụng = 0
    hoặc NaN giá), cash_weight, window_len, fallback, n_holdings, turnover, cost_pct_nav, meta.
    """
    cfg = apply_overrides(config, overrides)
    port, costs = cfg["portfolio"], cfg["costs"]
    idx = prices.index
    d = pd.Timestamp(decision_date)
    if d not in idx:
        raise ValueError(f"decision_date {d.date()} không phải phiên có trong dữ liệu giá")
    w, info = _target_at(prices, _close(benchmark).reindex(idx), rf["rf_annual"], strategy, cfg, d)

    px = prices.loc[d]
    nav, lot = port["nav_vnd"], port["lot_size"]
    tickers = info["tickers"]
    shares = pd.Series(0, index=prices.columns, dtype=np.int64)
    shares[tickers] = (np.floor(w[tickers] * nav / px[tickers] / lot) * lot).astype(np.int64)
    w_act = (shares * px).fillna(0.0) / nav

    cur = (pd.Series(1.0 / len(tickers), index=tickers) if current_weights is None
           else pd.Series(current_weights, dtype=float))
    union = w_act.index.union(cur.index)
    delta = w_act.reindex(union).fillna(0.0) - cur.reindex(union).fillna(0.0)
    fee, tax = costs["fee_per_side"], costs["sell_tax"]
    cost = float(delta.clip(lower=0.0).sum() * fee + (-delta.clip(upper=0.0)).sum() * (fee + tax))
    return {
        "weights": w, "shares": shares, "weights_actual": w_act, "prices": px,
        "cash_weight": float(1.0 - w_act.sum()),
        "window_len": info["window_len"], "fallback": info["fallback"],
        "n_holdings": int((shares > 0).sum()),
        "turnover": metrics.turnover(w_act, cur), "cost_pct_nav": cost,
        "meta": {
            "strategy": strategy, "decision_date": str(d.date()), "tickers": tickers,
            "rf_at_decision": info["rf_at_decision"], "rf_shift": _rf_shift(cfg),
            "w_max": port["w_max"], "rebalance": port["rebalance"],
            "fee_per_side": fee, "sell_tax": tax, "estimation": dict(cfg["estimation"]),
            "lot_size": lot, "nav_vnd": nav, "cash_return": port["cash_return"],
            "estimation_window_days": cfg["periods"]["estimation_window_days"],
            "min_estimation_window_days": cfg["periods"]["min_estimation_window_days"],
            "overrides": dict(overrides or {}),
        },
    }


def _rf_values(rf_annual, index: pd.Index) -> np.ndarray:
    """rf năm theo từng ngày của index (cùng cách căn với metrics._daily_rf)."""
    if isinstance(rf_annual, pd.Series):
        return rf_annual.reindex(index).ffill().bfill().to_numpy(dtype=float)
    return np.full(len(index), float(rf_annual))


def sharpe_diff_bootstrap(r_a: pd.Series, r_b: pd.Series, rf_annual, n_boot: int = 2000, block_len: int = 21,
                          seed: int | None = None, rf_annual_b=None) -> dict:
    """Bootstrap khối chồng lấn cho Sharpe(a) − Sharpe(b), lấy mẫu THEO CẶP (cùng ngày cho cả hai chuỗi).

    Mỗi mẫu rút các khối liên tiếp dài block_len, nối lại rồi cắt về đúng n quan sát. rf đi kèm từng quan sát
    theo ngày lịch gốc: mẫu mang chỉ số 0..n−1 và rf cùng chỉ số nên metrics.sharpe_ratio không căn lại theo
    ngày, kể cả khi một ngày xuất hiện nhiều lần.

    rf_annual: số hoặc Series rf năm. rf_annual_b: rf riêng cho chuỗi b, chỉ cần khi hai chuỗi được báo cáo với
    rf khác nhau (dòng rf_shift của lưới độ nhạy); mặc định dùng chung rf_annual.
    seed mặc định = config["seed"]. Khoảng 95% là khoảng phân vị của phân phối bootstrap.
    p_value hai phía = 2 × tỷ lệ mẫu có dấu ngược dấu diff, chặn ≤ 1 (diff = 0 thì p = 1; p = 0 nghĩa là
    không mẫu nào ngược dấu, tức p < 1/n_boot).
    """
    a, b = pd.Series(r_a, dtype=float).dropna(), pd.Series(r_b, dtype=float).dropna()
    common = a.index.intersection(b.index)
    if len(common) < 0.9 * min(len(a), len(b)):
        raise ValueError(f"Hai chuỗi chỉ có {len(common)} ngày chung, ít hơn 90% chuỗi ngắn hơn "
                         f"({min(len(a), len(b))} ngày)")
    n = len(common)
    if n < block_len or block_len < 1:
        raise ValueError(f"Chuỗi có {n} ngày chung, không đủ cho khối dài {block_len}")
    a_v, b_v = a.loc[common].to_numpy(), b.loc[common].to_numpy()
    rf_a = _rf_values(rf_annual, common)
    rf_b = rf_a if rf_annual_b is None else _rf_values(rf_annual_b, common)

    pos = pd.RangeIndex(n)

    def sharpes_on(ix: np.ndarray | slice) -> tuple[float, float]:
        return (metrics.sharpe_ratio(pd.Series(a_v[ix], index=pos), pd.Series(rf_a[ix], index=pos)),
                metrics.sharpe_ratio(pd.Series(b_v[ix], index=pos), pd.Series(rf_b[ix], index=pos)))

    sharpe_a, sharpe_b = sharpes_on(slice(None))
    diff = sharpe_a - sharpe_b

    rng = np.random.default_rng(load()["seed"] if seed is None else seed)
    n_blocks = int(np.ceil(n / block_len))
    starts = rng.integers(0, n - block_len + 1, size=(n_boot, n_blocks))
    samples = (starts[:, :, None] + np.arange(block_len)).reshape(n_boot, -1)[:, :n]
    diffs = np.empty(n_boot)
    for k in range(n_boot):
        s_a, s_b = sharpes_on(samples[k])
        diffs[k] = s_a - s_b
    if not (np.isfinite(diff) and np.isfinite(diffs).all()):
        raise ValueError("Có Sharpe không xác định (độ lệch chuẩn bằng 0) trong điểm ước lượng hoặc mẫu bootstrap")

    ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])
    p = 1.0 if diff == 0 else min(1.0, 2.0 * float(np.mean(np.sign(diffs) == -np.sign(diff))))
    return {"sharpe_a": sharpe_a, "sharpe_b": sharpe_b, "diff": diff, "ci_low": float(ci_low),
            "ci_high": float(ci_high), "p_value": p, "n_obs": n, "n_boot": n_boot, "block_len": block_len}


def verdict(diff: float, ci_low: float, ci_high: float, expected_sign: int) -> str:
    """Kết luận theo mục 1 của docs/A_gia_thuyet.md. expected_sign: +1 kỳ vọng diff ≥ 0, −1 kỳ vọng diff ≤ 0.

    "ung_ho": đúng chiều và khoảng 95% không chứa 0 (nằm hẳn về phía kỳ vọng).
    "dung_chieu_chua_du_bang_chung": đúng chiều (kể cả diff = 0, vì giả thuyết là "không thấp/cao hơn").
    "khong_ung_ho": ngược chiều. Đây chưa phải "bác bỏ": tiêu chí bác bỏ từng giả thuyết nằm ở bảng mục 2.
    """
    if expected_sign not in (1, -1):
        raise ValueError(f"expected_sign phải là 1 hoặc -1, nhận {expected_sign}")
    if expected_sign * diff < 0:
        return "khong_ung_ho"
    far_side = ci_low if expected_sign == 1 else -ci_high  # đầu khoảng gần 0 nhất, theo chiều kỳ vọng
    return "ung_ho" if diff != 0 and far_side > 0 else "dung_chieu_chua_du_bang_chung"


def benchmark_returns(benchmark, index: pd.DatetimeIndex) -> pd.Series:
    """Lợi suất VN-Index trên đúng index của chuỗi danh mục, ngày đầu tiên = 0.

    Danh mục mua ở giá đóng cửa ngày giao dịch đầu nên chưa chịu biến động của ngày đó; VN-Index cũng phải
    xuất phát từ giá đóng cửa ngày đó thì hai chuỗi mới so sánh công bằng.
    """
    px = _close(benchmark).reindex(index)
    if px.isna().any():
        raise ValueError(f"VN-Index thiếu giá tại {list(px.index[px.isna()].date)}")
    r = px.pct_change(fill_method=None)
    r.iloc[0] = 0.0
    return r.rename("VN-Index")


def equity_curve(result: dict, benchmark) -> pd.DataFrame:
    """NAV chuẩn hóa = 1 tại ngày giao dịch đầu, gồm gross, net, VN-Index.

    Lợi suất ngày đầu của net chỉ gồm phí mua lần đầu; chuẩn hóa theo ngày đó nên phí này không hiện trên đường.
    """
    curve = {name: (1.0 + result[key]).cumprod() for name, key in (("gross", "returns_gross"), ("net", "returns_net"))}
    df = pd.DataFrame({name: s / s.iloc[0] for name, s in curve.items()})
    df["VN-Index"] = (1.0 + benchmark_returns(benchmark, df.index)).cumprod()
    return df
