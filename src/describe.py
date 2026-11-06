"""Phân tích MÔ TẢ (cấp độ 1). Chủ file: TV3.

    python src/describe.py            # ghi các CSV và hình vào outputs/ (notebooks/01_mo_ta.ipynb gọi lại các hàm ở đây)

Đầu ra:
    outputs/mo_ta_tung_ma.csv         thống kê từng mã, theo giai đoạn
    outputs/mo_ta_theo_giai_doan.csv  1/N và VN-Index theo giai đoạn và theo năm
    outputs/tuong_quan_toan_ky.csv    ma trận tương quan lợi suất ngày, toàn kỳ
    outputs/figures/mo_ta_*.png       hình

Quy ước: lợi suất ngày thập phân; 252 phiên/năm; Sharpe/Sortino dùng rf_annual_avg_year (A9);
mọi chỉ số tính bằng src/metrics.py. Giai đoạn "bình thường" và "2022" định nghĩa trong PERIODS
(theo docs/00_BOI_CANH_CHUNG.md mục 6); có thể ghi đè bằng khóa `diagnosis` trong config.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from config import load  # noqa: E402
from lop1_facts import equal_weight_quarterly  # noqa: E402

OUT = ROOT / "outputs"
FIG = OUT / "figures"

_DEFAULT_PERIODS = {
    "binh_thuong": ("2018-11-01", "2021-12-31"),   # docs/00 mục 6: giai đoạn "bình thường" khi chẩn đoán
    "nam_2022": ("2022-01-01", "2022-12-31"),
}


def periods() -> dict[str, tuple[str, str]]:
    """Các giai đoạn dùng chung cho mô tả và chẩn đoán (đọc config.yaml nếu có khóa `diagnosis`)."""
    cfg = load()
    p = dict(_DEFAULT_PERIODS)
    for k, v in (cfg.get("diagnosis") or {}).items():
        p[k] = tuple(v)
    p["toan_ky"] = (str(cfg["data"]["start"]), str(cfg["data"]["end"]))
    p["lop1"] = tuple(cfg["periods"]["lop1_window"])
    return p


def load_data() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Giá các mã, VN-Index, rf (rf_annual_avg_year, theo ngày)."""
    P = pd.read_csv(ROOT / "data/processed/prices.csv", index_col=0, parse_dates=True)
    V = pd.read_csv(ROOT / "data/processed/vnindex.csv", index_col=0, parse_dates=True)["close"]
    R = pd.read_csv(ROOT / "data/processed/rf.csv", index_col=0, parse_dates=True)["rf_annual_avg_year"]
    return P, V, R


def daily_returns(P: pd.DataFrame, V: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    return P.pct_change(fill_method=None), V.pct_change()


def stock_table(ret: pd.DataFrame, vret: pd.Series, rf: pd.Series, start: str, end: str) -> pd.DataFrame:
    """Thống kê từng mã trong [start, end]: số phiên, lợi suất năm, biến động, Sharpe, Sortino, MDD, beta, tương quan với VN-Index."""
    r_all = ret.loc[start:end]
    m = vret.loc[start:end]
    rows = []
    for t in r_all.columns:
        s = r_all[t].dropna()
        if len(s) < 2:
            continue
        a = metrics.summary(s, rf)
        mm = m.reindex(s.index)
        cov = np.cov(s.values, mm.values)[0, 1] if mm.notna().all() else np.nan
        rows.append({
            "ma": t,
            "so_phien": a["n_obs"],
            "ngay_cuoi_co_gia": s.index[-1].date(),
            "loi_suat_nam": a["annual_return"],
            "do_lech_chuan_nam": a["annual_volatility"],
            "sharpe": a["sharpe"],
            "sortino": a["sortino"],
            "mdd": a["max_drawdown"],
            "beta_vnindex": cov / mm.var(ddof=1) if np.isfinite(cov) else np.nan,
            "tuong_quan_vnindex": s.corr(mm),
        })
    return pd.DataFrame(rows).set_index("ma")


def equal_weight_series(ret: pd.DataFrame) -> pd.Series:
    """1/N tái cân bằng quý, trước phí, trên toàn kỳ (hàng đầu chỉ để đặt tỷ trọng ban đầu)."""
    s, _ = equal_weight_quarterly(ret.iloc[1:], 0.0)
    return s


def portfolio_period_table(ew: pd.Series, vn: pd.Series, rf: pd.Series) -> pd.DataFrame:
    """1/N và VN-Index theo giai đoạn (toàn kỳ, bình thường, 2022) và theo từng năm.

    Không có dòng Lớp 1: số chính thức của Lớp 1 nằm ở outputs/lop1_facts.csv (cắt từ 03/10/2023,
    có tính phí) để không có hai bộ số Lớp 1 hơi khác nhau trong repo.
    """
    p = periods()
    spans = {k: p[k] for k in ["toan_ky", "binh_thuong", "nam_2022"]}
    for y in range(ew.index[0].year, ew.index[-1].year + 1):
        spans[str(y)] = (f"{y}-01-01", f"{y}-12-31")
    rows = []
    for k, (a, b) in spans.items():
        for name, s in [("1/N (quý, trước phí)", ew), ("VN-Index", vn.reindex(ew.index))]:
            x = s.loc[a:b].dropna()
            if len(x) < 100:
                continue
            m = metrics.summary(x, rf)
            m["tong_loi_suat"] = float((1 + x).prod() - 1)
            rows.append({"giai_doan": k, "tu": x.index[0].date(), "den": x.index[-1].date(), "danh_muc": name, **m})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- hình
def _cluster_order(C: pd.DataFrame) -> list[str]:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    D = np.sqrt(np.clip(2 * (1 - C.values), 0, None))
    np.fill_diagonal(D, 0)
    order = leaves_list(linkage(squareform(D, checks=False), "average"))
    return list(C.columns[order])


def plot_heatmap(C: pd.DataFrame, title: str, order: list[str] | None = None, ax=None, vmin=0.0, vmax=0.8):
    import seaborn as sns

    order = order or _cluster_order(C)
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(9, 7.5))
    else:
        fig = ax.figure
    sns.heatmap(C.loc[order, order], ax=ax, cmap="viridis", vmin=vmin, vmax=vmax, square=True,
                cbar_kws={"label": "Tương quan"}, xticklabels=True, yticklabels=True)
    ax.set_title(title)
    ax.tick_params(labelsize=7)
    return fig, order


