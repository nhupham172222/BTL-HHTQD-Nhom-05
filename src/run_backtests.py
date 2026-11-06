"""Chạy backtest chính thức và xuất CSV cho report, dashboard. Chủ file: TV5.

    python src/run_backtests.py --period validation
    python src/run_backtests.py --period test --i-confirm-freeze    # CHỈ MỘT LẦN, sau khi đóng băng thiết kế

--period validation ghi: validation_results.csv, validation_window_len.csv, validation_design_choice.csv.
--period test ghi:       test_results.csv, equity_curves.csv, sensitivity_grid.csv, weights_Q4_2026.csv.

Mọi file đều có cột cấu hình (từ meta), ngày chạy và git commit (thêm "-dirty" nếu còn thay đổi chưa commit).
Mọi tham số đọc từ config.yaml; n_boot, block_len theo mặc định của backtest.sharpe_diff_bootstrap.
Tỷ lệ chi phí và tỷ trọng ở dạng thập phân (0.01 = 1%). Sharpe, Sortino dùng rf_annual_avg_year + rf_shift.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import backtest  # noqa: E402
import estimators  # noqa: E402
import metrics  # noqa: E402
from config import load  # noqa: E402

OUT_DIR = ROOT / "outputs"
REMINDER = "Test chỉ chạy một lần sau khi đóng băng – không dùng để chọn thiết kế."
FREEZE_REQUIRED = ("DỪNG: --period test cần cờ --i-confirm-freeze. Chưa tính gì, chưa ghi file nào. " + REMINDER)
DESIGN_RULE = ("Chọn phương án có Sharpe sau phí cao hơn trên validation; nếu khoảng bootstrap 95% của chênh lệch "
               "chứa 0 thì giữ mặc định (μ = capm, Σ = ledoit_wolf).")
NA = "n/a"
BASELINE = "equal_weight"
H1_EXPECTED_SIGN = {"min_variance": 1, "risk_parity": 1, "max_sharpe": -1}  # so với 1/N, A_gia_thuyet.md H1
_METRICS = (("sharpe", "sharpe"), ("sortino", "sortino"), ("loi_suat_nam", "annual_return"),
            ("do_lech_chuan", "annual_volatility"), ("mdd", "max_drawdown"))
_CONFIG_COLS = ("start", "end", "decision_date", "w_max", "rebalance", "fee_per_side", "sell_tax", "rf_shift",
                "lot_size", "nav_vnd", "cash_return", "charge_initial",
                "estimation_window_days", "min_estimation_window_days")
_ESTIMATION_COLS = ("market_risk_premium", "max_sharpe_if_no_excess")


def _git_commit() -> str:
    """Hash commit hiện tại, thêm "-dirty" nếu file đã theo dõi còn thay đổi; không lấy được thì để trống."""
    try:
        return subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=7"], cwd=ROOT, text=True,
                              capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _stamp() -> dict:
    return {"ngay_chay": dt.date.today().isoformat(), "git_commit": _git_commit()}


def _config_cols(meta: dict) -> dict:
    cols = {k: meta[k] for k in _CONFIG_COLS if k in meta}
    cols.update({k: meta["estimation"].get(k) for k in _ESTIMATION_COLS})
    return cols


def _write(frames: dict[str, pd.DataFrame], out_dir: Path, stamp: dict) -> None:
    """Ghi sau khi đã tính xong mọi thứ, để lỗi giữa chừng không để lại bộ file dở dang."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        df.assign(**stamp).to_csv(out_dir / name, index=False, encoding="utf-8-sig")
        print(f"Đã ghi {out_dir / name}")


def _labels(strategy: str, mu: str, cov: str) -> dict:
    """Phương pháp thực sự dùng: 1/N không dùng μ, Σ; Min Variance và Risk Parity không dùng μ."""
    return {"chien_luoc": strategy,
            "mu": mu if strategy == "max_sharpe" else NA,
            "cov": NA if strategy == BASELINE else cov}


def _metric_cols(rows: dict) -> dict:
    """rows: {"truoc_phi": dict chỉ số, "sau_phi": dict chỉ số}."""
    return {f"{col}_{phase}": rows[phase][key] for phase in ("truoc_phi", "sau_phi") for col, key in _METRICS}


