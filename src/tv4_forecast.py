"""Cấp độ DỰ BÁO + đường biên hiệu quả. Chủ file: TV4.

    python src/tv4_forecast.py                     # validation 2020–2021 + đường biên (chạy trước 02/11)
    python src/tv4_forecast.py --period test       # CHỈ chạy sau khi đóng băng 03/11 (để báo cáo, không chọn gì)

1) Sai số dự báo biến động (outputs/forecast_error*.csv)
   Mỗi kỳ quyết định d (cuối quý, cùng lịch và cùng cách cắt cửa sổ với backtest), ước lượng Σ bằng
   "sample" và "ledoit_wolf" trên cửa sổ kết thúc tại d. Dự báo biến động năm của:
     - từng mã (căn bậc hai đường chéo Σ),
     - danh mục 1/N, Min Variance, Risk Parity (tỷ trọng dựng từ CHÍNH Σ đang đánh giá).
   Biến động thực tế = độ lệch chuẩn lợi suất ngày trong quý sau (d, d_kế_tiếp] × √252,
   tỷ trọng giữ cố định trong quý (xấp xỉ; mã mất giá giữa quý tính lợi suất 0 như giữ ở giá cuối).
   Sai số: RMSE, MAE, độ chệch (dự báo − thực tế, âm = dự báo thấp hơn thực tế).
   Không dùng dữ liệu sau d để dự báo; dữ liệu sau d chỉ dùng làm "đáp án" của quý sau.

2) Đường biên hiệu quả có ràng buộc (outputs/frontier.csv) tại kỳ quyết định cuối cùng của dữ liệu
   (30/09/2026 → tỷ trọng cho Q4/2026), μ và Σ theo config.yaml, với từng w_max trong
   sensitivity.w_max và w_max = 1 (không chặn, để so sánh). Kèm điểm của 4 chiến lược và từng mã.

Mọi giả định đọc từ config.yaml. Mọi con số trong report phần 5.4 lấy từ các file này.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import backtest  # noqa: E402
import estimators  # noqa: E402
import optimizers  # noqa: E402
from config import load  # noqa: E402

OUT = ROOT / "outputs"
COV_METHODS = ("sample", "ledoit_wolf")
PORTFOLIOS = ("equal_weight", "min_variance", "risk_parity")


def _window(prices: pd.DataFrame, bench: pd.Series, i: int, cfg: dict):
    """Cửa sổ ước lượng kết thúc tại vị trí i – dùng đúng hàm cắt của backtest."""
    per = cfg["periods"]
    s = backtest.estimation_start(i, per["estimation_window_days"], per["min_estimation_window_days"],
                                  prices.index)
    win = prices.iloc[s:i + 1]
    tickers = list(win.columns[win.notna().all()])
    ret = win[tickers].pct_change(fill_method=None).iloc[1:]
    mkt = bench.iloc[s:i + 1].pct_change(fill_method=None).iloc[1:]
    return ret, mkt, tickers


def _weights(name: str, cov: pd.DataFrame, w_max: float) -> pd.Series:
    if name == "equal_weight":
        return optimizers.equal_weight(list(cov.columns))
    if name == "min_variance":
        return optimizers.min_variance(cov, w_max)
    if name == "risk_parity":
        return optimizers.risk_parity(cov, w_max)
    raise ValueError(name)


def forecast_error(prices: pd.DataFrame, benchmark: pd.Series, rf: pd.DataFrame, cfg: dict,
                   period: str = "validation") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Trả (detail, summary, diagnostics). period = "validation" | "test"."""
    start, end = cfg["periods"][period]
    idx = prices.index
    bench = benchmark.reindex(idx)
    k = cfg["conventions"]["trading_days_per_year"]
    w_max = cfg["portfolio"]["w_max"]
    est = cfg["estimation"]
    ret_all = prices.pct_change(fill_method=None)
    dates = backtest.decision_dates(idx, start, end, cfg["portfolio"]["rebalance"])
    dates = [d for d in dates if d <= pd.Timestamp(end)]

    detail, diag = [], []
    for d, d_next in zip(dates[:-1], dates[1:]):
        i = idx.get_loc(d)
        ret_w, mkt_w, tickers = _window(prices, bench, i, cfg)
        realized = ret_all.loc[(idx > d) & (idx <= d_next), tickers]
        rf_d = float(rf["rf_annual"].loc[:d].iloc[-1])
        drow = {"decision_date": d.date(), "window_len": len(ret_w), "n_assets": len(tickers),
                "lw_shrinkage": estimators.shrinkage_intensity(ret_w)}
        for cm in COV_METHODS:
            S = estimators.covariance(ret_w, cm)
            # từng mã: chỉ mã có đủ giá cả quý sau
            full = realized.columns[realized.notna().all()]
            fc = np.sqrt(np.diag(S.loc[full, full]))
            rv = realized[full].std(ddof=1).to_numpy() * np.sqrt(k)
            for t, f, r in zip(full, fc, rv):
                detail.append({"decision_date": d.date(), "cov_method": cm, "target": "stock",
                               "ticker": t, "forecast_vol": f, "realized_vol": r})
            for p in PORTFOLIOS:
                w = _weights(p, S, w_max)
                f = float(np.sqrt(w @ S @ w))
                r = float((realized.fillna(0.0) @ w).std(ddof=1) * np.sqrt(k))
                detail.append({"decision_date": d.date(), "cov_method": cm, "target": p,
                               "ticker": "", "forecast_vol": f, "realized_vol": r})
                if p != "equal_weight":
                    drow[f"n_pos_{p}_{cm}"] = optimizers.n_positive(w)
            mu = estimators.expected_returns(ret_w, mkt_w, est["expected_returns"], rf_d,
                                             est.get("market_risk_premium"))
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    drow[f"n_pos_max_sharpe_{cm}"] = optimizers.n_positive(
                        optimizers.max_sharpe(mu, S, rf_d, w_max))
            except ValueError:
                drow[f"n_pos_max_sharpe_{cm}"] = np.nan
        diag.append(drow)

    detail = pd.DataFrame(detail)
    detail["error"] = detail["forecast_vol"] - detail["realized_vol"]
    detail.insert(0, "period", period)
    grp = detail.groupby(["target", "cov_method"])["error"]
    summary = pd.DataFrame({
        "rmse": grp.apply(lambda e: float(np.sqrt(np.mean(e ** 2)))),
        "mae": grp.apply(lambda e: float(np.mean(np.abs(e)))),
        "bias": grp.mean(),
        "n": grp.size(),
    }).reset_index()
    summary.insert(0, "period", period)
    meta = {"w_max": w_max, "rebalance": cfg["portfolio"]["rebalance"],
            "mu_method_for_max_sharpe": est["expected_returns"],
            "estimation_window_days": cfg["periods"]["estimation_window_days"],
            "min_estimation_window_days": cfg["periods"]["min_estimation_window_days"]}
    for key, val in meta.items():
        summary[key] = val
    diag = pd.DataFrame(diag)
    diag.insert(0, "period", period)
    diag["mu_method_for_max_sharpe"] = est["expected_returns"]
    diag["w_max"] = w_max
    return detail, summary, diag


