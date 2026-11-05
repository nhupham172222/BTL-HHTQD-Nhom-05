"""Kiểm tra src/backtest.py. Chủ file: TV5.

    python -m pytest tests/test_backtest.py -q

Chỉ dùng dữ liệu đến hết validation 2020–2021 hoặc dữ liệu giả; không chạy trên giai đoạn test.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import backtest  # noqa: E402
from config import load  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return backtest.load_inputs()


@pytest.fixture(scope="module")
def cfg():
    return load()


@pytest.fixture(scope="module")
def val_1n(data, cfg):
    P, V, R = data
    return backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"])


def _fake_min_variance(monkeypatch):
    """Thay estimators/optimizers (TV4 chưa xong) bằng bản đơn giản PHỤ THUỘC dữ liệu cửa sổ:
    Σ mẫu và tỷ trọng nghịch đảo phương sai có chặn w_max."""
    def covariance(R, method):
        return R.cov() * 252

    def min_variance(cov, w_max):
        w = 1.0 / pd.Series(np.diag(cov), index=cov.index)
        w = w / w.sum()
        for _ in range(100):
            over = w > w_max
            if not over.any():
                break
            spare = (w[over] - w_max).sum()
            w[over] = w_max
            w[~over] += spare * w[~over] / w[~over].sum()
        return w

    monkeypatch.setattr(backtest.estimators, "covariance", covariance)
    monkeypatch.setattr(backtest.optimizers, "min_variance", min_variance)


# --- Lịch và cửa sổ --------------------------------------------------------------------------

def test_lich_quy_validation(val_1n):
    s = val_1n["schedule"]
    assert s["decision_date"].iloc[0] == pd.Timestamp("2019-12-31")
    assert s["trade_date"].iloc[0] == pd.Timestamp("2020-01-02")
    assert (s["trade_date"] > s["decision_date"]).all()
    assert val_1n["returns_net"].index[0] == pd.Timestamp("2020-01-02")
    assert val_1n["returns_net"].index[-1] == pd.Timestamp("2021-12-31")


@pytest.mark.parametrize("freq, n", [("monthly", 24), ("quarterly", 8), ("semiannual", 4)])
def test_tan_suat_tai_can_bang(data, cfg, freq, n):
    idx = data[0].index
    d = backtest.decision_dates(idx, "2020-01-01", "2021-12-31", freq)
    assert d[0] == pd.Timestamp("2019-12-31")
    assert len(d) == n + 1  # gồm 2021-12-31 (sẽ bị bỏ vì phiên giao dịch nằm sau end)


def test_window_len_validation(val_1n, cfg):
    wl = val_1n["window_len"]
    assert wl.iloc[0] == 291
    assert wl.is_monotonic_increasing
    assert wl.max() <= cfg["periods"]["estimation_window_days"]


def test_cua_so_ngan_bao_loi(data, cfg):
    P, V, R = data
    with pytest.raises(ValueError, match="252"):
        backtest.run_backtest(P, V, R, "equal_weight", cfg, "2019-07-01", "2019-12-31")
    with pytest.raises(ValueError):
        backtest.estimation_start(100, 756, 252)
    assert backtest.estimation_start(1000, 756, 252) == 244
    assert backtest.estimation_start(252, 756, 252) == 0


# --- Mô phỏng giao dịch ------------------------------------------------------------------------

def test_lo_100_va_tien_khong_am(val_1n, cfg):
    lot = cfg["portfolio"]["lot_size"]
    assert (val_1n["holdings"] % lot == 0).all().all()
    assert (val_1n["trades"]["shares"] % lot == 0).all()
    assert (val_1n["trades"]["shares"] > 0).all()
    assert (val_1n["cash"] >= 0).all()


def test_phi_bang_0_thi_net_bang_gross(data, cfg):
    P, V, R = data
    res = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                                overrides={"fee_per_side": 0.0, "sell_tax": 0.0})
    pd.testing.assert_series_equal(res["returns_net"], res["returns_gross"], check_names=False)


def test_co_phi_thi_net_thap_hon_gross(val_1n):
    assert val_1n["nav"].iloc[-1] < (1 + val_1n["returns_gross"]).prod() * val_1n["meta"]["nav_vnd"]
    assert val_1n["returns_net"].iloc[0] < 0  # lần mua đầu có phí (charge_initial=True)


def test_nav_giam_dung_bang_phi_thue(val_1n, data):
    """Ngày giao dịch: NAV(danh mục cũ, giá hôm nay) − phí − thuế = NAV sau giao dịch."""
    px = data[0].ffill()
    nav, cash, hold, tr = val_1n["nav"], val_1n["cash"], val_1n["holdings"], val_1n["trades"]
    sched = val_1n["schedule"]
    for k in range(1, len(sched)):
        t = sched["trade_date"].iloc[k]
        prev_h = hold.loc[sched["decision_date"].iloc[k - 1]]
        prev_cash = cash.loc[:t].iloc[-2]
        before = float((prev_h * px.loc[t]).where(prev_h > 0, 0.0).sum() + prev_cash)
        paid = tr.loc[tr["date"] == t, ["fee", "tax"]].to_numpy().sum()
        assert nav.loc[t] == pytest.approx(before - paid, abs=1e-3)


def test_charge_initial_false(data, cfg):
    P, V, R = data
    res = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                                charge_initial=False)
    assert res["returns_net"].iloc[0] == pytest.approx(0.0, abs=1e-12)
    t0 = res["schedule"]["trade_date"].iloc[0]
    first = res["trades"][res["trades"]["date"] == t0]
    assert (first[["fee", "tax"]].to_numpy() == 0).all()


# --- Giả thuyết H2 và chống nhìn trước ----------------------------------------------------------

def test_1n_khong_doi_theo_w_max(data, cfg):
    P, V, R = data
    a = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                              overrides={"w_max": 0.05})
    b = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                              overrides={"w_max": 0.20})
    for key in ("returns_net", "returns_gross", "nav"):
        pd.testing.assert_series_equal(a[key], b[key])
    pd.testing.assert_frame_equal(a["weights"], b["weights"])
    assert a["meta"]["w_max"] == 0.05 and b["meta"]["w_max"] == 0.20


@pytest.mark.parametrize("strategy", ["equal_weight", "min_variance"])
def test_khong_nhin_truoc(data, cfg, monkeypatch, strategy):
    _fake_min_variance(monkeypatch)
    P, V, R = data
    start, end = cfg["periods"]["validation"]
    d = pd.Timestamp("2020-06-30")
    base = backtest.run_backtest(P, V, R, strategy, cfg, start, end)

    rng = np.random.default_rng(cfg["seed"])
    after = P.index > d
    P2 = P.copy()
    P2.loc[after] = P2.loc[after] * rng.uniform(0.5, 1.5, size=P2.loc[after].shape)
    V2 = V.copy()
    V2.loc[after] = V2.loc[after] * rng.uniform(0.5, 1.5, size=after.sum())
    R2 = R.copy()
    R2.loc[after, "rf_annual"] = R2.loc[after, "rf_annual"] + 0.05
    pert = backtest.run_backtest(P2, V2, R2, strategy, cfg, start, end)

    pd.testing.assert_frame_equal(base["weights"].loc[:d], pert["weights"].loc[:d])
    if strategy == "min_variance":  # nhiễu có tác dụng: các kỳ SAU d phải đổi
        assert not np.allclose(base["weights"].loc[d:].iloc[1:], pert["weights"].loc[d:].iloc[1:])


def test_rf_lay_rf_annual_tai_ngay_quyet_dinh(data, cfg, monkeypatch):
    P, V, R = data
    seen = {}

    def capture(strategy, ret_window, mkt_window, rf_at_decision, tickers, cfg_, return_info=False):
        seen[ret_window.index[-1]] = rf_at_decision
        return pd.Series(1.0 / len(tickers), index=list(tickers)), {"fallback": False}

    monkeypatch.setattr(backtest, "compute_target_weights", capture)
    backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"])
    for d, rf_d in seen.items():
        assert rf_d == R.loc[d, "rf_annual"]


def test_chien_luoc_khong_hop_le(data, cfg):
    P, V, R = data
    with pytest.raises(ValueError):
        backtest.run_backtest(P, V, R, "abc", cfg, *cfg["periods"]["validation"])
    with pytest.raises(ValueError):
        backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                              overrides={"khong_co": 1})


# --- Mã ngừng giao dịch: dữ liệu giả, vì ROS thật ngừng 08/2022, thuộc giai đoạn test -----------------

@pytest.fixture(scope="module")
def halted_data():
    """12 mã, 520 phiên từ 2019; mã HALT ngừng giao dịch sau 2020-08-11."""
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2019-01-01", "2020-12-31")
    cols = [f"M{k:02d}" for k in range(11)] + ["HALT"]
    P = pd.DataFrame(20_000 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, (len(idx), 12)), axis=0)),
                     index=idx, columns=cols)
    P.loc[P.index > "2020-08-11", "HALT"] = np.nan
    V = pd.Series(900 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(idx)))), index=idx, name="close")
    R = pd.DataFrame({"rf_annual": 0.03, "rf_annual_avg_year": 0.03}, index=idx)
    return P, V, R


def test_ma_ngung_giao_dich_bi_loai_va_ban_het(halted_data, cfg):
    P, V, R = halted_data
    res = backtest.run_backtest(P, V, R, "equal_weight", cfg, "2020-07-01", "2020-10-31")
    w, hold, tr = res["weights"], res["holdings"], res["trades"]
    q2, q3 = pd.Timestamp("2020-06-30"), pd.Timestamp("2020-09-30")
    assert w.loc[q2, "HALT"] > 0 and hold.loc[q2, "HALT"] > 0
    assert (w.loc[q3:, "HALT"] == 0).all()
    assert hold.loc[q3, "HALT"] == 0

    t = res["schedule"].set_index("decision_date").loc[q3, "trade_date"]
    assert t == pd.Timestamp("2020-10-01")
    halted = tr[(tr["ticker"] == "HALT") & (tr["date"] == t)]
    assert len(halted) == 1 and halted["side"].iloc[0] == "sell"
    assert halted["shares"].iloc[0] == hold.loc[q2, "HALT"]
    assert halted["price"].iloc[0] == P["HALT"].dropna().iloc[-1]
    assert halted["tax"].iloc[0] > 0 and halted["fee"].iloc[0] > 0
    assert res["nav"].notna().all()  # giữa hai kỳ, mã ngừng giao dịch định giá ở giá cuối


# --- B1: kỳ dùng Min Variance thay thế (A15) -----------------------------------------------------

MS_HISTORICAL = {"estimation": {"expected_returns": "historical"}}


def test_config_co_khoa_a15(cfg):
    assert cfg["estimation"]["max_sharpe_if_no_excess"] == "min_variance"


def test_fallback_dung_ky_31_03_2020(data, cfg):
    """Cửa sổ kết thúc 31/03/2020 (kỳ 2019-12-31 → 2020-03-31): μ lịch sử không có danh mục vượt rf."""
    P, V, R = data
    res = backtest.run_backtest(P, V, R, "max_sharpe", cfg, *cfg["periods"]["validation"], overrides=MS_HISTORICAL)
    fb = res["fallback"]
    assert list(fb.index) == list(res["schedule"]["decision_date"])
    assert list(fb[fb].index) == [pd.Timestamp("2020-03-31")]
    assert not fb.loc["2019-12-31"]
    assert backtest.summarize(res, R)["n_fallback"].tolist() == [1, 1]

    d = pd.Timestamp("2020-03-31")
    mv = backtest.run_backtest(P, V, R, "min_variance", cfg, *cfg["periods"]["validation"], overrides=MS_HISTORICAL)
    pd.testing.assert_series_equal(res["weights"].loc[d], mv["weights"].loc[d])


def test_fallback_khong_phu_thuoc_bo_loc_canh_bao(data, cfg):
    """Cờ fallback vẫn đúng ở mọi lần gọi, kể cả khi bên ngoài tắt cảnh báo (vd python -W ignore)."""
    P, V, R = data
    d = pd.Timestamp("2020-03-31")
    win = P.loc[:d]
    ret, mkt = win.pct_change(fill_method=None).iloc[1:], V.loc[:d].pct_change(fill_method=None).iloc[1:]
    cfg2 = backtest.apply_overrides(cfg, MS_HISTORICAL)
    rf_d = float(R["rf_annual"].loc[d])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        flags = [backtest.compute_target_weights("max_sharpe", ret, mkt, rf_d, list(P.columns), cfg2,
                                                 return_info=True)[1]["fallback"] for _ in range(3)]
    assert flags == [True, True, True]


def test_compute_target_weights_giu_chu_ky_cu(data, cfg):
    P, V, R = data
    d = pd.Timestamp("2019-12-31")
    ret = P.loc[:d].pct_change(fill_method=None).iloc[1:]
    mkt = V.loc[:d].pct_change(fill_method=None).iloc[1:]
    w = backtest.compute_target_weights("equal_weight", ret, mkt, 0.03, list(P.columns), cfg)
    assert isinstance(w, pd.Series)
    w2, info = backtest.compute_target_weights("equal_weight", ret, mkt, 0.03, list(P.columns), cfg, return_info=True)
    pd.testing.assert_series_equal(w, w2)
    assert info == {"fallback": False}


# --- B2: target_weights_at ----------------------------------------------------------------------

@pytest.mark.parametrize("strategy", backtest.STRATEGIES)
def test_target_weights_at_khop_run_backtest(data, cfg, strategy):
    P, V, R = data
    d = pd.Timestamp("2020-09-30")
    res = backtest.run_backtest(P, V, R, strategy, cfg, *cfg["periods"]["validation"])
    tw = backtest.target_weights_at(P, V, R, strategy, cfg, d)
    pd.testing.assert_series_equal(tw["weights"], res["weights"].loc[d], check_names=False)
    assert tw["window_len"] == res["window_len"].loc[d]
    assert tw["fallback"] == res["fallback"].loc[d]

    lot = cfg["portfolio"]["lot_size"]
    assert (tw["shares"] % lot == 0).all() and (tw["shares"] >= 0).all()
    assert tw["cash_weight"] >= 0
    px = P.loc[d]
    nav = cfg["portfolio"]["nav_vnd"]
    used = tw["weights"] > 0
    # làm tròn XUỐNG: không vượt mục tiêu và thiếu dưới một lô
    gap = (tw["weights"] * nav - tw["shares"] * px)[used]
    assert (gap >= -1e-6).all() and (gap <= lot * px[used] + 1e-6).all()
    assert tw["n_holdings"] == int((tw["shares"] > 0).sum())
    assert tw["weights_actual"].sum() + tw["cash_weight"] == pytest.approx(1.0)


def test_target_weights_at_khong_nhin_truoc(data, cfg):
    P, V, R = data
    d = pd.Timestamp("2020-09-30")
    a = backtest.target_weights_at(P, V, R, "min_variance", cfg, d)
    b = backtest.target_weights_at(P.loc[:d], V.loc[:d], R.loc[:d], "min_variance", cfg, d)
    pd.testing.assert_series_equal(a["weights"], b["weights"])
    pd.testing.assert_series_equal(a["shares"], b["shares"])


def test_target_weights_at_turnover_va_chi_phi(data, cfg):
    P, V, R = data
    d = pd.Timestamp("2020-09-30")
    # Mặc định so với 1/N: danh mục 1/N chỉ chênh phần làm tròn lô, nên gần như không phải bán
    eq = backtest.target_weights_at(P, V, R, "equal_weight", cfg, d)
    assert eq["turnover"] < 0.01

    # Đang giữ đúng danh mục thực tế: không giao dịch, không chi phí
    same = backtest.target_weights_at(P, V, R, "min_variance", cfg, d)
    held = backtest.target_weights_at(P, V, R, "min_variance", cfg, d, current_weights=same["weights_actual"])
    assert held["turnover"] == pytest.approx(0.0) and held["cost_pct_nav"] == pytest.approx(0.0)

    # Tính tay: bán hết vào tiền mặt chịu fee + tax; từ tiền mặt mua chịu fee
    fee, tax = cfg["costs"]["fee_per_side"], cfg["costs"]["sell_tax"]
    w_act = same["weights_actual"]
    from_cash = backtest.target_weights_at(P, V, R, "min_variance", cfg, d, current_weights=pd.Series(dtype=float))
    assert from_cash["cost_pct_nav"] == pytest.approx(w_act.sum() * fee)
    only_sell = backtest.target_weights_at(P, V, R, "min_variance", cfg, d,
                                           current_weights=w_act + 0.001 * (w_act > 0))
    n = int((w_act > 0).sum())
    assert only_sell["cost_pct_nav"] == pytest.approx(0.001 * n * (fee + tax))


def test_target_weights_at_ngay_khong_giao_dich(data, cfg):
    P, V, R = data
    with pytest.raises(ValueError, match="không phải phiên"):
        backtest.target_weights_at(P, V, R, "equal_weight", cfg, "2020-09-27")  # Chủ nhật


# --- B3: rf_shift --------------------------------------------------------------------------------

def test_rf_shift_voi_1n(data, cfg):
    P, V, R = data
    a = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"])
    b = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"],
                              overrides={"rf_shift": 0.01})
    pd.testing.assert_frame_equal(a["weights"], b["weights"])
    pd.testing.assert_series_equal(a["returns_net"], b["returns_net"])
    assert a["meta"]["rf_shift"] == 0.0 and b["meta"]["rf_shift"] == 0.01
    sa, sb = backtest.summarize(a, R), backtest.summarize(b, R)
    assert (sb["sharpe"] < sa["sharpe"]).all() and (sb["sortino"] < sa["sortino"]).all()
    # summarize tự đọc rf_shift từ meta, khớp với tự dịch rf bằng tay
    expected = backtest.metrics.sharpe_ratio(b["returns_net"], R["rf_annual_avg_year"] + 0.01)
    assert sb.loc["sau_phi", "sharpe"] == pytest.approx(expected)


def test_rf_shift_tac_dong_len_rf_ngay_quyet_dinh(data, cfg, monkeypatch):
    P, V, R = data
    seen = []

    def capture(strategy, ret_window, mkt_window, rf_at_decision, tickers, cfg_, return_info=False):
        seen.append((ret_window.index[-1], rf_at_decision))
        return pd.Series(1.0 / len(tickers), index=list(tickers)), {"fallback": False}

    monkeypatch.setattr(backtest, "compute_target_weights", capture)
    backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"], overrides={"rf_shift": 0.01})
    for d, rf_d in seen:
        assert rf_d == pytest.approx(R.loc[d, "rf_annual"] + 0.01)


def test_rf_shift_doi_max_sharpe_capm(data, cfg):
    P, V, R = data
    d = pd.Timestamp("2019-12-31")
    a = backtest.target_weights_at(P, V, R, "max_sharpe", cfg, d)
    b = backtest.target_weights_at(P, V, R, "max_sharpe", cfg, d, overrides={"rf_shift": 0.01})
    assert b["meta"]["rf_at_decision"] == pytest.approx(a["meta"]["rf_at_decision"] + 0.01)
    # CAPM: μ − rf = β·MRP không đổi theo rf, nên dịch rf không đổi nghiệm Max Sharpe
    pd.testing.assert_series_equal(a["weights"], b["weights"], atol=1e-4)


# --- B4: bootstrap chênh lệch Sharpe -------------------------------------------------------------

@pytest.fixture(scope="module")
def fake_returns():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2020-01-01", periods=500)
    a = pd.Series(rng.normal(0.0006, 0.012, 500), index=idx)
    b = pd.Series(rng.normal(0.0003, 0.012, 500), index=idx)
    return a, b, pd.Series(np.linspace(0.02, 0.05, 500), index=idx)


def test_bootstrap_hai_chuoi_giong_het(fake_returns):
    a, _, rf = fake_returns
    t = backtest.sharpe_diff_bootstrap(a, a.copy(), rf, n_boot=100, seed=1)
    assert t["diff"] == 0 and t["ci_low"] == 0 and t["ci_high"] == 0 and t["p_value"] == 1.0
    assert t["sharpe_a"] == t["sharpe_b"]
    assert (t["n_obs"], t["n_boot"], t["block_len"]) == (500, 100, 21)


def test_bootstrap_tai_lap_voi_cung_seed(fake_returns, cfg):
    a, b, rf = fake_returns
    assert (backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100, seed=7)
            == backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100, seed=7))
    assert (backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100)
            == backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100, seed=cfg["seed"]))
    assert (backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100, seed=7)
            != backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=100, seed=8))


def test_bootstrap_lay_mau_theo_cap(fake_returns):
    """Hai chuỗi gần như cùng biến động: lấy theo cặp thì khoảng hẹp hơn hẳn hai chuỗi độc lập."""
    a, b, rf = fake_returns
    paired = backtest.sharpe_diff_bootstrap(a, a + 0.0001, rf, n_boot=300, seed=3)
    indep = backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=300, seed=3)
    assert (paired["ci_high"] - paired["ci_low"]) < 0.05 * (indep["ci_high"] - indep["ci_low"])


def test_bootstrap_diem_khop_metrics_va_rf_theo_ngay_goc(fake_returns):
    a, b, rf = fake_returns
    t = backtest.sharpe_diff_bootstrap(a, b, rf, n_boot=50, seed=1)
    assert t["sharpe_a"] == pytest.approx(backtest.metrics.sharpe_ratio(a, rf))
    assert t["sharpe_b"] == pytest.approx(backtest.metrics.sharpe_ratio(b, rf))
    assert t["diff"] == pytest.approx(t["sharpe_a"] - t["sharpe_b"])
    assert t["ci_low"] <= t["ci_high"]
    assert 0 <= t["p_value"] <= 1

    # rf đi cùng từng quan sát: nếu lợi suất đúng bằng rf ngày của chính nó thì mọi mẫu có lợi suất vượt = 0
    # cho chuỗi a; khi đó sd = 0 và Sharpe không xác định phải báo lỗi. Sai cách căn rf sẽ cho sd > 0 và lọt qua.
    rf_daily = (1 + rf) ** (1 / 252) - 1
    with pytest.raises(ValueError, match="không xác định"):
        backtest.sharpe_diff_bootstrap(rf_daily, b, rf, n_boot=20, seed=1)


def test_bootstrap_rf_rieng_cho_chuoi_b(fake_returns):
    a, _, rf = fake_returns
    t = backtest.sharpe_diff_bootstrap(a, a, rf + 0.01, rf_annual_b=rf, n_boot=50, seed=1)
    assert t["diff"] == pytest.approx(backtest.metrics.sharpe_ratio(a, rf + 0.01) - backtest.metrics.sharpe_ratio(a, rf))
    assert t["diff"] < 0


def test_bootstrap_it_ngay_chung_bao_loi(fake_returns):
    a, b, rf = fake_returns
    with pytest.raises(ValueError, match="90%"):
        backtest.sharpe_diff_bootstrap(a.iloc[:300], b.iloc[250:], rf, n_boot=10)
    t = backtest.sharpe_diff_bootstrap(a.iloc[:480], b.iloc[20:], rf, n_boot=10, seed=1)  # 460/480 ≥ 90%
    assert t["n_obs"] == 460


@pytest.mark.parametrize("diff, low, high, sign, expected", [
    (0.3, 0.1, 0.5, 1, "ung_ho"),
    (0.3, -0.1, 0.5, 1, "dung_chieu_chua_du_bang_chung"),
    (-0.3, -0.5, -0.1, 1, "khong_ung_ho"),
    (-0.3, -0.5, 0.1, 1, "khong_ung_ho"),
    (-0.3, -0.5, -0.1, -1, "ung_ho"),
    (-0.3, -0.5, 0.1, -1, "dung_chieu_chua_du_bang_chung"),
    (0.3, 0.1, 0.5, -1, "khong_ung_ho"),
    (0.0, 0.0, 0.0, 1, "dung_chieu_chua_du_bang_chung"),
])
def test_verdict(diff, low, high, sign, expected):
    assert backtest.verdict(diff, low, high, sign) == expected


def test_verdict_dau_khong_hop_le():
    with pytest.raises(ValueError):
        backtest.verdict(0.1, 0.0, 0.2, 0)


# --- B5: căn VN-Index với danh mục ----------------------------------------------------------------

def test_benchmark_returns(data, val_1n):
    _, V, _ = data
    index = val_1n["returns_net"].index
    r = backtest.benchmark_returns(V, index)
    assert list(r.index) == list(index)
    assert r.iloc[0] == 0.0
    pd.testing.assert_series_equal(r.iloc[1:], V.reindex(index).pct_change(fill_method=None).iloc[1:],
                                   check_names=False)


def test_benchmark_returns_nhan_dataframe_va_bao_thieu_gia(data, val_1n):
    _, V, _ = data
    index = val_1n["returns_net"].index
    pd.testing.assert_series_equal(backtest.benchmark_returns(V.to_frame("close"), index),
                                   backtest.benchmark_returns(V, index))
    with pytest.raises(ValueError, match="thiếu giá"):
        backtest.benchmark_returns(V.drop(index[5]), index)


def test_equity_curve(data, val_1n):
    _, V, _ = data
    eq = backtest.equity_curve(val_1n, V)
    assert list(eq.columns) == ["gross", "net", "VN-Index"]
    assert list(eq.index) == list(val_1n["returns_net"].index)
    assert (eq.iloc[0] == 1.0).all()
    assert eq["net"].iloc[-1] == pytest.approx(val_1n["nav"].iloc[-1] / val_1n["nav"].iloc[0])
    assert eq["VN-Index"].iloc[-1] == pytest.approx(V.loc[eq.index[-1]] / V.loc[eq.index[0]])
    assert eq["gross"].iloc[-1] > eq["net"].iloc[-1]