def _row(result: dict, rf: pd.DataFrame) -> dict:
    """Các cột chỉ số dùng chung cho validation, test và lưới độ nhạy."""
    table = backtest.summarize(result, rf)
    net = table.loc["sau_phi"]
    years = len(result["returns_net"]) / load()["conventions"]["trading_days_per_year"]
    window = result["window_len"]
    return {
        **_metric_cols({"truoc_phi": table.loc["truoc_phi"], "sau_phi": net}),
        "turnover_tb": net["turnover_mean"],                                # mỗi kỳ, bỏ kỳ đầu
        "turnover_tb_nam": float(result["turnover"].iloc[1:].sum() / years),  # tổng turnover / số năm
        "n_holdings_tb": net["n_holdings_mean"],
        "cash_weight_tb": float(result["cash_weight"].mean()),
        "n_fallback": int(net["n_fallback"]),
        "tong_phi_thue_pct_nav0": net["cost_pct_nav0"],
        "window_len_min": int(window.min()),
        "window_len_max": int(window.max()),
        "so_ky": len(result["schedule"]),
    }


def _estimation_override(mu: str | None = None, cov: str | None = None) -> dict:
    est = {}
    if mu is not None:
        est["expected_returns"] = mu
    if cov is not None:
        est["covariance"] = cov
    return {"estimation": est}


def _rf_report(rf: pd.DataFrame, result: dict) -> pd.Series:
    return rf["rf_annual_avg_year"] + result["meta"]["rf_shift"]


def _inputs_until(inputs, end) -> tuple:
    """Cắt dữ liệu tới hết giai đoạn đang chạy: dữ liệu sau đó không có mặt nên không thể bị dùng."""
    P, V, R = inputs if inputs is not None else backtest.load_inputs()
    return P.loc[:end], V.loc[:end], R.loc[:end]


# --- validation --------------------------------------------------------------------------------

def _choice_by_rule(diff: float, ci_low: float, ci_high: float, a: str, b: str, default: str) -> str:
    if ci_low <= 0 <= ci_high:
        return default
    return a if diff > 0 else b


def _design_row(variable: str, strategy: str, a: str, b: str, default: str,
                res_a: dict, res_b: dict, rf: pd.DataFrame, boot: dict) -> dict:
    """So sánh phương án a với b trên lợi suất sau phí; diff = Sharpe(a) − Sharpe(b)."""
    t = backtest.sharpe_diff_bootstrap(res_a["returns_net"], res_b["returns_net"], _rf_report(rf, res_a), **boot)
    return {"bien_thiet_ke": variable, "chien_luoc": strategy, "phuong_an_a": a, "phuong_an_b": b,
            "mac_dinh": default, **t,
            "lua_chon_theo_quy_tac": _choice_by_rule(t["diff"], t["ci_low"], t["ci_high"], a, b, default),
            "ghi_chu": DESIGN_RULE, **_config_cols(res_a["meta"])}


def run_validation(cfg: dict | None = None, out_dir: Path = OUT_DIR, inputs=None, boot: dict | None = None) -> dict:
    """Chạy lưới μ × Σ trên validation. Chỉ đề xuất thiết kế, KHÔNG sửa config."""
    cfg = load() if cfg is None else cfg
    boot = boot or {}
    start, end = cfg["periods"]["validation"]
    P, V, R = _inputs_until(inputs, end)
    est = cfg["estimation"]

    combos = [(BASELINE, NA, NA)]
    combos += [(s, NA, c) for s in ("min_variance", "risk_parity") for c in estimators.COV_METHODS]
    combos += [("max_sharpe", m, c) for m in estimators.MU_METHODS for c in estimators.COV_METHODS]

    results, rows = {}, []
    for strategy, mu, cov in combos:
        over = _estimation_override(None if mu == NA else mu, None if cov == NA else cov)
        res = backtest.run_backtest(P, V, R, strategy, cfg, start, end, overrides=over)
        results[strategy, mu, cov] = res
        rows.append({"chien_luoc": strategy, "mu": mu, "cov": cov, **_row(res, R), **_config_cols(res["meta"])})

    base = results[BASELINE, NA, NA]
    for res in results.values():  # window_len không phụ thuộc chiến lược; lệch nghĩa là lỗi cắt cửa sổ
        pd.testing.assert_series_equal(res["window_len"], base["window_len"])
    window = base["schedule"].assign(window_len=base["window_len"].to_numpy(), **_config_cols(base["meta"]))

    design = []
    for strategy, mu in (("min_variance", NA), ("risk_parity", NA), ("max_sharpe", "capm")):
        design.append(_design_row("cov", strategy, "ledoit_wolf", "sample", est["covariance"],
                                  results[strategy, mu, "ledoit_wolf"], results[strategy, mu, "sample"], R, boot))
    design.append(_design_row("mu", "max_sharpe", "historical", "capm", est["expected_returns"],
                              results["max_sharpe", "historical", "ledoit_wolf"],
                              results["max_sharpe", "capm", "ledoit_wolf"], R, boot))

    frames = {"validation_results.csv": pd.DataFrame(rows),
              "validation_window_len.csv": window,
              "validation_design_choice.csv": pd.DataFrame(design)}
    _write(frames, out_dir, _stamp())
    return frames


