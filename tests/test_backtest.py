"""Kiểm tra src/backtest.py. Chủ file: TV5.

    python -m pytest tests/test_backtest.py -q

Chỉ chạy validation 2020–2021, trừ test ROS (1/N, 07–10/2022, không ghi file, không in chỉ số).
"""
import sys
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

    def capture(strategy, ret_window, mkt_window, rf_at_decision, tickers, cfg_):
        seen[ret_window.index[-1]] = rf_at_decision
        return pd.Series(1.0 / len(tickers), index=list(tickers))

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


# --- Mã ngừng giao dịch (ROS) ------------------------------------------------------------------

def test_ros_bi_loai_va_ban_het(data, cfg):
    P, V, R = data
    res = backtest.run_backtest(P, V, R, "equal_weight", cfg, "2022-07-01", "2022-10-31")
    w, hold, tr = res["weights"], res["holdings"], res["trades"]
    q2, q3 = pd.Timestamp("2022-06-30"), pd.Timestamp("2022-09-30")
    assert w.loc[q2, "ROS"] > 0 and hold.loc[q2, "ROS"] > 0
    assert (w.loc[q3:, "ROS"] == 0).all()
    assert hold.loc[q3, "ROS"] == 0

    t = res["schedule"].set_index("decision_date").loc[q3, "trade_date"]
    assert t == pd.Timestamp("2022-10-03")
    ros = tr[(tr["ticker"] == "ROS") & (tr["date"] == t)]
    assert len(ros) == 1 and ros["side"].iloc[0] == "sell"
    assert ros["shares"].iloc[0] == hold.loc[q2, "ROS"]
    assert ros["price"].iloc[0] == P["ROS"].dropna().iloc[-1]
    assert ros["tax"].iloc[0] > 0 and ros["fee"].iloc[0] > 0
    assert res["nav"].notna().all()  # giữa hai kỳ ROS định giá ở giá cuối
