"""Kiểm tra src/run_backtests.py và bước --backtest của run_all.py. Chủ file: TV5.

    python -m pytest tests/test_run_backtests.py -q

Không bao giờ chạy trên giai đoạn test: nhánh --period test được chạy thử với period = validation,
ghi vào thư mục tạm của pytest. Không ghi gì vào outputs/.
"""
import copy
import importlib
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import backtest  # noqa: E402
import run_backtests as RB  # noqa: E402
from config import load  # noqa: E402

PROTECTED = ("test_results.csv", "sensitivity_grid.csv", "equity_curves.csv", "weights_Q4_2026.csv")
BOOT = {"n_boot": 20, "block_len": 21}
AS_OF = "2021-09-30"


def _outputs_snapshot():
    return sorted(p.name for p in (ROOT / "outputs").iterdir())


OUTPUTS_BEFORE = _outputs_snapshot()  # chụp khi nạp file test, trước mọi fixture


@pytest.fixture(scope="module")
def cfg():
    return load()


@pytest.fixture(scope="module")
def small_cfg(cfg):
    """Rút gọn lưới độ nhạy để test nhanh; vẫn đủ mọi biến."""
    c = copy.deepcopy(cfg)
    c["sensitivity"].update(w_max=[0.10, 0.20], rebalance=["quarterly", "semiannual"], fee_per_side=[0.0015, 0.0040],
                            rf_shift=[0.0, 0.01], market_risk_premium=[0.0813, 0.0631])
    return c


@pytest.fixture(scope="module")
def validation_frames(cfg, tmp_path_factory):
    out = tmp_path_factory.mktemp("validation")
    return RB.run_validation(cfg, out_dir=out, boot=BOOT), out


@pytest.fixture(scope="module")
def test_branch_frames(small_cfg, tmp_path_factory):
    """Chạy thử nhánh test trên khoảng VALIDATION, thư mục tạm."""
    out = tmp_path_factory.mktemp("nhanh_test")
    return RB.run_test_period(small_cfg, out_dir=out, boot=BOOT, period=small_cfg["periods"]["validation"],
                              as_of=AS_OF), out


# --- Khóa đóng băng ------------------------------------------------------------------------------

def test_main_test_khong_co_co_thi_dung_khong_tinh_khong_ghi_file(monkeypatch, capsys):
    """Chạy trong tiến trình, phần tính toán bị thay bằng hàm báo lỗi: nếu khóa hỏng thì test đỏ,
    KHÔNG vô tình chạy backtest thật trên giai đoạn test (không dùng subprocess ở đây vì lý do đó)."""
    def fail(*a, **k):
        raise AssertionError("không được chạy phần tính toán khi thiếu cờ")

    monkeypatch.setattr(RB.backtest, "load_inputs", fail)
    monkeypatch.setattr(RB.backtest, "run_backtest", fail)
    monkeypatch.setattr(RB, "run_test_period", fail)
    before = _outputs_snapshot()
    assert RB.main(["--period", "test"]) == 2
    assert "--i-confirm-freeze" in capsys.readouterr().err
    assert _outputs_snapshot() == before


def test_main_chuyen_dung_nhanh(monkeypatch):
    called = []
    monkeypatch.setattr(RB, "run_test_period", lambda: called.append("test"))
    assert RB.main(["--period", "test", "--i-confirm-freeze"]) == 0
    assert called == ["test"]


# --- Validation ----------------------------------------------------------------------------------

def test_validation_du_to_hop(validation_frames, cfg):
    frames, out = validation_frames
    df = frames["validation_results.csv"]
    got = set(map(tuple, df[["chien_luoc", "mu", "cov"]].to_numpy()))
    assert got == {
        ("equal_weight", "n/a", "n/a"),
        ("min_variance", "n/a", "ledoit_wolf"), ("min_variance", "n/a", "sample"),
        ("risk_parity", "n/a", "ledoit_wolf"), ("risk_parity", "n/a", "sample"),
        ("max_sharpe", "capm", "ledoit_wolf"), ("max_sharpe", "capm", "sample"),
        ("max_sharpe", "historical", "ledoit_wolf"), ("max_sharpe", "historical", "sample"),
    }
    assert (df["so_ky"] == 8).all() and (df["window_len_min"] == 291).all()
    fb = df.set_index(["chien_luoc", "mu", "cov"])["n_fallback"]
    assert fb["max_sharpe", "historical", "ledoit_wolf"] == 1
    assert fb["max_sharpe", "capm", "ledoit_wolf"] == 0