# --- test (chỉ chạy một lần, sau khi đóng băng) ----------------------------------------------------

def _test_results(results: dict, V, R, cfg: dict, boot: dict) -> pd.DataFrame:
    est = cfg["estimation"]
    base = results[BASELINE]
    rows = []
    for strategy, res in results.items():
        row = {**_labels(strategy, est["expected_returns"], est["covariance"]), **_row(res, R)}
        sign = H1_EXPECTED_SIGN.get(strategy)
        if sign is not None:
            t = backtest.sharpe_diff_bootstrap(res["returns_net"], base["returns_net"], _rf_report(R, res), **boot)
            row.update(diff_vs_1n=t["diff"], ci_low_vs_1n=t["ci_low"], ci_high_vs_1n=t["ci_high"],
                       p_value_vs_1n=t["p_value"], ky_vong_dau_h1=sign,
                       verdict_h1=backtest.verdict(t["diff"], t["ci_low"], t["ci_high"], sign))
        rows.append({**row, **_config_cols(res["meta"])})
    # VN-Index không có giao dịch: trước phí = sau phí, các cột danh mục để trống
    r_vn = backtest.benchmark_returns(V, base["returns_net"].index)
    vn = metrics.summary(r_vn, R["rf_annual_avg_year"])
    rows.append({"chien_luoc": "VN-Index", "mu": NA, "cov": NA, **_metric_cols({"truoc_phi": vn, "sau_phi": vn}),
                 **_config_cols(base["meta"])})
    return pd.DataFrame(rows)


def _equity_long(results: dict, V) -> pd.DataFrame:
    parts = []
    curve = None
    for strategy, res in results.items():
        curve = backtest.equity_curve(res, V)
        cfg_cols = _config_cols(res["meta"])
        for col in ("gross", "net"):
            parts.append(pd.DataFrame({"date": curve.index, "series": f"{strategy}_{col}",
                                       "value": curve[col].to_numpy(), **cfg_cols}))
    parts.append(pd.DataFrame({"date": curve.index, "series": "VN-Index", "value": curve["VN-Index"].to_numpy(),
                               **cfg_cols}))
    return pd.concat(parts, ignore_index=True)


def _sensitivity_cases(cfg: dict) -> list[tuple]:
    """Đổi TỪNG biến một quanh mặc định. Mỗi phần tử: (biến, giá trị, overrides, chiến lược, có phải mặc định)."""
    grid, est = cfg["sensitivity"], cfg["estimation"]
    all4 = tuple(cfg["strategies"])
    cases = []
    defaults = {"w_max": cfg["portfolio"]["w_max"], "rebalance": cfg["portfolio"]["rebalance"],
                "fee_per_side": cfg["costs"]["fee_per_side"], "rf_shift": 0.0}
    for var, default in defaults.items():
        cases += [(var, v, {var: v}, all4, v == default) for v in grid[var]]
    cases += [("market_risk_premium", v, {"estimation": {"market_risk_premium": v}}, ("max_sharpe",),
               v == est["market_risk_premium"]) for v in grid["market_risk_premium"]]
    # H3, H4: giữ đủ 4 chiến lược để kiểm tra "μ, Σ không làm đổi chiến lược không dùng chúng"
    cases += [("cov", v, _estimation_override(cov=v), all4, v == est["covariance"]) for v in estimators.COV_METHODS]
    cases += [("mu", v, _estimation_override(mu=v), all4, v == est["expected_returns"]) for v in estimators.MU_METHODS]
    return cases