def plot_cum_dd(ew: pd.Series, vn: pd.Series, stress: tuple[str, str]):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for name, s, c in [("1/N (quý, trước phí)", ew, "#1f77b4"), ("VN-Index", vn.reindex(ew.index), "#d62728")]:
        w = (1 + s.fillna(0)).cumprod()
        a1.plot(w.index, w, label=name, color=c, lw=1.4)
        a2.plot(w.index, w / w.cummax() - 1, color=c, lw=1.2)
    for a in (a1, a2):
        a.axvspan(pd.Timestamp(stress[0]), pd.Timestamp(stress[1]), color="grey", alpha=0.18)
    a1.set_ylabel("Giá trị lũy kế (đầu kỳ = 1)")
    a1.set_title("Lợi suất lũy kế và sụt giảm: 1/N so với VN-Index (vùng xám = 2022)")
    a1.legend(loc="upper left")
    a2.set_ylabel("Sụt giảm từ đỉnh")
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    fig.tight_layout()
    return fig


def plot_stock_bars(tab: pd.DataFrame, title: str):
    t = tab.sort_values("sharpe")
    fig, axes = plt.subplots(1, 3, figsize=(13, 7.5), sharey=True)
    axes[0].barh(t.index, t["loi_suat_nam"] * 100, color="#4c72b0")
    axes[0].set_title("Lợi suất năm hóa (%)")
    axes[1].barh(t.index, t["sharpe"], color="#55a868")
    axes[1].set_title("Sharpe")
    axes[2].barh(t.index, t["mdd"] * 100, color="#c44e52")
    axes[2].set_title("Sụt giảm tối đa (%)")
    for a in axes:
        a.axvline(0, color="k", lw=0.6)
        a.tick_params(labelsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def run() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    P, V, R = load_data()
    ret, vret = daily_returns(P, V)
    p = periods()

    # 1. từng mã theo giai đoạn
    parts = []
    for k in ["toan_ky", "binh_thuong", "nam_2022", "lop1"]:
        t = stock_table(ret, vret, R, *p[k]).reset_index()
        t.insert(0, "giai_doan", k)
        parts.append(t)
    stocks = pd.concat(parts, ignore_index=True)
    stocks.round(6).to_csv(OUT / "mo_ta_tung_ma.csv", index=False, encoding="utf-8-sig")

    # 2. danh mục theo giai đoạn / năm
    ew = equal_weight_series(ret)
    per = portfolio_period_table(ew, vret, R)
    per.round(6).to_csv(OUT / "mo_ta_theo_giai_doan.csv", index=False, encoding="utf-8-sig")

    # 3. tương quan toàn kỳ (cặp có đủ dữ liệu cùng ngày)
    C = ret.loc[p["toan_ky"][0]:p["toan_ky"][1]].corr(min_periods=250)
    C.round(6).to_csv(OUT / "tuong_quan_toan_ky.csv", encoding="utf-8-sig")

    # 4. hình
    fig, _ = plot_heatmap(C, "Tương quan lợi suất ngày giữa các mã, toàn kỳ 11/2018–09/2026 (sắp theo cụm)")
    fig.tight_layout()
    fig.savefig(FIG / "mo_ta_heatmap_toan_ky.png", dpi=150)
    plt.close(fig)
    fig = plot_cum_dd(ew, vret, p["nam_2022"])
    fig.savefig(FIG / "mo_ta_luy_ke_drawdown.png", dpi=150)
    plt.close(fig)
    full = stocks[stocks.giai_doan == "toan_ky"].set_index("ma")
    fig = plot_stock_bars(full, "Từng mã, toàn kỳ 11/2018–09/2026 (sắp theo Sharpe; ROS dừng giao dịch 11/08/2022)")
    fig.savefig(FIG / "mo_ta_tung_ma.png", dpi=150)
    plt.close(fig)
    return {"stocks": stocks, "periods": per, "corr": C, "ew": ew}


if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_columns", 30)
    res = run()
    print(res["periods"][res["periods"].giai_doan.isin(["toan_ky", "binh_thuong", "nam_2022", "lop1"])]
          [["giai_doan", "danh_muc", "n_obs", "annual_return", "annual_volatility", "sharpe", "max_drawdown"]].round(4).to_string(index=False))
    print("\nĐã ghi outputs/mo_ta_*.csv, tuong_quan_toan_ky.csv và outputs/figures/mo_ta_*.png")