def test_validation_khop_run_backtest(validation_frames, cfg):
    frames, _ = validation_frames
    df = frames["validation_results.csv"]
    P, V, R = backtest.load_inputs()
    res = backtest.run_backtest(P, V, R, "equal_weight", cfg, *cfg["periods"]["validation"])
    row = df[df["chien_luoc"] == "equal_weight"].iloc[0]
    s = backtest.summarize(res, R)
    assert row["sharpe_sau_phi"] == pytest.approx(s.loc["sau_phi", "sharpe"])
    assert row["sharpe_truoc_phi"] == pytest.approx(s.loc["truoc_phi", "sharpe"])
    assert row["tong_phi_thue_pct_nav0"] == pytest.approx(s.loc["sau_phi", "cost_pct_nav0"])
    assert row["turnover_tb"] == pytest.approx(res["turnover"].iloc[1:].mean())


def test_validation_window_len(validation_frames):
    frames, _ = validation_frames
    w = frames["validation_window_len.csv"]
    assert len(w) == 8 and w["window_len"].iloc[0] == 291 and w["window_len"].is_monotonic_increasing


def test_design_choice_va_quy_tac(validation_frames):
    frames, _ = validation_frames
    d = frames["validation_design_choice.csv"]
    assert set(map(tuple, d[["bien_thiet_ke", "chien_luoc"]].to_numpy())) == {
        ("cov", "min_variance"), ("cov", "risk_parity"), ("cov", "max_sharpe"), ("mu", "max_sharpe")}
    assert (d["ghi_chu"] == RB.DESIGN_RULE).all()
    assert RB._choice_by_rule(0.2, -0.1, 0.5, "a", "b", "b") == "b"    # khoảng chứa 0: giữ mặc định
    assert RB._choice_by_rule(0.2, 0.1, 0.5, "a", "b", "b") == "a"
    assert RB._choice_by_rule(-0.2, -0.5, -0.1, "a", "b", "a") == "b"


def test_moi_file_validation_co_cot_cau_hinh(validation_frames):
    frames, out = validation_frames
    for name in frames:
        f = pd.read_csv(out / name, encoding="utf-8-sig")
        for col in ("ngay_chay", "git_commit", "w_max", "fee_per_side", "rf_shift", "market_risk_premium"):
            assert col in f.columns, (name, col)
        assert f["ngay_chay"].notna().all()


# --- Nhánh test, chạy thử trên validation ------------------------------------------------------------

def test_nhanh_test_ghi_du_file_va_dung_ten(test_branch_frames):
    frames, out = test_branch_frames
    assert set(frames) == set(PROTECTED)
    for name in PROTECTED:
        f = pd.read_csv(out / name, encoding="utf-8-sig")
        assert len(f) and {"ngay_chay", "git_commit", "w_max"} <= set(f.columns)


def test_nhanh_test_bang_ket_qua(test_branch_frames):
    frames, _ = test_branch_frames
    t = frames["test_results.csv"].set_index("chien_luoc")
    assert set(t.index) == {"equal_weight", "min_variance", "max_sharpe", "risk_parity", "VN-Index"}
    assert t.loc["min_variance", "ky_vong_dau_h1"] == 1 and t.loc["risk_parity", "ky_vong_dau_h1"] == 1
    assert t.loc["max_sharpe", "ky_vong_dau_h1"] == -1
    assert t.loc[["min_variance", "max_sharpe", "risk_parity"], "verdict_h1"].isin(backtest.VERDICTS).all()
    assert pd.isna(t.loc["equal_weight", "verdict_h1"])
    assert t.loc["VN-Index", "sharpe_truoc_phi"] == t.loc["VN-Index", "sharpe_sau_phi"]
    assert t.loc["max_sharpe", "mu"] == "capm" and t.loc["min_variance", "mu"] == "n/a"


def test_nhanh_test_equity_dang_dai(test_branch_frames):
    frames, _ = test_branch_frames
    eq = frames["equity_curves.csv"]
    assert {"date", "series", "value"} <= set(eq.columns)
    assert eq["series"].nunique() == 9  # 4 chiến lược × (gross, net) + VN-Index
    first = eq.sort_values("date").groupby("series")["value"].first()
    assert (first == 1.0).all()


