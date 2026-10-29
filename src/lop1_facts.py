"""Số liệu Lớp 1 (bước S): 1/N và VN-Index, giai đoạn lop1_window trong config.yaml. Chủ file: TV3.

    python src/lop1_facts.py          # ghi outputs/lop1_facts.csv

Quy ước (đều đọc từ config.yaml, không gõ cứng):
- "Danh mục hiện tại" = 1/N trên các mã còn giá (ROS NaN từ 12/08/2022 nên không nằm trong cửa sổ Lớp 1).
- Tái cân bằng theo quý: về 1/N tại giá đóng cửa PHIÊN ĐẦU TIÊN của mỗi quý; giữa hai lần để tỷ trọng trôi.
- Danh mục bắt đầu ở 1/N tại phiên đầu tiên của cửa sổ; lợi suất tính từ phiên kế tiếp
  (VN-Index cắt cùng các ngày để so sánh công bằng). Lần mua ban đầu không tính phí.
- Biến thể "sau phí": mỗi lần tái cân bằng trừ  turnover * (2*fee_per_side + sell_tax)
  (turnover = ½Σ|Δw| = tỷ lệ giá trị đem bán = tỷ lệ đem mua). Bỏ qua làm tròn lô 100.
- Sharpe/Sortino dùng rf_annual_avg_year (A9: TPCP 10 năm, bình quân theo năm);
  cột sharpe_rf_ngay dùng rf_annual theo ngày để đối chiếu.
- Mọi chỉ số tính bằng src/metrics.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from config import load  # noqa: E402


def quarter_starts(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Phiên đầu tiên của mỗi quý lịch có trong index."""
    q = index.to_period("Q")
    first = pd.Series(index, index=index).groupby(q).first()
    return pd.DatetimeIndex(first.values)


def equal_weight_quarterly(ret: pd.DataFrame, cost_rate: float) -> tuple[pd.Series, pd.Series]:
    """Lợi suất ngày của 1/N tái cân bằng quý. Trả (lợi suất, vòng quay mỗi lần tái cân bằng).

    ret: lợi suất ngày của các mã (NaN = không có giá). Hàng đầu tiên là phiên bắt đầu (chỉ để đặt tỷ trọng).
    cost_rate: phí quy đổi theo vòng quay (0 = trước phí).
    """
    dates = ret.index
    rebal = set(quarter_starts(dates)[1:])         # bỏ phiên đầu cửa sổ (đã đặt 1/N từ đầu)
    valid0 = ret.iloc[0].notna()
    w = pd.Series(np.where(valid0, 1.0 / valid0.sum(), 0.0), index=ret.columns)
    out, turns = {}, {}
    for t in dates[1:]:
        r = ret.loc[t].fillna(0.0)
        port = float((w * r).sum())
        w = w * (1.0 + r) / (1.0 + port)           # trôi tỷ trọng
        if t in rebal:
            valid = ret.loc[t].notna()
            w_new = pd.Series(np.where(valid, 1.0 / valid.sum(), 0.0), index=ret.columns)
            tn = metrics.turnover(w_new, w)
            turns[t] = tn
            port_net = (1.0 + port) * (1.0 - tn * cost_rate) - 1.0
            out[t] = port_net
            w = w_new
        else:
            out[t] = port
    return pd.Series(out), pd.Series(turns, dtype=float)


def run() -> pd.DataFrame:
    cfg = load()
    start, end = cfg["periods"]["lop1_window"]
    fee, tax = cfg["costs"]["fee_per_side"], cfg["costs"]["sell_tax"]
    assert cfg["portfolio"]["rebalance"] == "quarterly"
    cost_rate = 2 * fee + tax

    P = pd.read_csv(ROOT / "data/processed/prices.csv", index_col=0, parse_dates=True)
    V = pd.read_csv(ROOT / "data/processed/vnindex.csv", index_col=0, parse_dates=True)["close"]
    R = pd.read_csv(ROOT / "data/processed/rf.csv", index_col=0, parse_dates=True)

    ret = P.pct_change(fill_method=None).loc[start:end]
    vret = V.pct_change().loc[start:end]
    n_assets = int(ret.iloc[0].notna().sum())
    n_universe = P.shape[1]

    gross, t_g = equal_weight_quarterly(ret, 0.0)
    net, _ = equal_weight_quarterly(ret, cost_rate)
    vn = vret.loc[gross.index]

    cfg_txt = (f"config.yaml: lop1_window={start}..{end}; rebalance=quarterly; "
               f"fee_per_side={fee}; sell_tax={tax}; trading_days=252")
    rows = []
    for name, variant, s, turn in [
        ("1/N", "truoc_phi", gross, t_g),
        ("1/N", "sau_phi", net, t_g),
        ("VN-Index", "chi_so", vn, None),
    ]:
        a = metrics.summary(s, R["rf_annual_avg_year"])
        rows.append({
            "danh_muc": name,
            "bien_the": variant,
            "so_ma_trong_cua_so": n_assets if name == "1/N" else "",
            "so_ma_vu_tru": n_universe if name == "1/N" else "",
            "ngay_bat_dau": s.index[0].date(),
            "ngay_ket_thuc": s.index[-1].date(),
            "so_phien": a["n_obs"],
            "rf_cot": "rf_annual_avg_year",
            "loi_suat_nam": round(a["annual_return"], 6),
            "do_lech_chuan_nam": round(a["annual_volatility"], 6),
            "sharpe": round(a["sharpe"], 4),
            "sortino": round(a["sortino"], 4),
            "mdd": round(a["max_drawdown"], 6),
            "sut_giam_toi_da_pct": round(-100 * a["max_drawdown"], 2),
            "sharpe_rf_ngay": round(metrics.sharpe_ratio(s, R["rf_annual"]), 4),
            "vong_quay_tb_moi_lan_can_bang": round(float(turn.mean()), 6) if turn is not None else "",
            "so_lan_can_bang": int(len(turn)) if turn is not None else "",
            "config": cfg_txt,
        })
    df = pd.DataFrame(rows)
    out = ROOT / "outputs" / "lop1_facts.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print(run().drop(columns=["config"]).to_string(index=False))
    print("\nĐã ghi outputs/lop1_facts.csv")
