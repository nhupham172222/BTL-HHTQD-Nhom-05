"""Kiểm tra src/estimators.py và src/optimizers.py. Chủ file: TV4.

    python -m pytest tests/test_estimators_optimizers.py -q

Dùng dữ liệu giả lập (seed từ config.yaml) và một cửa sổ VALIDATION của dữ liệu thật (kỳ quyết định
31/12/2019). Không chạm tập test.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import backtest  # noqa: E402
import estimators as E  # noqa: E402
import optimizers as O  # noqa: E402
from config import load  # noqa: E402

TOL = 1e-6


@pytest.fixture(scope="module")
def cfg():
    return load()


@pytest.fixture(scope="module")
def fake(cfg):
    """10 mã, 500 phiên: r_i = β_i r_m + nhiễu riêng (β đã biết)."""
    rng = np.random.default_rng(cfg["seed"])
    n, T = 10, 500
    idx = pd.bdate_range("2020-01-01", periods=T)
    beta = np.linspace(0.5, 1.5, n)
    mkt = pd.Series(rng.normal(0.0004, 0.012, T), index=idx)
    eps = rng.normal(0, 0.01, (T, n)) * np.linspace(0.5, 2.0, n)
    R = pd.DataFrame(mkt.to_numpy()[:, None] * beta + eps, index=idx,
                     columns=[f"M{k:02d}" for k in range(n)])
    return R, mkt, pd.Series(beta, index=R.columns)


@pytest.fixture(scope="module")
def real_window(cfg):
    """Cửa sổ ước lượng thật tại kỳ quyết định đầu của validation (31/12/2019, 291 phiên)."""
    P, V, Rf = backtest.load_inputs()
    idx = P.index
    d = pd.Timestamp("2019-12-31")
    i = idx.get_loc(d)
    per = cfg["periods"]
    s = backtest.estimation_start(i, per["estimation_window_days"], per["min_estimation_window_days"], idx)
    win = P.iloc[s:i + 1]
    tk = win.columns[win.notna().all()]
    R = win[tk].pct_change(fill_method=None).iloc[1:]
    M = V.reindex(idx).iloc[s:i + 1].pct_change(fill_method=None).iloc[1:]
    return R, M, float(Rf["rf_annual"].loc[:d].iloc[-1])


def _check(w, tickers, w_max):
    assert list(w.index) == list(tickers)
    assert (w >= -TOL).all()
    assert w.max() <= w_max + TOL
    assert w.sum() == pytest.approx(1.0, abs=TOL)


# --- estimators -------------------------------------------------------------------------------

def test_beta_thi_truong_bang_1(fake):
    R, mkt, _ = fake
    b = E.betas(R.assign(MKT=mkt), mkt)
    assert b["MKT"] == pytest.approx(1.0, abs=1e-12)


def test_beta_khop_gia_tri_that(fake):
    R, mkt, beta = fake
    b = E.betas(R, mkt)
    assert np.corrcoef(b, beta)[0, 1] > 0.95


def test_capm_va_historical(fake, cfg):
    R, mkt, _ = fake
    rf, mrp = 0.04, cfg["estimation"]["market_risk_premium"]
    mu = E.expected_returns(R, mkt, "capm", rf, mrp)
    assert np.allclose(mu, rf + E.betas(R, mkt) * mrp)
    hist = E.expected_returns(R, mkt, "historical", rf)
    assert np.allclose(hist, R.mean() * cfg["conventions"]["trading_days_per_year"])
    with pytest.raises(ValueError):
        E.expected_returns(R, mkt, "capm", rf, None)
    with pytest.raises(ValueError):
        E.expected_returns(R, mkt, "abc", rf, mrp)


def test_covariance(fake, cfg):
    R, _, _ = fake
    k = cfg["conventions"]["trading_days_per_year"]
    S = E.covariance(R, "sample")
    assert np.allclose(S, R.cov() * k)
    L = E.covariance(R, "ledoit_wolf")
    assert list(L.index) == list(R.columns) and np.allclose(L, L.T)
    assert np.linalg.eigvalsh(L.to_numpy()).min() > 0
    # LW co về mục tiêu nên số điều kiện không lớn hơn Σ mẫu
    assert np.linalg.cond(L.to_numpy()) <= np.linalg.cond(S.to_numpy()) + 1e-9
    assert 0.0 <= E.shrinkage_intensity(R) <= 1.0
    with pytest.raises(ValueError):
        E.covariance(R, "abc")


def test_cua_so_co_nan_bao_loi(fake):
    R, mkt, _ = fake
    R2 = R.copy()
    R2.iloc[3, 2] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        E.covariance(R2, "sample")


# --- optimizers --------------------------------------------------------------------------------

@pytest.mark.parametrize("w_max", [0.05, 0.10, 0.15, 0.20])
def test_rang_buoc_bon_chien_luoc(real_window, cfg, w_max):
    R, M, rf = real_window
    S = E.covariance(R, "ledoit_wolf")
    mu = E.expected_returns(R, M, "capm", rf, cfg["estimation"]["market_risk_premium"])
    _check(O.equal_weight(list(R.columns)), R.columns, w_max)
    _check(O.min_variance(S, w_max), R.columns, w_max)
    _check(O.max_sharpe(mu, S, rf, w_max), R.columns, w_max)
    _check(O.risk_parity(S, w_max), R.columns, w_max)


def test_vo_nghiem_bao_loi(fake):
    R, _, _ = fake
    S = E.covariance(R, "sample")
    for f in (lambda: O.min_variance(S, 0.05), lambda: O.risk_parity(S, 0.05),
              lambda: O.max_sharpe(pd.Series(0.2, index=R.columns), S, 0.0, 0.05)):
        with pytest.raises(ValueError, match="Vô nghiệm"):
            f()  # 10 mã × 5% = 50% < 100%


def test_max_sharpe_khong_co_ma_vuot_rf(fake):
    R, _, _ = fake
    S = E.covariance(R, "sample")
    with pytest.raises(ValueError, match="vượt rf"):
        O.max_sharpe(pd.Series(0.01, index=R.columns), S, 0.05, 0.2)


def test_min_variance_toi_uu(real_window):
    """Không danh mục khả thi ngẫu nhiên nào có phương sai nhỏ hơn Min Variance."""
    R, _, _ = real_window
    S = E.covariance(R, "ledoit_wolf")
    w = O.min_variance(S, 0.10).to_numpy()
    v = w @ S.to_numpy() @ w
    rng = np.random.default_rng(0)
    for _ in range(300):
        x = rng.dirichlet(np.ones(len(w)))
        if x.max() <= 0.10:
            assert x @ S.to_numpy() @ x >= v - 1e-12


def test_max_sharpe_toi_uu(real_window, cfg):
    R, M, rf = real_window
    S = E.covariance(R, "ledoit_wolf")
    mu = E.expected_returns(R, M, "historical", rf)
    w = O.max_sharpe(mu, S, rf, 0.10)
    best = O.portfolio_stats(w, mu, S, rf)["sharpe"]
    for x in (O.min_variance(S, 0.10), O.risk_parity(S, 0.10), O.equal_weight(list(R.columns))):
        assert O.portfolio_stats(x, mu, S, rf)["sharpe"] <= best + 1e-6


def test_risk_parity_dong_gop_bang_nhau(real_window):
    R, _, _ = real_window
    S = E.covariance(R, "ledoit_wolf")
    w = O.risk_parity(S, 1.0)
    rc = O.risk_contributions(w, S)
    assert rc.max() - rc.min() < 1e-8
    assert rc.mean() == pytest.approx(1 / len(w))


def test_risk_parity_cham_tran(real_window):
    """Mã chạm trần có RC không lớn hơn các mã còn lại; các mã còn lại RC bằng nhau."""
    R, _, _ = real_window
    S = E.covariance(R, "ledoit_wolf")
    w_max = 0.05
    w = O.risk_parity(S, w_max)
    rc = O.risk_contributions(w, S)
    cap = w > w_max - 1e-9
    assert cap.any(), "cửa sổ này phải có mã chạm trần 5% (kiểm tra lại dữ liệu nếu đổi)"
    assert rc[~cap].max() - rc[~cap].min() < 1e-8
    assert rc[cap].max() <= rc[~cap].min() + 1e-10


def test_duong_bien(real_window, cfg):
    R, M, rf = real_window
    S = E.covariance(R, "ledoit_wolf")
    mu = E.expected_returns(R, M, "capm", rf, cfg["estimation"]["market_risk_premium"])
    pts, ws = O.efficient_frontier(mu, S, 0.10, n_points=15, rf_annual=rf)
    assert len(pts) == 15 and ws.shape == (15, len(R.columns))
    assert (np.diff(pts["exp_return"]) >= -1e-9).all()
    assert (np.diff(pts["volatility"]) >= -1e-9).all()
    mv = O.portfolio_stats(O.min_variance(S, 0.10), mu, S, rf)
    ms = O.portfolio_stats(O.max_sharpe(mu, S, rf, 0.10), mu, S, rf)
    assert pts["volatility"].iloc[0] == pytest.approx(mv["volatility"], rel=1e-4)
    assert pts["sharpe"].max() <= ms["sharpe"] + 1e-6
    for _, row in ws.iterrows():
        _check(row, R.columns, 0.10)


def test_max_sharpe_quy_tac_du_phong(fake, monkeypatch):
    """Có khóa estimation.max_sharpe_if_no_excess = min_variance thì trả Min Variance + cảnh báo."""
    R, _, _ = fake
    S = E.covariance(R, "sample")
    base = load()
    patched = {**base, "estimation": {**base["estimation"], "max_sharpe_if_no_excess": "min_variance"}}
    monkeypatch.setattr(O, "load", lambda: patched)
    with pytest.warns(UserWarning, match="Min Variance"):
        w = O.max_sharpe(pd.Series(0.01, index=R.columns), S, 0.05, 0.2)
    pd.testing.assert_series_equal(w, O.min_variance(S, 0.2))