def _sensitivity_grid(results: dict, P, V, R, cfg: dict, start, end, boot: dict) -> pd.DataFrame:
    est = cfg["estimation"]
    rows = []
    for var, value, over, strategies, is_default in _sensitivity_cases(cfg):
        for strategy in strategies:
            base = results[strategy]
            res = base if is_default else backtest.run_backtest(P, V, R, strategy, cfg, start, end, overrides=over)
            if is_default:
                diff = {"diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": 1.0}
            else:  # dòng rf_shift: mỗi bên Sharpe tính với rf của chính nó, khớp cột sharpe_sau_phi
                t = backtest.sharpe_diff_bootstrap(res["returns_net"], base["returns_net"], _rf_report(R, res),
                                                   rf_annual_b=_rf_report(R, base), **boot)
                diff = {k: t[k] for k in ("diff", "ci_low", "ci_high", "p_value")}
            over_est = over.get("estimation", {})
            labels = _labels(strategy, over_est.get("expected_returns", est["expected_returns"]),
                             over_est.get("covariance", est["covariance"]))
            rows.append({"bien_thay_doi": var, "gia_tri": str(value), "la_mac_dinh": bool(is_default), **labels,
                         **_row(res, R), **{f"{k}_vs_mac_dinh": v for k, v in diff.items()},
                         **_config_cols(res["meta"])})
    return pd.DataFrame(rows)


def _weights_table(P, V, R, cfg: dict, as_of) -> pd.DataFrame:
    rows = []
    for strategy in cfg["strategies"]:
        tw = backtest.target_weights_at(P, V, R, strategy, cfg, as_of)
        for ticker in tw["meta"]["tickers"]:
            rows.append({"chien_luoc": strategy, "ticker": ticker, "weight_target": tw["weights"][ticker],
                         "shares": int(tw["shares"][ticker]), "weight_actual": tw["weights_actual"][ticker],
                         "gia_dung": tw["prices"][ticker], "turnover_vs_1n": tw["turnover"],
                         "cost_pct_nav_vs_1n": tw["cost_pct_nav"], "cash_weight": tw["cash_weight"],
                         "n_holdings": tw["n_holdings"], "fallback": tw["fallback"],
                         "window_len": tw["window_len"], "rf_at_decision": tw["meta"]["rf_at_decision"],
                         **_config_cols(tw["meta"])})
    return pd.DataFrame(rows)


def run_test_period(cfg: dict | None = None, out_dir: Path = OUT_DIR, inputs=None, boot: dict | None = None,
                    period=None, as_of=None) -> dict:
    """Chạy giai đoạn test. Lần chạy chính thức dùng mặc định: period = periods.test, as_of = phiên cuối của data.end.

    period, as_of chỉ để unit test chạy thử đường đi này trên khoảng validation và thư mục tạm.
    """
    print(REMINDER)
    cfg = load() if cfg is None else cfg
    boot = boot or {}
    start, end = period if period is not None else cfg["periods"]["test"]
    P, V, R = _inputs_until(inputs, end)
    if as_of is None:
        as_of = P.index[P.index <= pd.Timestamp(cfg["data"]["end"])][-1]

    results = {s: backtest.run_backtest(P, V, R, s, cfg, start, end) for s in cfg["strategies"]}
    frames = {"test_results.csv": _test_results(results, V, R, cfg, boot),
              "equity_curves.csv": _equity_long(results, V),
              "sensitivity_grid.csv": _sensitivity_grid(results, P, V, R, cfg, start, end, boot),
              "weights_Q4_2026.csv": _weights_table(P, V, R, cfg, as_of)}
    _write(frames, out_dir, _stamp())
    print(REMINDER)
    return frames


# --- CLI -----------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backtest chính thức: validation hoặc test")
    ap.add_argument("--period", required=True, choices=["validation", "test"])
    ap.add_argument("--i-confirm-freeze", action="store_true",
                    help="bắt buộc với --period test: xác nhận thiết kế đã đóng băng")
    args = ap.parse_args(argv)

    if args.period == "test":
        if not args.i_confirm_freeze:
            print(FREEZE_REQUIRED, file=sys.stderr)
            return 2
        run_test_period()
        return 0

    frames = run_validation()
    pd.set_option("display.width", 250, "display.max_columns", None, "display.max_colwidth", 60)
    for name, df in frames.items():
        print(f"\n=== {name} ===")
        hidden = {"ghi_chu", *_CONFIG_COLS, *_ESTIMATION_COLS} - {"decision_date"}
        print(df.drop(columns=list(hidden), errors="ignore").to_string(index=False))
    print("\nQuy tắc chọn thiết kế:", DESIGN_RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