def test_nhanh_test_luoi_do_nhay(test_branch_frames, small_cfg):
    frames, _ = test_branch_frames
    g = frames["sensitivity_grid.csv"]
    assert set(g["bien_thay_doi"]) == {"w_max", "rebalance", "fee_per_side", "rf_shift", "market_risk_premium",
                                       "cov", "mu"}
    assert set(g.loc[g["bien_thay_doi"] == "market_risk_premium", "chien_luoc"]) == {"max_sharpe"}
    # Đổi từng biến một: mỗi biến có đúng một mức mặc định cho mỗi chiến lược
    assert (g[g["la_mac_dinh"]].groupby(["bien_thay_doi", "chien_luoc"]).size() == 1).all()
    dflt = g[g["la_mac_dinh"]]
    assert (dflt["diff_vs_mac_dinh"] == 0).all() and (dflt["p_value_vs_mac_dinh"] == 1).all()
    # 1/N không chạm w_max (H2) và không dùng μ, Σ (H3, H4): đổi các biến này phải cho đúng Sharpe mặc định
    eq = g[(g["chien_luoc"] == "equal_weight") & g["bien_thay_doi"].isin(["w_max", "cov", "mu"])]
    assert eq["sharpe_sau_phi"].nunique() == 1
    # μ không ảnh hưởng Min Variance, Risk Parity (H4)
    for s in ("min_variance", "risk_parity"):
        m = g[(g["chien_luoc"] == s) & (g["bien_thay_doi"] == "mu")]
        assert m["sharpe_sau_phi"].nunique() == 1


def test_luoi_rf_shift_diff_khop_cot_sharpe(test_branch_frames):
    """Dòng rf_shift: diff phải bằng chênh lệch cột Sharpe, tức mỗi bên dùng rf của chính nó."""
    frames, _ = test_branch_frames
    g = frames["sensitivity_grid.csv"]
    r = g[(g["bien_thay_doi"] == "rf_shift") & (g["chien_luoc"] == "equal_weight")].set_index("gia_tri")
    expected = r.loc["0.01", "sharpe_sau_phi"] - r.loc["0.0", "sharpe_sau_phi"]
    assert expected < 0
    assert r.loc["0.01", "diff_vs_mac_dinh"] == pytest.approx(expected)


def test_nhanh_test_bang_ty_trong(test_branch_frames, small_cfg):
    frames, _ = test_branch_frames
    w = frames["weights_Q4_2026.csv"]
    assert set(w["chien_luoc"]) == set(small_cfg["strategies"])
    assert (w["shares"] % small_cfg["portfolio"]["lot_size"] == 0).all()
    assert (w.groupby("chien_luoc")["weight_target"].sum().round(8) == 1).all()
    assert (w["decision_date"] == AS_OF).all()
    assert {"ticker", "weight_target", "shares", "weight_actual", "gia_dung", "turnover_vs_1n",
            "cost_pct_nav_vs_1n"} <= set(w.columns)


def test_unit_test_khong_ghi_gi_vao_outputs(test_branch_frames, validation_frames):
    """So với ảnh chụp đầu phiên, không kiểm tra tồn tại: sau lần chạy test chính thức các file đó sẽ có thật."""
    assert _outputs_snapshot() == OUTPUTS_BEFORE


# --- run_all.py ----------------------------------------------------------------------------------

@pytest.fixture
def run_all(monkeypatch):
    """run_all với bước O giả: không chạm data/, không chạy backtest thật."""
    log = types.SimpleNamespace(calls=[], o_ran=False)

    def clean_run():
        log.o_ran = True
        return {"final_shape": {"tickers": 1, "rows": 1}, "universe_size": 1, "final_imputed_cells": 0,
                "final_na_cells": 0, "excluded": {}, "suspect_unadjusted": {}, "notes": []}

    monkeypatch.setitem(sys.modules, "clean", types.SimpleNamespace(run=clean_run))
    monkeypatch.setitem(sys.modules, "export_phu_luc", types.SimpleNamespace(run=lambda: []))
    mod = importlib.import_module("run_all")
    monkeypatch.setattr(mod.subprocess, "call", lambda cmd: log.calls.append(cmd) or 0)
    return mod, log


def _run(monkeypatch, mod, *argv):
    monkeypatch.setattr(sys, "argv", ["run_all.py", *argv])
    return mod.main()


def test_run_all_mac_dinh_khong_chay_backtest(run_all, monkeypatch):
    mod, log = run_all
    assert _run(monkeypatch, mod) == 0
    assert log.o_ran and log.calls == []


def test_run_all_validation_chuyen_tiep(run_all, monkeypatch):
    mod, log = run_all
    assert _run(monkeypatch, mod, "--backtest", "validation") == 0
    assert log.o_ran
    assert log.calls[0][-2:] == ["--period", "validation"]
    assert log.calls[0][1].endswith("run_backtests.py")


def test_run_all_test_thieu_co_dung_truoc_buoc_o(run_all, monkeypatch):
    mod, log = run_all
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, mod, "--backtest", "test")
    assert e.value.code != 0
    assert not log.o_ran and log.calls == []


def test_run_all_test_co_co_chuyen_tiep(run_all, monkeypatch):
    mod, log = run_all
    assert _run(monkeypatch, mod, "--backtest", "test", "--i-confirm-freeze") == 0
    assert log.calls[0][-3:] == ["--period", "test", "--i-confirm-freeze"]