def frontier(prices: pd.DataFrame, benchmark: pd.Series, rf: pd.DataFrame, cfg: dict,
             decision_date=None, n_points: int = 40) -> pd.DataFrame:
    """Đường biên + điểm chiến lược + điểm từng mã tại decision_date (mặc định: phiên cuối dữ liệu)."""
    idx = prices.index
    bench = benchmark.reindex(idx)
    d = pd.Timestamp(decision_date) if decision_date is not None else idx[idx <= cfg["data"]["end"]][-1]
    d = idx[idx <= d][-1]
    i = idx.get_loc(d)
    ret_w, mkt_w, tickers = _window(prices, bench, i, cfg)
    est = cfg["estimation"]
    rf_d = float(rf["rf_annual"].loc[:d].iloc[-1])
    S = estimators.covariance(ret_w, est["covariance"])
    mu = estimators.expected_returns(ret_w, mkt_w, est["expected_returns"], rf_d,
                                     est.get("market_risk_premium"))
    base = {"decision_date": d.date(), "window_len": len(ret_w), "mu_method": est["expected_returns"],
            "cov_method": est["covariance"], "rf_annual": rf_d}
    rows = []
    for w_max in list(cfg["sensitivity"]["w_max"]) + [1.0]:
        label_w = "khong_chan" if w_max >= 1.0 else f"{w_max:.2f}"
        pts, _ = optimizers.efficient_frontier(mu, S, w_max, n_points=n_points, rf_annual=rf_d)
        for k, r in pts.iterrows():
            rows.append({**base, "w_max": w_max, "w_max_label": label_w, "point_type": "frontier",
                         "label": f"diem_{k:02d}", **r.drop("target_return").to_dict()})
        strat = {"equal_weight": optimizers.equal_weight(tickers),
                 "min_variance": optimizers.min_variance(S, w_max),
                 "max_sharpe": optimizers.max_sharpe(mu, S, rf_d, w_max),
                 "risk_parity": optimizers.risk_parity(S, w_max)}
        for name, w in strat.items():
            rows.append({**base, "w_max": w_max, "w_max_label": label_w, "point_type": "strategy",
                         "label": name, **optimizers.portfolio_stats(w, mu, S, rf_d)})
    for t in tickers:
        vol = float(np.sqrt(S.loc[t, t]))
        rows.append({**base, "w_max": np.nan, "w_max_label": "", "point_type": "asset", "label": t,
                     "exp_return": float(mu[t]), "volatility": vol,
                     "sharpe": (float(mu[t]) - rf_d) / vol, "n_positive": 1})
    return pd.DataFrame(rows)


def run(period: str = "validation", with_frontier: bool = True) -> list[Path]:
    cfg = load()
    P, V, R = backtest.load_inputs()
    OUT.mkdir(exist_ok=True)
    written = []
    detail, summary, diag = forecast_error(P, V, R, cfg, period)
    suffix = "" if period == "validation" else f"_{period}"
    for name, df in ((f"forecast_error{suffix}.csv", summary),
                     (f"forecast_error_detail{suffix}.csv", detail),
                     (f"estimation_diagnostics{suffix}.csv", diag)):
        df.to_csv(OUT / name, index=False, encoding="utf-8-sig")
        written.append(OUT / name)
    if with_frontier:
        fr = frontier(P, V, R, cfg)
        fr.to_csv(OUT / "frontier.csv", index=False, encoding="utf-8-sig")
        written.append(OUT / "frontier.csv")
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", choices=["validation", "test"], default="validation")
    ap.add_argument("--no-frontier", action="store_true")
    a = ap.parse_args()
    if a.period == "test":
        print("CHÚ Ý: tập test chỉ chạy SAU khi đóng băng (03/11) và không dùng để chọn thiết kế.")
    for p in run(a.period, not a.no_frontier):
        print("[TV4] Đã ghi", p.relative_to(ROOT))
